/*
 * ESP32 Advanced Web Server with GPIO Control
 * ============================================
 *
 * This firmware provides a complete web server solution for ESP32 modules
 * with GPIO control, real-time monitoring, and a responsive web interface.
 *
 * Features:
 * - WiFi connection with fallback AP mode
 * - Asynchronous web server
 * - GPIO control (LEDs, relays, etc.)
 * - Real-time status monitoring
 * - JSON API endpoints
 * - Mobile-responsive web interface
 * - OTA updates support
 * - Serial debugging
 * - Touch sensor support
 * - ADC readings
 *
 * Hardware connections:
 * - Built-in LED: GPIO2
 * - External LED: GPIO5
 * - Button: GPIO4 with pull-up
 * - Relay: GPIO12
 * - Sensor: GPIO14 (ADC)
 * - Touch sensor: GPIO15
 *
 * Author: ESP Deployment System
 * Version: 1.0.0
 */

#include <WiFi.h>
#include <ESPAsyncWebServer.h>
#include <ArduinoJson.h>
#include <SPIFFS.h>
#include <ArduinoOTA.h>
#include <ESPmDNS.h>
#include "esp_wifi.h"

// ==================== CONFIGURATION ====================

// WiFi Configuration
const char* ssid = "YOUR_WIFI_SSID";           // Replace with your WiFi SSID
const char* password = "YOUR_WIFI_PASSWORD";   // Replace with your WiFi password

// Access Point Configuration (fallback)
const char* ap_ssid = "ESP32-WebServer";
const char* ap_password = "12345678";

// Device Configuration
const char* hostname = "esp32-webserver";
const char* device_name = "ESP32 Web Server";
const char* firmware_version = "1.0.0";

// GPIO Pin Definitions
const int BUILTIN_LED_PIN = 2;     // Built-in LED
const int EXTERNAL_LED_PIN = 5;    // External LED
const int BUTTON_PIN = 4;          // Button with pull-up
const int RELAY_PIN = 12;          // Relay control
const int SENSOR_PIN = 14;         // Analog sensor (ADC)
const int TOUCH_PIN = 15;          // Touch sensor

// Server Configuration
const int HTTP_PORT = 80;
const int WEBSOCKET_PORT = 81;

// Touch sensor threshold
const int TOUCH_THRESHOLD = 40;

// ==================== GLOBAL VARIABLES ====================

AsyncWebServer server(HTTP_PORT);
AsyncWebSocket ws("/ws");

// Device state
struct DeviceState {
  bool builtin_led = false;
  bool external_led = false;
  bool button_pressed = false;
  bool relay_state = false;
  int sensor_value = 0;
  int touch_value = 0;
  bool touch_detected = false;
  unsigned long uptime = 0;
  int free_heap = 0;
  int wifi_rssi = 0;
  String ip_address = "";
  String mac_address = "";
  float cpu_temperature = 0.0;
  unsigned long last_update = 0;
} deviceState;

// Statistics
struct Statistics {
  unsigned long boot_time = 0;
  unsigned long total_requests = 0;
  unsigned long websocket_connections = 0;
  unsigned long gpio_toggles = 0;
  unsigned long touch_events = 0;
  String last_client_ip = "";
  unsigned long last_request_time = 0;
} stats;

// Timing variables
unsigned long last_sensor_read = 0;
unsigned long last_status_update = 0;
unsigned long last_button_check = 0;
unsigned long last_touch_check = 0;
bool last_button_state = HIGH;
bool last_touch_state = false;

// Constants
const unsigned long SENSOR_READ_INTERVAL = 1000;    // 1 second
const unsigned long STATUS_UPDATE_INTERVAL = 5000;  // 5 seconds
const unsigned long BUTTON_DEBOUNCE = 50;           // 50ms debounce
const unsigned long TOUCH_DEBOUNCE = 100;           // 100ms touch debounce

