# ESP32 Edge AI Security System

A distributed security demo that combines ESP32-based sensing with PC-side edge AI inference. Multi-sensor data is transmitted over MQTT; a local LLM generates environmental summaries; alerts are pushed to WeChat and played through Windows TTS.

![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Platform: ESP32](https://img.shields.io/badge/Platform-ESP32-blue)
![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue)

> **Status**: Teaching / demo project. For production security use, see the "Security Boundaries" section — the default setup uses a public MQTT broker and third-party push, which are not appropriate for real deployments.

## Overview

Most "smart security" demos either push everything to the cloud (privacy issues, latency) or run everything on a microcontroller (no room for real AI). This project splits the workload:

- **ESP32** handles real-time sensing and physical output. It samples distance, motion, and ambient light, publishes over MQTT, and listens for control commands.
- **PC (Python)** handles logic and AI inference. It subscribes to sensor data, decides when to trigger an alert, calls a local LLM (Ollama) for a short environmental summary, sends a WeChat push, and plays Windows TTS.

The result: real-time responsiveness from the MCU, real intelligence from the PC, and sensor data processed locally (see Security Boundaries for caveats on the broker and push provider).

## Architecture

```text
[Sensing]      ESP32 (Ultrasonic / PIR / Photoresistor)
                   │
                   ▼ (MQTT publish, port 1883)
           [MQTT Broker] (broker.emqx.io — public, for demo only)
                   │
                   ▼ (MQTT subscribe, port 1883)
[Edge Compute] PC Python (parse + decision logic)
                   │
                   ├─► MQTT publish control ──► ESP32 (buzzer / relay)
                   │
                   ├─► HTTP request ──► PushPlus (WeChat notification)
                   │
                   └─► Local API ──► Ollama (qwen2.5:1.5b) ──► Windows TTS
```

## Repository Structure

```text
esp32-edge-ai-security/
├── README.md
├── LICENSE
├── .gitignore
├── requirements.txt
├── firmware/                 # ESP32 side
│   ├── esp32_sensors.ino
│   └── config.example.h
└── server/                   # PC side
    ├── main.py
    └── config.example.py
```

## Hardware Bill of Materials

| Component | Model | Qty |
|-----------|-------|-----|
| MCU | ESP32-S3 (or ESP32) | 1 |
| Ultrasonic sensor | HC-SR04 | 1 |
| PIR motion sensor | HC-SR501 | 1 |
| Photoresistor module | HW-072 (digital out) | 1 |
| Buzzer / Relay | 5V active buzzer or relay module | 1 |
| Breadboard + jumpers | — | assorted |

## Pin Mapping (ESP32-S3)

| Module | Pin | ESP32 GPIO |
|--------|-----|------------|
| HC-SR04 | Trig | D18 |
| HC-SR04 | Echo | D19 |
| HC-SR501 | OUT | D5 |
| HW-072 | DO | D4 |
| Buzzer/Relay | IN | D2 |
| All modules | VCC | 5V (external) |
| All modules | GND | GND (**must be common with ESP32**) |

> ⚠️ **HC-SR04 Echo outputs 5V, but ESP32 GPIO is 3.3V-tolerant only.** Use a voltage divider (e.g. 1kΩ + 2kΩ) on the Echo line, or you will eventually damage the pin.

## Quick Start

### 1. Flash the ESP32

```text
1. Open firmware/esp32_sensors.ino in Arduino IDE.
2. Install the PubSubClient library via Library Manager.
3. Copy firmware/config.example.h to firmware/config.h and fill in your WiFi credentials.
4. Select the correct board and port, then upload.
```

### 2. Run the PC Side

```bash
pip install -r requirements.txt
pip install pywin32   # Windows only, for TTS speech

# Copy and fill in your PushPlus token
cp server/config.example.py server/config.py

# Start the local LLM (first run will download the model)
ollama run qwen2.5:1.5b

# Start the main program (new terminal)
python server/main.py
```

### 3. Demo Behavior

The alarm triggers only when **both** conditions are met: distance ≤ 20cm **AND** PIR detects motion.

```text
1. Stand in front of the PIR sensor and sway slightly (HC-SR501 only responds to motion — a still person will not trigger it).
2. While swaying, move your hand within ~20cm of the ultrasonic sensor.
3. When both conditions hold, the ESP32 buzzer fires.
4. The PC generates a short summary via the local LLM (e.g. "Motion detected nearby").
5. PushPlus delivers a WeChat alert.
6. Windows TTS speaks the summary.
```

> **Single-person demo tip**: if the PIR keeps timing out while you reach for the ultrasonic sensor, temporarily increase `DANGER_DISTANCE` in `main.py` to 40cm to make solo demos easier.

## Configuration & Secrets

**Never commit WiFi credentials or API tokens.** The repo uses `.example` templates:

- `firmware/config.example.h` → copy to `firmware/config.h`
- `server/config.example.py` → copy to `server/config.py`

Both real config files are listed in `.gitignore`.

## Security Boundaries

This is a teaching project, not a hardened security product. Two things are worth understanding before deploying anything resembling real use:

**1. `broker.emqx.io` is a public broker.** Anyone can subscribe to your topics and see sensor data. Anyone can also publish to your control topic and trigger the buzzer or relay. For any non-demo use, run a local broker (e.g. Mosquitto) on your PC or LAN, and add username/password + ACLs on the control topic before going further.

**2. PushPlus is a third-party push service.** Sensor data stays local, but the alert text passes through PushPlus's servers on its way to WeChat. If full-local privacy is required, replace it with a self-hosted notification backend (see Roadmap).

## Hardware & Engineering Pitfalls

This project is a compact case study for IoT + edge AI instruction. The real engineering lessons are in the pitfalls:

1. **Breadboard rules**: vertical rails connect, horizontal rows are isolated. Mixing up the power rails is the #1 cause of dead circuits.
2. **GPIO protection**: motors and relays must be isolated through a transistor or driver module. Driving them directly from GPIO will fry the MCU.
3. **Common ground**: when using external power, the ESP32 GND and the external supply GND must be tied together. Floating ground causes erratic sensor readings.
4. **Sensor quirks**: HC-SR04 needs a level shifter on the Echo line (see pin table above); HC-SR501 only responds to **motion**, not presence — a still person will not trigger it; HW-072 photoresistor modules need potentiometer threshold tuning.
5. **Edge compute architecture**: MCUs do real-time control; PCs do heavy AI inference. MQTT is the decoupling layer that keeps both sides independent.

## Known Limitations

- **No cooldown on the alarm path.** A single intrusion-like event may trigger repeated LLM invocations, duplicate PushPlus alerts, and continuous TTS playback. Implementing event debounce, a cooldown timer, and tiered-alert logic is mandatory for real-world usage.
- **No MQTT reconnection handling beyond `PubSubClient.reconnect()`.** Under WiFi jitter, the ESP32 will drop and re-establish, but there is no Last Will or persistent session.
- **Windows-only on the PC side.** TTS uses `pywin32` + SAPI. On macOS/Linux, replace `speak_text()` with a system equivalent. (If you prefer not to touch Python, the ESP32 side can be extended with a DFPlayer module for offline voice playback.)
- **Payload schema is not formally specified.** Topics and field names are documented only in code comments. See Roadmap.
- **No demo photo or video yet.** A 30-second GIF (reach → buzzer → WeChat push → TTS) would tell the story better than text.

## Roadmap

- [ ] Add cooldown + tiered escalation on the alarm path.
- [ ] Replace `broker.emqx.io` with a local Mosquitto broker and add auth on the control topic.
- [ ] Define a formal JSON payload schema for MQTT messages.
- [ ] Add a lightweight web dashboard for live sensor data.
- [ ] Replace PushPlus with a self-hosted notification service.
- [ ] Dockerize the PC-side Python server.
- [ ] Record a demo GIF and add it to the README.

## License

Distributed under the MIT License. See `LICENSE` for details.
