#include <WiFi.h>
#include <PubSubClient.h>
#include "config.h"

// ================= Pin Definitions =================
const int TRIG_PIN  = 18;   // HC-SR04 Trig
const int ECHO_PIN  = 19;   // HC-SR04 Echo (needs 5V->3.3V divider)
const int PIR_PIN   = 5;    // HC-SR501 OUT
const int ALARM_PIN = 2;    // Buzzer / relay
const int LIGHT_PIN = 4;    // HW-072 photoresistor DO

// ================= MQTT Config =================
// Override any of these in config.h (see config.example.h). The defaults keep
// working with a config.h that only defines WIFI_SSID / WIFI_PASSWORD.
//
// SECURITY: broker.emqx.io is a PUBLIC test broker. Anyone who guesses the
// topic can read this node's data and can publish to the control topic to
// trigger or silence the alarm. Point these at your own broker before trusting
// this as a real security device.
#ifndef MQTT_SERVER
#define MQTT_SERVER   "broker.emqx.io"
#endif
#ifndef MQTT_PORT
#define MQTT_PORT     1883
#endif
#ifndef MQTT_USERNAME
#define MQTT_USERNAME ""
#endif
#ifndef MQTT_PASSWORD
#define MQTT_PASSWORD ""
#endif
#ifndef MQTT_TOPIC_PUB
#define MQTT_TOPIC_PUB "home/alert/data"
#endif
#ifndef MQTT_TOPIC_SUB
#define MQTT_TOPIC_SUB "home/alert/control"
#endif

// How long setup() waits for WiFi before rebooting, and how long a single
// reconnect attempt may block the loop.
const unsigned long WIFI_TIMEOUT_MS    = 30000;
const unsigned long RECONNECT_TIMEOUT_MS = 10000;

WiFiClient espClient;
PubSubClient client(espClient);

// ================= Client ID =================
// Derived from the MAC so two boards - or a reconnect while the broker still
// holds the previous session - do not kick each other offline.
String clientId() {
  uint8_t mac[6];
  WiFi.macAddress(mac);
  char buf[32];
  snprintf(buf, sizeof(buf), "ESP32_Node_%02X%02X%02X",
           mac[3], mac[4], mac[5]);
  return String(buf);
}

// ================= MQTT Callback =================
void callback(char* topic, byte* payload, unsigned int length) {
  String msg;
  for (unsigned int i = 0; i < length; i++) {
    msg += (char)payload[i];
  }

  if (msg == "1") {
    digitalWrite(ALARM_PIN, HIGH);
  } else if (msg == "0") {
    digitalWrite(ALARM_PIN, LOW);
  }
}

// ================= Setup =================
void setup() {
  Serial.begin(115200);
  pinMode(TRIG_PIN,  OUTPUT);
  pinMode(ECHO_PIN,  INPUT);
  pinMode(PIR_PIN,   INPUT);
  pinMode(ALARM_PIN, OUTPUT);
  pinMode(LIGHT_PIN, INPUT);
  digitalWrite(ALARM_PIN, LOW);

  // Bounded wait: never hang in setup() forever if the access point is down.
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  unsigned long wifiStart = millis();
  while (WiFi.status() != WL_CONNECTED) {
    if (millis() - wifiStart > WIFI_TIMEOUT_MS) {
      Serial.println("\nWiFi unavailable - rebooting to retry.");
      ESP.restart();
    }
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected.");

  client.setServer(MQTT_SERVER, MQTT_PORT);
  client.setCallback(callback);
}

// ================= MQTT Reconnect =================
// Bounded: returns false instead of blocking the loop forever. An unattended
// security node that stops sensing without saying so is worse than one that
// reboots.
bool reconnect() {
  unsigned long start = millis();
  while (!client.connected()) {
    if (millis() - start > RECONNECT_TIMEOUT_MS) {
      return false;
    }

    bool ok;
    if (strlen(MQTT_USERNAME) > 0) {
      ok = client.connect(clientId().c_str(), MQTT_USERNAME, MQTT_PASSWORD);
    } else {
      ok = client.connect(clientId().c_str());
    }

    if (ok) {
      client.subscribe(MQTT_TOPIC_SUB);
      Serial.print("MQTT connected as ");
      Serial.println(clientId());
    } else {
      Serial.print("MQTT connect failed, rc=");
      Serial.println(client.state());
      delay(500);
    }
  }
  return true;
}

// ================= Main Loop =================
void loop() {
  if (!client.connected()) {
    if (!reconnect()) {
      Serial.println("MQTT unavailable - rebooting to retry.");
      delay(1000);
      ESP.restart();
    }
  }
  client.loop();

  // Ultrasonic distance measurement
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);
  long duration = pulseIn(ECHO_PIN, HIGH, 30000);
  int distance = duration * 0.034 / 2;
  if (distance == 0) distance = 999;   // timeout -> treat as "far away"

  // Read PIR and photoresistor
  int pirState   = digitalRead(PIR_PIN);
  int lightState = digitalRead(LIGHT_PIN);

  // Publish as "D:<distance>,P:<pir>,L:<light>"
  String msg = "D:" + String(distance)
             + ",P:" + String(pirState)
             + ",L:" + String(lightState);
  client.publish(MQTT_TOPIC_PUB, msg.c_str());

  delay(500);  // 2 Hz publish rate
}