// Task handles for ESP32 multitasking
TaskHandle_t SensorTaskHandle = NULL;
TaskHandle_t WebSocketTaskHandle = NULL;

// ==================== SETUP FUNCTION ====================

void setup() {
  Serial.begin(115200);
  Serial.println();
  Serial.println("=========================================");
  Serial.println("ESP32 Advanced Web Server Starting...");
  Serial.println("=========================================");

  // Initialize boot time
  stats.boot_time = millis();

  // Initialize GPIO pins
  initializeGPIO();

  // Initialize SPIFFS
  if (!SPIFFS.begin(true)) {
    Serial.println("Failed to mount SPIFFS");
  } else {
    Serial.println("SPIFFS mounted successfully");
  }

  // Initialize WiFi
  initializeWiFi();

  // Initialize mDNS
  if (MDNS.begin(hostname)) {
    Serial.printf("mDNS responder started: http://%s.local\n", hostname);
    MDNS.addService("http", "tcp", HTTP_PORT);
  }

  // Initialize OTA updates
  initializeOTA();

  // Initialize web server
  initializeWebServer();

  // Initialize WebSocket
  initializeWebSocket();

  // Start services
  server.begin();
  Serial.printf("HTTP server started on port %d\n", HTTP_PORT);

  // Create FreeRTOS tasks
  createTasks();

  // Print connection info
  printConnectionInfo();

  Serial.println("Setup completed successfully!");
  Serial.println("=========================================");

  // Initial LED flash to indicate ready
  flashBuiltinLED(3);
}

// ==================== MAIN LOOP ====================

void loop() {
  // Handle OTA updates
  ArduinoOTA.handle();

  // Handle mDNS
  MDNS.update();

  // Clean up WebSocket clients
  ws.cleanupClients();

  // Check button state
  if (millis() - last_button_check > BUTTON_DEBOUNCE) {
    checkButton();
    last_button_check = millis();
  }

  // Check touch sensor
  if (millis() - last_touch_check > TOUCH_DEBOUNCE) {
    checkTouch();
    last_touch_check = millis();
  }

  // Small delay to prevent watchdog reset
  delay(10);
}

// ==================== FREERTOS TASKS ====================

void createTasks() {
  // Create sensor reading task
  xTaskCreatePinnedToCore(
    sensorTask,           // Task function
    "SensorTask",         // Name
    4096,                 // Stack size
    NULL,                 // Parameters
    1,                    // Priority
    &SensorTaskHandle,    // Task handle
    0                     // Core (0 or 1)
  );

  // Create WebSocket broadcast task
  xTaskCreatePinnedToCore(
    webSocketTask,        // Task function
    "WebSocketTask",      // Name
    4096,                 // Stack size
    NULL,                 // Parameters
    1,                    // Priority
    &WebSocketTaskHandle, // Task handle
    1                     // Core (0 or 1)
  );

  Serial.println("FreeRTOS tasks created");
}

void sensorTask(void * parameter) {
  for (;;) {
    // Read sensors
    readSensors();

    // Update device status
    updateDeviceStatus();

    // Wait for next reading
    vTaskDelay(SENSOR_READ_INTERVAL / portTICK_PERIOD_MS);
  }
}

void webSocketTask(void * parameter) {
  for (;;) {
    // Broadcast status update
    broadcastStatus();

    // Wait before next broadcast
    vTaskDelay(STATUS_UPDATE_INTERVAL / portTICK_PERIOD_MS);
  }
}

// ==================== GPIO FUNCTIONS ====================

