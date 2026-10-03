#ifndef CONFIG_H
#define CONFIG_H

// ---------------------------------------------------------------------------
// Required
// ---------------------------------------------------------------------------
const char* WIFI_SSID     = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

// ---------------------------------------------------------------------------
// Optional - uncomment to override the defaults compiled into the sketch
// ---------------------------------------------------------------------------
// SECURITY: the default broker is a PUBLIC test broker. Anyone who guesses the
// topic can read this node's data and can publish to the control topic to
// trigger or silence the alarm. Point these at your own broker (with a
// username and password) before relying on this as a security device.
//
// #define MQTT_SERVER    "your.broker.example"
// #define MQTT_PORT      1883
// #define MQTT_USERNAME  "your-user"
// #define MQTT_PASSWORD  "your-password"
// #define MQTT_TOPIC_PUB "home/alert/data"
// #define MQTT_TOPIC_SUB "home/alert/control"

#endif
