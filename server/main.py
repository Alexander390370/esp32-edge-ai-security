import paho.mqtt.client as mqtt
import requests

import config

# ================= 1. Global Config =================
# Optional keys are read with getattr so an existing config.py that only
# defines PUSHPLUS_TOKEN and DANGER_DISTANCE keeps working unchanged.
# See config.example.py for the full set of overridable values.
MQTT_BROKER     = getattr(config, "MQTT_BROKER", "broker.emqx.io")
MQTT_PORT       = getattr(config, "MQTT_PORT", 1883)
MQTT_USERNAME   = getattr(config, "MQTT_USERNAME", "")
MQTT_PASSWORD   = getattr(config, "MQTT_PASSWORD", "")
MQTT_TOPIC_DATA = getattr(config, "MQTT_TOPIC_DATA", "home/alert/data")
MQTT_TOPIC_CTRL = getattr(config, "MQTT_TOPIC_CTRL", "home/alert/control")

PUSHPLUS_TOKEN  = config.PUSHPLUS_TOKEN
DANGER_DISTANCE = config.DANGER_DISTANCE

# PushPlus over HTTPS. The token must never travel in a cleartext query string.
PUSHPLUS_URL    = getattr(config, "PUSHPLUS_URL", "https://www.pushplus.plus/send")

# Local Ollama API (OpenAI-compatible endpoint)
LOCAL_API_URL   = getattr(config, "LOCAL_API_URL",
                          "http://localhost:11434/v1/chat/completions")
MODEL_NAME      = getattr(config, "MODEL_NAME", "qwen2.5:1.5b")

HTTP_TIMEOUT    = 5

is_alarm_on = False

# ================= 2. Push Notification =================
def send_phone_alert(title, content):
    """POST to PushPlus. Token goes in the JSON body, not the URL."""
    try:
        r = requests.post(
            PUSHPLUS_URL,
            json={"token": PUSHPLUS_TOKEN, "title": title, "content": content},
            timeout=HTTP_TIMEOUT,
        )
        r.raise_for_status()
        print(f"[Push] Sent WeChat notification: {title}")
    except Exception as e:
        print(f"[Push] Failed to send WeChat notification: {e}")

# ================= 3. Text-to-Speech (Windows SAPI) =================
def speak_text(text):
    print(f"[TTS] Speaking: {text}")
    try:
        import win32com.client
        speaker = win32com.client.Dispatch("SAPI.SpVoice")
        speaker.Speak(text)
        print("[TTS] Done")
    except Exception as e:
        print(f"[TTS] Failed (install pywin32 on Windows): {e}")

# ================= 4. Local LLM Summary =================
def get_ai_description(dist, status, light_status):
    try:
        messages = [
            {"role": "system", "content":
                "You are a smart security announcer. Describe the current state in under 10 characters."},
            {"role": "user", "content":
                f"Distance {dist} cm, {status}, {light_status}."}
        ]
        payload = {
            "model": MODEL_NAME,
            "messages": messages,
            "max_tokens": 15,
            "temperature": 0.3
        }
        r = requests.post(LOCAL_API_URL, json=payload, timeout=HTTP_TIMEOUT)
        r.raise_for_status()

        ai_msg = r.json()["choices"][0]["message"]
        reply  = ai_msg["content"].strip() if ai_msg["content"] else "Standby"
        print(f"[AI] Summary: {reply}")
        speak_text(reply)
    except Exception as e:
        print(f"[AI] Call failed: {e}")

# ================= 5. MQTT Callbacks =================
def on_connect(client, userdata, flags, rc):
    """Subscribe here rather than once after connect().

    paho reconnects on its own but does NOT re-subscribe by itself. Subscribing
    only at startup means that after the first network blip the server silently
    stops receiving data: no error, no log, just an alarm that never fires.
    (Callback signatures follow paho-mqtt 1.6.1, which requirements.txt pins.)
    """
    if rc == 0:
        client.subscribe(MQTT_TOPIC_DATA)
        print(f"[MQTT] Connected to {MQTT_BROKER}:{MQTT_PORT}, "
              f"subscribed to {MQTT_TOPIC_DATA}")
    else:
        print(f"[MQTT] Connection refused, rc={rc}")

def on_disconnect(client, userdata, rc):
    if rc != 0:
        print(f"[MQTT] Unexpected disconnect (rc={rc}); paho will retry.")

def on_message(client, userdata, msg):
    global is_alarm_on
    payload = msg.payload.decode()
    print(f"[Data] {payload}")

    try:
        parts = payload.split(",")
        dist  = int(parts[0].split(":")[1])
        pir   = int(parts[1].split(":")[1])
        light = int(parts[2].split(":")[1])

        status       = "person detected" if pir == 1 else "no person"
        # Note: light == 1 is assumed to mean "dark", light == 0 means "bright".
        # This depends on the potentiometer threshold on the HW-072 module.
        light_status = "low light" if light == 1 else "bright light"

        if dist <= DANGER_DISTANCE and pir == 1:
            if not is_alarm_on:
                print("[Alarm] Triggered")
                client.publish(MQTT_TOPIC_CTRL, "1")
                is_alarm_on = True
                get_ai_description(dist, status, light_status)
                send_phone_alert("Security Alert",
                                 f"Distance {dist}cm, {status}, {light_status}!")
        else:
            if is_alarm_on:
                print("[Alarm] Cleared")
                client.publish(MQTT_TOPIC_CTRL, "0")
                is_alarm_on = False
                get_ai_description(dist, status, light_status)
                send_phone_alert("All Clear", "Environment is back to normal.")
    except Exception as e:
        print(f"[Parse] Error: {e}")

# ================= 6. Entry Point =================
if __name__ == "__main__":
    client = mqtt.Client()
    if MQTT_USERNAME:
        client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

    client.on_connect    = on_connect
    client.on_disconnect = on_disconnect
    client.on_message    = on_message

    print("[System] MQTT + LLM + Push + TTS pipeline started. "
          "Waiting for ESP32 data...")
    # connect_async + loop_forever keeps retrying if the broker is not up yet
    # (a plain connect() would raise and exit instead).
    client.connect_async(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_forever()