void initializeGPIO() {
  Serial.println("Initializing GPIO pins...");

  // Configure LED pins as outputs
  pinMode(BUILTIN_LED_PIN, OUTPUT);
  pinMode(EXTERNAL_LED_PIN, OUTPUT);
  pinMode(RELAY_PIN, OUTPUT);

  // Configure input pins
  pinMode(BUTTON_PIN, INPUT_PULLUP);

  // Set initial states
  digitalWrite(BUILTIN_LED_PIN, LOW);   // Turn off built-in LED
  digitalWrite(EXTERNAL_LED_PIN, LOW);  // Turn off external LED
  digitalWrite(RELAY_PIN, LOW);         // Turn off relay

  Serial.println("GPIO pins initialized");
}

void setBuiltinLED(bool state) {
  deviceState.builtin_led = state;
  digitalWrite(BUILTIN_LED_PIN, state);
  stats.gpio_toggles++;
  Serial.printf("Built-in LED: %s\n", state ? "ON" : "OFF");
}

void setExternalLED(bool state) {
  deviceState.external_led = state;
  digitalWrite(EXTERNAL_LED_PIN, state);
  stats.gpio_toggles++;
  Serial.printf("External LED: %s\n", state ? "ON" : "OFF");
}

void setRelay(bool state) {
  deviceState.relay_state = state;
  digitalWrite(RELAY_PIN, state);
  stats.gpio_toggles++;
  Serial.printf("Relay: %s\n", state ? "ON" : "OFF");
}

void flashBuiltinLED(int times) {
  for (int i = 0; i < times; i++) {
    digitalWrite(BUILTIN_LED_PIN, HIGH);  // ON
    delay(200);
    digitalWrite(BUILTIN_LED_PIN, LOW);   // OFF
    delay(200);
  }
}

void readSensors() {
  // Read analog sensor
  deviceState.sensor_value = analogRead(SENSOR_PIN);

  // Read touch sensor
  deviceState.touch_value = touchRead(TOUCH_PIN);

  // Detect touch
  bool current_touch = deviceState.touch_value < TOUCH_THRESHOLD;
  if (current_touch != deviceState.touch_detected) {
    deviceState.touch_detected = current_touch;
    if (current_touch) {
      stats.touch_events++;
      Serial.println("Touch detected!");

      // Example action: toggle built-in LED on touch
      setBuiltinLED(!deviceState.builtin_led);
    }
  }
}

void checkButton() {
  bool current_button_state = digitalRead(BUTTON_PIN);

  // Button pressed (with debounce)
  if (current_button_state == LOW && last_button_state == HIGH) {
    deviceState.button_pressed = true;
    Serial.println("Button pressed!");

    // Example action: toggle external LED
    setExternalLED(!deviceState.external_led);

    // Broadcast button press via WebSocket
    DynamicJsonDocument doc(200);
    doc["type"] = "button_press";
    doc["timestamp"] = millis();
    String message;
    serializeJson(doc, message);
    ws.textAll(message);
  } else {
    deviceState.button_pressed = false;
  }

  last_button_state = current_button_state;
}

void checkTouch() {
  // Touch checking is now handled in readSensors()
}

// ==================== WIFI FUNCTIONS ====================

void initializeWiFi() {
  Serial.println("Initializing WiFi...");

  WiFi.mode(WIFI_STA);
  WiFi.setHostname(hostname);
  WiFi.begin(ssid, password);

  Serial.printf("Connecting to %s", ssid);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 30) {
    delay(1000);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWiFi connected successfully!");
    Serial.printf("IP address: %s\n", WiFi.localIP().toString().c_str());
    Serial.printf("Hostname: %s\n", hostname);
  } else {
    Serial.println("\nFailed to connect to WiFi. Starting Access Point...");
    startAccessPoint();
  }
}

void startAccessPoint() {
  WiFi.mode(WIFI_AP);
  WiFi.softAP(ap_ssid, ap_password);

  Serial.println("Access Point started");
  Serial.printf("AP SSID: %s\n", ap_ssid);
  Serial.printf("AP Password: %s\n", ap_password);
  Serial.printf("AP IP address: %s\n", WiFi.softAPIP().toString().c_str());
}

