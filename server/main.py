import paho.mqtt.client as mqtt
import requests
from config import PUSHPLUS_TOKEN, DANGER_DISTANCE

# ================= 1. Global Config =================
MQTT_BROKER      = "broker.emqx.io"
MQTT_PORT        = 1883
MQTT_TOPIC_DATA  = "home/alert/data"
MQTT_TOPIC_CTRL  = "home/alert/control"

# Local Ollama API (OpenAI-compatible endpoint)
LOCAL_API_URL    = "http://localhost:11434/v1/chat/completions"
MODEL_NAME       = "qwen2.5:1.5b"

is_alarm_on = False

# ================= 2. Push Notification =================
def send_phone_alert(title, content):
    try:
        url = f"http://www.pushplus.plus/send?token={PUSHPLUS_TOKEN}&title={title}&content={content}"
        requests.get(url)
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
        r = requests.post(LOCAL_API_URL, json=payload, timeout=5)
        r.raise_for_status()

        ai_msg = r.json()["choices"][0]["message"]
        reply  = ai_msg["content"].strip() if ai_msg["content"] else "Standby"
        print(f"[AI] Summary: {reply}")
        speak_text(reply)
    except Exception as e:
        print(f"[AI] Call failed: {e}")

# ================= 5. MQTT Message Handler =================
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
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.subscribe(MQTT_TOPIC_DATA)
    print("[System] MQTT + LLM + Push + TTS pipeline started. Waiting for ESP32 data...")
    client.loop_forever()
