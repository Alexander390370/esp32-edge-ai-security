# Copy this file to config.py and fill in your own values.
# config.py is listed in .gitignore and will never be committed.
#
# Everything below is optional except PUSHPLUS_TOKEN and DANGER_DISTANCE:
# main.py falls back to the defaults shown here when a key is absent, so an
# older config.py with only those two entries keeps working.

# ---------------------------------------------------------------------------
# PushPlus
# ---------------------------------------------------------------------------
# Get a token at: https://www.pushplus.plus/
PUSHPLUS_TOKEN = "YOUR_PUSHPLUS_TOKEN"

# ---------------------------------------------------------------------------
# Alarm behaviour
# ---------------------------------------------------------------------------
# Alarm trigger threshold (centimeters)
DANGER_DISTANCE = 20

# ---------------------------------------------------------------------------
# MQTT broker
# ---------------------------------------------------------------------------
# SECURITY WARNING
# The default below is a PUBLIC test broker. Anyone who guesses the topic can
#   * subscribe to MQTT_TOPIC_DATA  -> read your sensor data, and
#   * publish to   MQTT_TOPIC_CTRL  -> trigger the alarm, or silence it.
# Before treating this as a real security device, point it at your own broker
# (with a username and password) and use topics nobody else knows.
MQTT_BROKER     = "broker.emqx.io"
MQTT_PORT       = 1883
MQTT_USERNAME   = ""        # leave empty for anonymous brokers
MQTT_PASSWORD   = ""
MQTT_TOPIC_DATA = "home/alert/data"
MQTT_TOPIC_CTRL = "home/alert/control"

# ---------------------------------------------------------------------------
# Local LLM (Ollama, OpenAI-compatible endpoint)
# ---------------------------------------------------------------------------
LOCAL_API_URL = "http://localhost:11434/v1/chat/completions"
MODEL_NAME    = "qwen2.5:1.5b"