void printConnectionInfo() {
  Serial.println("\n========== CONNECTION INFO ==========");

  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("Mode: Station (Connected to %s)\n", ssid);
    Serial.printf("IP Address: %s\n", WiFi.localIP().toString().c_str());
    Serial.printf("Gateway: %s\n", WiFi.gatewayIP().toString().c_str());
    Serial.printf("DNS: %s\n", WiFi.dnsIP().toString().c_str());
    Serial.printf("RSSI: %d dBm\n", WiFi.RSSI());
  } else {
    Serial.printf("Mode: Access Point\n");
    Serial.printf("AP SSID: %s\n", ap_ssid);
    Serial.printf("AP IP: %s\n", WiFi.softAPIP().toString().c_str());
  }

  Serial.printf("MAC Address: %s\n", WiFi.macAddress().c_str());
  Serial.printf("Hostname: %s\n", hostname);
  Serial.printf("Chip Model: %s\n", ESP.getChipModel());
  Serial.printf("Chip Revision: %d\n", ESP.getChipRevision());
  Serial.printf("CPU Frequency: %d MHz\n", ESP.getCpuFreqMHz());
  Serial.printf("Flash Size: %d MB\n", ESP.getFlashChipSize() / (1024 * 1024));
  Serial.printf("Web Interface: http://%s/\n",
    WiFi.status() == WL_CONNECTED ? WiFi.localIP().toString().c_str() : WiFi.softAPIP().toString().c_str());
  Serial.println("====================================");
}

// ==================== WEB SERVER FUNCTIONS ====================

void initializeWebServer() {
  Serial.println("Initializing web server...");

  // Serve static files from SPIFFS
  server.serveStatic("/", SPIFFS, "/").setDefaultFile("index.html");

  // Main web interface
  server.on("/", HTTP_GET, handleRoot);

  // API endpoints
  server.on("/api/status", HTTP_GET, handleAPIStatus);
  server.on("/api/device", HTTP_GET, handleAPIDevice);
  server.on("/api/stats", HTTP_GET, handleAPIStats);

  // GPIO control endpoints
  server.on("/api/led/builtin", HTTP_POST, handleBuiltinLED);
  server.on("/api/led/external", HTTP_POST, handleExternalLED);
  server.on("/api/relay", HTTP_POST, handleRelay);
  server.on("/api/gpio/toggle", HTTP_POST, handleGPIOToggle);

  // System endpoints
  server.on("/api/restart", HTTP_POST, handleRestart);
  server.on("/api/reset", HTTP_POST, handleReset);

  // Handle 404
  server.onNotFound(handleNotFound);

  Serial.println("Web server routes configured");
}

void handleRoot(AsyncWebServerRequest *request) {
  stats.total_requests++;
  stats.last_client_ip = request->client()->remoteIP().toString();
  stats.last_request_time = millis();

  String html = generateWebInterface();
  request->send(200, "text/html", html);
}

void handleAPIStatus(AsyncWebServerRequest *request) {
  stats.total_requests++;

  DynamicJsonDocument doc(1024);

  doc["status"] = "online";
  doc["timestamp"] = millis();
  doc["uptime"] = millis() - stats.boot_time;
  doc["free_heap"] = ESP.getFreeHeap();
  doc["chip_id"] = ESP.getEfuseMAC();
  doc["flash_size"] = ESP.getFlashChipSize();
  doc["cpu_freq"] = ESP.getCpuFreqMHz();
  doc["cpu_temp"] = temperatureRead();

  // WiFi info
  JsonObject wifi = doc.createNestedObject("wifi");
  wifi["connected"] = WiFi.status() == WL_CONNECTED;
  wifi["ssid"] = WiFi.SSID();
  wifi["ip"] = WiFi.localIP().toString();
  wifi["rssi"] = WiFi.RSSI();
  wifi["mac"] = WiFi.macAddress();

  // GPIO states
  JsonObject gpio = doc.createNestedObject("gpio");
  gpio["builtin_led"] = deviceState.builtin_led;
  gpio["external_led"] = deviceState.external_led;
  gpio["relay"] = deviceState.relay_state;
  gpio["button"] = deviceState.button_pressed;
  gpio["sensor"] = deviceState.sensor_value;
  gpio["touch"] = deviceState.touch_value;
  gpio["touch_detected"] = deviceState.touch_detected;

  String response;
  serializeJson(doc, response);
  request->send(200, "application/json", response);
}

