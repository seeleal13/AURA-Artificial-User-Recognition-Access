#include <WiFi.h>
#include <WebServer.h>
#include <ArduinoJson.h>

// Wifi credentials ( i will try to make CLI entry possible later so user can enter info about his wifi without accessing the code source or changing it)
const char* ssid = "WIFI_ssid";
const char* password = "WIFI_password";

const int GREEN_LED = 2;
const int RED_LED = 3;
const int BUZZER = 4;

WebServer server(80);

void setup() {
  //match to baud rate 
  Serial.begin(115200);

  pinMode(GREEN_LED, OUTPUT);
  pinMode(RED_LED, OUTPUT);
  pinMode(BUZZER, OUTPUT);
  digitalWrite(GREEN_LED, LOW);
  digitalWrite(RED_LED, LOW);

  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.println("Connecting to WiFi...");
  }
  Serial.println("Connected to wifi");
  Serial.println(WiFi.localIP());

  // the server route ( use this "/update" in ESP url)
  server.on("/update", HTTP_POST, handleUpdate);
  server.begin();
  Serial.println("HTTP server started");
}

void handleUpdate() {
}

void loop() {
  
}