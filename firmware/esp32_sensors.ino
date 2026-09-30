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
const char* MQTT_SERVER = "broker.emqx.io";
const char* MQTT_TOPIC_PUB = "home/alert/data";
const char* MQTT_TOPIC_SUB = "home/alert/control";

WiFiClient espClient;
PubSubClient client(espClient);

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

  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected.");

  client.setServer(MQTT_SERVER, 1883);
  client.setCallback(callback);
}

// ================= MQTT Reconnect =================
void reconnect() {
  while (!client.connected()) {
    if (client.connect("ESP32_Node")) {
      client.subscribe(MQTT_TOPIC_SUB);
    } else {
      delay(500);
    }
  }
}

// ================= Main Loop =================
void loop() {
  if (!client.connected()) reconnect();
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