void handleAPIDevice(AsyncWebServerRequest *request) {
  stats.total_requests++;

  DynamicJsonDocument doc(512);

  doc["name"] = device_name;
  doc["hostname"] = hostname;
  doc["version"] = firmware_version;
  doc["chip_model"] = ESP.getChipModel();
  doc["chip_revision"] = ESP.getChipRevision();
  doc["flash_size"] = ESP.getFlashChipSize();
  doc["flash_speed"] = ESP.getFlashChipSpeed();
  doc["cpu_freq"] = ESP.getCpuFreqMHz();
  doc["sdk_version"] = ESP.getSdkVersion();
  doc["idf_version"] = esp_get_idf_version();

  String response;
  serializeJson(doc, response);
  request->send(200, "application/json", response);
}

void handleAPIStats(AsyncWebServerRequest *request) {
  stats.total_requests++;

  DynamicJsonDocument doc(512);

  doc["boot_time"] = stats.boot_time;
  doc["uptime"] = millis() - stats.boot_time;
  doc["total_requests"] = stats.total_requests;
  doc["websocket_connections"] = stats.websocket_connections;
  doc["gpio_toggles"] = stats.gpio_toggles;
  doc["touch_events"] = stats.touch_events;
  doc["last_client_ip"] = stats.last_client_ip;
  doc["last_request_time"] = stats.last_request_time;
  doc["free_heap"] = ESP.getFreeHeap();
  doc["min_free_heap"] = ESP.getMinFreeHeap();

  String response;
  serializeJson(doc, response);
  request->send(200, "application/json", response);
}

void handleBuiltinLED(AsyncWebServerRequest *request) {
  stats.total_requests++;

  if (request->hasParam("state", true)) {
    String state = request->getParam("state", true)->value();
    bool newState = (state == "on" || state == "true" || state == "1");
    setBuiltinLED(newState);

    request->send(200, "application/json",
      "{\"success\": true, \"state\": " + String(newState ? "true" : "false") + "}");
  } else {
    request->send(400, "application/json", "{\"error\": \"Missing state parameter\"}");
  }
}

void handleExternalLED(AsyncWebServerRequest *request) {
  stats.total_requests++;

  if (request->hasParam("state", true)) {
    String state = request->getParam("state", true)->value();
    bool newState = (state == "on" || state == "true" || state == "1");
    setExternalLED(newState);

    request->send(200, "application/json",
      "{\"success\": true, \"state\": " + String(newState ? "true" : "false") + "}");
  } else {
    request->send(400, "application/json", "{\"error\": \"Missing state parameter\"}");
  }
}

void handleRelay(AsyncWebServerRequest *request) {
  stats.total_requests++;

  if (request->hasParam("state", true)) {
    String state = request->getParam("state", true)->value();
    bool newState = (state == "on" || state == "true" || state == "1");
    setRelay(newState);

    request->send(200, "application/json",
      "{\"success\": true, \"state\": " + String(newState ? "true" : "false") + "}");
  } else {
    request->send(400, "application/json", "{\"error\": \"Missing state parameter\"}");
  }
}

void handleGPIOToggle(AsyncWebServerRequest *request) {
  stats.total_requests++;

  if (request->hasParam("pin", true)) {
    String pinStr = request->getParam("pin", true)->value();

    if (pinStr == "builtin_led") {
      setBuiltinLED(!deviceState.builtin_led);
      request->send(200, "application/json", "{\"success\": true, \"pin\": \"builtin_led\"}");
    } else if (pinStr == "external_led") {
      setExternalLED(!deviceState.external_led);
      request->send(200, "application/json", "{\"success\": true, \"pin\": \"external_led\"}");
    } else if (pinStr == "relay") {
      setRelay(!deviceState.relay_state);
      request->send(200, "application/json", "{\"success\": true, \"pin\": \"relay\"}");
    } else {
      request->send(400, "application/json", "{\"error\": \"Invalid pin\"}");
    }
  } else {
    request->send(400, "application/json", "{\"error\": \"Missing pin parameter\"}");
  }
}

void handleRestart(AsyncWebServerRequest *request) {
  stats.total_requests++;
  request->send(200, "application/json", "{\"success\": true, \"message\": \"Restarting in 2 seconds\"}");
  delay(2000);
  ESP.restart();
}

void handleReset(AsyncWebServerRequest *request) {
  stats.total_requests++;

  // Reset GPIO states
  setBuiltinLED(false);
  setExternalLED(false);
  setRelay(false);

  // Reset statistics
  stats.gpio_toggles = 0;
  stats.touch_events = 0;
  stats.total_requests = 1; // This request

  request->send(200, "application/json", "{\"success\": true, \"message\": \"GPIO states reset\"}");
}

void handleNotFound(AsyncWebServerRequest *request) {
  stats.total_requests++;

  DynamicJsonDocument doc(256);
  doc["error"] = "Not Found";
  doc["path"] = request->url();
  doc["method"] = request->methodToString();

  String response;
  serializeJson(doc, response);
  request->send(404, "application/json", response);
}

// ==================== WEBSOCKET FUNCTIONS ====================

void initializeWebSocket() {
  ws.onEvent(onWebSocketEvent);
  server.addHandler(&ws);
  Serial.println("WebSocket server initialized");
}

void onWebSocketEvent(AsyncWebSocket *server, AsyncWebSocketClient *client,
                     AwsEventType type, void *arg, uint8_t *data, size_t len) {
  switch (type) {
    case WS_EVT_CONNECT:
      Serial.printf("WebSocket client #%u connected from %s\n",
        client->id(), client->remoteIP().toString().c_str());
      stats.websocket_connections++;

      // Send current status to new client
      sendStatusToClient(client);
      break;

    case WS_EVT_DISCONNECT:
      Serial.printf("WebSocket client #%u disconnected\n", client->id());
      break;

    case WS_EVT_DATA:
      handleWebSocketMessage(arg, data, len);
      break;

    case WS_EVT_PONG:
    case WS_EVT_ERROR:
      break;
  }
}

void handleWebSocketMessage(void *arg, uint8_t *data, size_t len) {
  AwsFrameInfo *info = (AwsFrameInfo*)arg;
  if (info->final && info->index == 0 && info->len == len && info->opcode == WS_TEXT) {

    DynamicJsonDocument doc(256);
    deserializeJson(doc, (char*)data);

    String command = doc["command"];

    if (command == "toggle_builtin_led") {
      setBuiltinLED(!deviceState.builtin_led);
    } else if (command == "toggle_external_led") {
      setExternalLED(!deviceState.external_led);
    } else if (command == "toggle_relay") {
      setRelay(!deviceState.relay_state);
    } else if (command == "get_status") {
      broadcastStatus();
    }
  }
}

void sendStatusToClient(AsyncWebSocketClient *client) {
  DynamicJsonDocument doc(512);

  doc["type"] = "status";
  doc["timestamp"] = millis();
  doc["builtin_led"] = deviceState.builtin_led;
  doc["external_led"] = deviceState.external_led;
  doc["relay"] = deviceState.relay_state;
  doc["button"] = deviceState.button_pressed;
  doc["sensor"] = deviceState.sensor_value;
  doc["touch"] = deviceState.touch_value;
  doc["touch_detected"] = deviceState.touch_detected;
  doc["uptime"] = millis() - stats.boot_time;
  doc["free_heap"] = ESP.getFreeHeap();
  doc["wifi_rssi"] = WiFi.RSSI();
  doc["cpu_temp"] = temperatureRead();

  String message;
  serializeJson(doc, message);
  client->text(message);
}

void broadcastStatus() {
  DynamicJsonDocument doc(512);

  doc["type"] = "status_update";
  doc["timestamp"] = millis();
  doc["builtin_led"] = deviceState.builtin_led;
  doc["external_led"] = deviceState.external_led;
  doc["relay"] = deviceState.relay_state;
  doc["button"] = deviceState.button_pressed;
  doc["sensor"] = deviceState.sensor_value;
  doc["touch"] = deviceState.touch_value;
  doc["touch_detected"] = deviceState.touch_detected;
  doc["uptime"] = millis() - stats.boot_time;
  doc["free_heap"] = ESP.getFreeHeap();
  doc["wifi_rssi"] = WiFi.RSSI();
  doc["cpu_temp"] = temperatureRead();

  String message;
  serializeJson(doc, message);
  ws.textAll(message);
}

// ==================== OTA FUNCTIONS ====================

void initializeOTA() {
  ArduinoOTA.setHostname(hostname);
  ArduinoOTA.setPassword("esp32ota");  // Change this password!

  ArduinoOTA.onStart([]() {
    String type;
    if (ArduinoOTA.getCommand() == U_FLASH) {
      type = "sketch";
    } else { // U_SPIFFS
      type = "filesystem";
    }
    Serial.println("Start updating " + type);
  });

  ArduinoOTA.onEnd([]() {
    Serial.println("\nEnd");
  });

  ArduinoOTA.onProgress([](unsigned int progress, unsigned int total) {
    Serial.printf("Progress: %u%%\r", (progress / (total / 100)));
  });

  ArduinoOTA.onError([](ota_error_t error) {
    Serial.printf("Error[%u]: ", error);
    if (error == OTA_AUTH_ERROR) {
      Serial.println("Auth Failed");
    } else if (error == OTA_BEGIN_ERROR) {
      Serial.println("Begin Failed");
    } else if (error == OTA_CONNECT_ERROR) {
      Serial.println("Connect Failed");
    } else if (error == OTA_RECEIVE_ERROR) {
      Serial.println("Receive Failed");
    } else if (error == OTA_END_ERROR) {
      Serial.println("End Failed");
    }
  });

  ArduinoOTA.begin();
  Serial.println("OTA updates enabled");
}

// ==================== UTILITY FUNCTIONS ====================

void updateDeviceStatus() {
  deviceState.uptime = millis() - stats.boot_time;
  deviceState.free_heap = ESP.getFreeHeap();
  deviceState.wifi_rssi = WiFi.RSSI();
  deviceState.ip_address = WiFi.localIP().toString();
  deviceState.mac_address = WiFi.macAddress();
  deviceState.cpu_temperature = temperatureRead();
  deviceState.last_update = millis();
}

String generateWebInterface() {
  String html = R"rawliteral(
<!DOCTYPE html>
<html>
<head>
    <title>ESP32 Web Server</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(45deg, #FF6B6B, #4ECDC4);
            color: white;
            padding: 30px;
            text-align: center;
        }
        .header h1 { font-size: 2.5em; margin-bottom: 10px; }
        .header p { opacity: 0.9; font-size: 1.1em; }
        .content { padding: 30px; }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .card {
            background: #f8f9fa;
            border-radius: 10px;
            padding: 20px;
            border: 1px solid #e9ecef;
        }
        .card h3 {
            color: #495057;
            margin-bottom: 15px;
            font-size: 1.3em;
        }
        .status-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 15px;
            margin-top
