/*
 * ESP8266 Advanced Web Server with GPIO Control
 * ==============================================
 *
 * This firmware provides a complete web server solution for ESP8266 modules
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
 *
 * Hardware connections:
 * - Built-in LED: GPIO2 (D4)
 * - External LED: GPIO5 (D1)
 * - Button: GPIO4 (D2) with pull-up
 * - Relay: GPIO12 (D6)
 * - Sensor: GPIO14 (D5)
 *
 * Author: ESP Deployment System
 * Version: 1.0.0
 */

#include <ESP8266WiFi.h>
#include <ESPAsyncWebServer.h>
#include <ArduinoJson.h>
#include <LittleFS.h>
#include <ArduinoOTA.h>
#include <ESP8266mDNS.h>

// ==================== CONFIGURATION ====================

// WiFi Configuration
const char* ssid = "YOUR_WIFI_SSID";           // Replace with your WiFi SSID
const char* password = "YOUR_WIFI_PASSWORD";   // Replace with your WiFi password

// Access Point Configuration (fallback)
const char* ap_ssid = "ESP8266-WebServer";
const char* ap_password = "12345678";

// Device Configuration
const char* hostname = "esp8266-webserver";
const char* device_name = "ESP8266 Web Server";
const char* firmware_version = "1.0.0";

// GPIO Pin Definitions
const int BUILTIN_LED_PIN = 2;     // D4 - Built-in LED (inverted)
const int EXTERNAL_LED_PIN = 5;    // D1 - External LED
const int BUTTON_PIN = 4;          // D2 - Button with pull-up
const int RELAY_PIN = 12;          // D6 - Relay control
const int SENSOR_PIN = 14;         // D5 - Sensor input

// Server Configuration
const int HTTP_PORT = 80;
const int WEBSOCKET_PORT = 81;

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
  unsigned long uptime = 0;
  int free_heap = 0;
  int wifi_rssi = 0;
  String ip_address = "";
  String mac_address = "";
  unsigned long last_update = 0;
} deviceState;

// Statistics
struct Statistics {
  unsigned long boot_time = 0;
  unsigned long total_requests = 0;
  unsigned long websocket_connections = 0;
  unsigned long gpio_toggles = 0;
  String last_client_ip = "";
  unsigned long last_request_time = 0;
} stats;

// Timing variables
unsigned long last_sensor_read = 0;
unsigned long last_status_update = 0;
unsigned long last_button_check = 0;
bool last_button_state = HIGH;

// Constants
const unsigned long SENSOR_READ_INTERVAL = 1000;    // 1 second
const unsigned long STATUS_UPDATE_INTERVAL = 5000;  // 5 seconds
const unsigned long BUTTON_DEBOUNCE = 50;           // 50ms debounce

// ==================== SETUP FUNCTION ====================

void setup() {
  Serial.begin(115200);
  Serial.println();
  Serial.println("=========================================");
  Serial.println("ESP8266 Advanced Web Server Starting...");
  Serial.println("=========================================");

  // Initialize boot time
  stats.boot_time = millis();

  // Initialize GPIO pins
  initializeGPIO();

  // Initialize file system
  if (!LittleFS.begin()) {
    Serial.println("Failed to mount file system");
  } else {
    Serial.println("File system mounted successfully");
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

  // Read sensors periodically
  if (millis() - last_sensor_read > SENSOR_READ_INTERVAL) {
    readSensors();
    last_sensor_read = millis();
  }

  // Update device status periodically
  if (millis() - last_status_update > STATUS_UPDATE_INTERVAL) {
    updateDeviceStatus();
    broadcastStatus();
    last_status_update = millis();
  }

  // Check button state
  if (millis() - last_button_check > BUTTON_DEBOUNCE) {
    checkButton();
    last_button_check = millis();
  }

  // Small delay to prevent watchdog reset
  delay(10);
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
  pinMode(SENSOR_PIN, INPUT);

  // Set initial states
  digitalWrite(BUILTIN_LED_PIN, HIGH);  // Turn off built-in LED (inverted)
  digitalWrite(EXTERNAL_LED_PIN, LOW);  // Turn off external LED
  digitalWrite(RELAY_PIN, LOW);         // Turn off relay

  Serial.println("GPIO pins initialized");
}

void setBuiltinLED(bool state) {
  deviceState.builtin_led = state;
  digitalWrite(BUILTIN_LED_PIN, !state);  // Inverted logic
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
    digitalWrite(BUILTIN_LED_PIN, LOW);   // ON (inverted)
    delay(200);
    digitalWrite(BUILTIN_LED_PIN, HIGH);  // OFF (inverted)
    delay(200);
  }
}

void readSensors() {
  // Read analog sensor
  deviceState.sensor_value = analogRead(A0);

  // Read digital sensor
  // deviceState.sensor_value = digitalRead(SENSOR_PIN);
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

// ==================== WIFI FUNCTIONS ====================

void initializeWiFi() {
  Serial.println("Initializing WiFi...");

  WiFi.mode(WIFI_STA);
  WiFi.hostname(hostname);
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
  Serial.printf("Web Interface: http://%s/\n",
    WiFi.status() == WL_CONNECTED ? WiFi.localIP().toString().c_str() : WiFi.softAPIP().toString().c_str());
  Serial.println("====================================");
}

// ==================== WEB SERVER FUNCTIONS ====================

void initializeWebServer() {
  Serial.println("Initializing web server...");

  // Serve static files from LittleFS
  server.serveStatic("/", LittleFS, "/").setDefaultFile("index.html");

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
  doc["chip_id"] = ESP.getChipId();
  doc["flash_size"] = ESP.getFlashChipSize();
  doc["cpu_freq"] = ESP.getCpuFreqMHz();

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
  doc["chip_id"] = ESP.getChipId();
  doc["flash_size"] = ESP.getFlashChipSize();
  doc["flash_speed"] = ESP.getFlashChipSpeed();
  doc["cpu_freq"] = ESP.getCpuFreqMHz();
  doc["core_version"] = ESP.getCoreVersion();
  doc["sdk_version"] = ESP.getSdkVersion();

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
  doc["last_client_ip"] = stats.last_client_ip;
  doc["last_request_time"] = stats.last_request_time;
  doc["free_heap"] = ESP.getFreeHeap();
  doc["heap_fragmentation"] = ESP.getHeapFragmentation();

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
  doc["uptime"] = millis() - stats.boot_time;
  doc["free_heap"] = ESP.getFreeHeap();
  doc["wifi_rssi"] = WiFi.RSSI();

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
  doc["uptime"] = millis() - stats.boot_time;
  doc["free_heap"] = ESP.getFreeHeap();
  doc["wifi_rssi"] = WiFi.RSSI();

  String message;
  serializeJson(doc, message);
  ws.textAll(message);
}

// ==================== OTA FUNCTIONS ====================

void initializeOTA() {
  ArduinoOTA.setHostname(hostname);
  ArduinoOTA.setPassword("esp8266ota");  // Change this password!

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
  deviceState.last_update = millis();
}

String generateWebInterface() {
  String html = R"rawliteral(
<!DOCTYPE html>
<html>
<head>
    <title>ESP8266 Web Server</title>
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
            max-width: 1000px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(45deg, #2196F3, #21CBF3);
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
            margin-top: 15px;
        }
        .status-item {
            text-align: center;
            padding: 15px;
            background: white;
            border-radius: 8px;
            border: 2px solid #e9ecef;
        }
        .status-value {
            font-size: 1.5em;
            font-weight: bold;
            color: #495057;
        }
        .status-label {
            color: #6c757d;
            font-size: 0.9em;
            margin-top: 5px;
        }
        .control-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
        }
        .control-item {
            background: white;
            border-radius: 8px;
            padding: 20px;
            text-align: center;
            border: 2px solid #e9ecef;
        }
        .control-item h4 {
            margin-bottom: 15px;
            color: #495057;
        }
        .btn {
            padding: 12px 24px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 1em;
            font-weight: 500;
            transition: all 0.3s ease;
            margin: 5px;
        }
        .btn-primary { background: #007bff; color: white; }
        .btn-success { background: #28a745; color: white; }
        .btn-danger { background: #dc3545; color: white; }
        .btn-warning { background: #ffc107; color: #212529; }
        .btn:hover { transform: translateY(-2px); box-shadow: 0 4px 8px rgba(0,0,0,0.2); }
        .btn:active { transform: translateY(0); }
        .led-indicator {
            width: 20px;
            height: 20px;
            border-radius: 50%;
            display: inline-block;
            margin-left: 10px;
            border: 2px solid #333;
        }
        .led-on { background: #28a745; box-shadow: 0 0 10px #28a745; }
        .led-off { background: #6c757d; }
        .connection-status {
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 10px 15px;
            border-radius: 20px;
            color: white;
            font-weight: bold;
            z-index: 1000;
        }
        .connected { background: #28a745; }
        .disconnected { background: #dc3545; }
        @media (max-width: 768px) {
            .grid { grid-template-columns: 1fr; }
            .control-grid { grid-template-columns: 1fr; }
            .status-grid { grid-template-columns: repeat(2, 1fr); }
        }
    </style>
</head>
<body>
    <div class="connection-status" id="connectionStatus">
        <span id="connectionText">Connecting...</span>
    </div>

    <div class="container">
        <div class="header">
            <h1>🌐 ESP8266 Web Server</h1>
            <p>Advanced GPIO Control & Monitoring System</p>
        </div>

        <div class="content">
            <div class="grid">
                <!-- Device Status Card -->
                <div class="card">
                    <h3>📊 Device Status</h3>
                    <div class="status-grid">
                        <div class="status-item">
                            <div class="status-value" id="uptime">0s</div>
                            <div class="status-label">Uptime</div>
                        </div>
                        <div class="status-item">
                            <div class="status-value" id="freeHeap">0</div>
                            <div class="status-label">Free Heap</div>
                        </div>
                        <div class="status-item">
                            <div class="status-value" id="wifiRssi">0</div>
                            <div class="status-label">WiFi RSSI</div>
                        </div>
                        <div class="status-item">
                            <div class="status-value" id="sensorValue">0</div>
                            <div class="status-label">Sensor</div>
                        </div>
                    </div>
                </div>

                <!-- GPIO Controls Card -->
                <div class="card">
                    <h3>🔧 GPIO Controls</h3>
                    <div class="control-grid">
                        <div class="control-item">
                            <h4>Built-in LED <span class="led-indicator" id="builtinLedIndicator"></span></h4>
                            <button class="btn btn-primary" onclick="toggleBuiltinLED()">Toggle</button>
                        </div>
                        <div class="control-item">
                            <h4>External LED <span class="led-indicator" id="externalLedIndicator"></span></h4>
                            <button class="btn btn-success" onclick="toggleExternalLED()">Toggle</button>
                        </div>
                        <div class="control-item">
                            <h4>Relay <span class="led-indicator" id="relayIndicator"></span></h4>
                            <button class="btn btn-warning" onclick="toggleRelay()">Toggle</button>
                        </div>
                        <div class="control-item">
                            <h4>Button Status</h4>
                            <div class="status-value" id="buttonStatus">Released</div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Quick Actions -->
            <div class="card">
                <h3>⚡ Quick Actions</h3>
                <button class="btn btn-primary" onclick="refreshStatus()">🔄 Refresh</button>
                <button class="btn btn-success" onclick="allLEDsOn()">💡 All LEDs On</button>
                <button class="btn btn-danger" onclick="allLEDsOff()">💡 All LEDs Off</button>
                <button class="btn btn-warning" onclick="resetDevice()">🔄 Reset GPIO</button>
                <button class="btn btn-danger" onclick="restartDevice()">🔄 Restart Device</button>
            </div>

            <!-- API Information -->
            <div class="card">
                <h3>🔗 API Endpoints</h3>
                <div style="background: white; padding: 15px; border-radius: 8px; font-family: monospace; font-size: 0.9em;">
                    <div><strong>GET /api/status</strong> - Device status</div>
                    <div><strong>POST /api/led/builtin</strong> - Control built-in LED</div>
                    <div><strong>POST /api/led/external</strong> - Control external LED</div>
                    <div><strong>POST /api/relay</strong> - Control relay</div>
                    <div><strong>POST /api/gpio/toggle</strong> - Toggle GPIO pin</div>
                    <div><strong>POST /api/restart</strong> - Restart device</div>
                </div>
            </div>
        </div>
    </div>

    <script>
        let socket;
        let connectionStatus = document.getElementById('connectionStatus');
        let connectionText = document.getElementById('connectionText');

        // Initialize WebSocket connection
        function initWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = protocol + '//' + window.location.host + '/ws';

            socket = new WebSocket(wsUrl);

            socket.onopen = function(event) {
                connectionStatus.className = 'connection-status connected';
                connectionText.textContent = 'Connected';
                console.log('WebSocket connected');
            };

            socket.onclose = function(event) {
                connectionStatus.className = 'connection-status disconnected';
                connectionText.textContent = 'Disconnected';
                console.log('WebSocket disconnected');
                // Try to reconnect after 3 seconds
                setTimeout(initWebSocket, 3000);
            };

            socket.onmessage = function(event) {
                const data = JSON.parse(event.data);
                handleWebSocketMessage(data);
            };

            socket.onerror = function(error) {
                console.error('WebSocket error:', error);
                connectionStatus.className = 'connection-status disconnected';
                connectionText.textContent = 'Error';
            };
        }

        function handleWebSocketMessage(data) {
            if (data.type === 'status' || data.type === 'status_update') {
                updateStatus(data);
            } else if (data.type === 'button_press') {
                showNotification('Button pressed!');
            }
        }

        function updateStatus(data) {
            // Update uptime
            const uptimeSeconds = Math.floor(data.uptime / 1000);
            const hours = Math.floor(uptimeSeconds / 3600);
            const minutes = Math.floor((uptimeSeconds % 3600) / 60);
            const seconds = uptimeSeconds % 60;
            document.getElementById('uptime').textContent =
                hours > 0 ? `${hours}h ${minutes}m ${seconds}s` : `${minutes}m ${seconds}s`;

            // Update other status values
            document.getElementById('freeHeap').textContent = (data.free_heap / 1024).toFixed(1) + 'KB';
            document.getElementById('wifiRssi').textContent = data.wifi_rssi + 'dBm';
            document.getElementById('sensorValue').textContent = data.sensor;

            // Update LED indicators
            updateLEDIndicator('builtinLedIndicator', data.builtin_led);
            updateLEDIndicator('externalLedIndicator', data.external_led);
            updateLEDIndicator('relayIndicator', data.relay);

            // Update button status
            document.getElementById('buttonStatus').textContent = data.button ? 'Pressed' : 'Released';
        }

        function updateLEDIndicator(elementId, state) {
            const indicator = document.getElementById(elementId);
            indicator.className = 'led-indicator ' + (state ? 'led-on' : 'led-off');
        }

        // GPIO Control Functions
        async function toggleBuiltinLED() {
            try {
                const response = await fetch('/api/gpio/toggle', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                    body: 'pin=builtin_led'
                });
                const result = await response.json();
                if (result.success) {
                    showNotification('Built-in LED toggled');
                }
            } catch (error) {
                showNotification('Error: ' + error.message, 'error');
            }
        }

        async function toggleExternalLED() {
            try {
                const response = await fetch('/api/gpio/toggle', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                    body: 'pin=external_led'
                });
                const result = await response.json();
                if (result.success) {
                    showNotification('External LED toggled');
                }
            } catch (error) {
                showNotification('Error: ' + error.message, 'error');
            }
        }

        async function toggleRelay() {
            try {
                const response = await fetch('/api/gpio/toggle', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                    body: 'pin=relay'
                });
                const result = await response.json();
                if (result.success) {
                    showNotification('Relay toggled');
                }
            } catch (error) {
                showNotification('Error: ' + error.message, 'error');
            }
        }

        async function allLEDsOn() {
            try {
                await fetch('/api/led/builtin', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                    body: 'state=on'
                });
                await fetch('/api/led/external', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                    body: 'state=on'
                });
                showNotification('All LEDs turned on');
            } catch (error) {
                showNotification('Error: ' + error.message, 'error');
            }
        }

        async function allLEDsOff() {
            try {
                await fetch('/api/led/builtin', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                    body: 'state=off'
                });
                await fetch('/api/led/external', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                    body: 'state=off'
                });
                showNotification('All LEDs turned off');
            } catch (error) {
                showNotification('Error: ' + error.message, 'error');
            }
        }

        async function resetDevice() {
            try {
                const response = await fetch('/api/reset', { method: 'POST' });
                const result = await response.json();
                if (result.success) {
                    showNotification('GPIO states reset');
                }
            } catch (error) {
                showNotification('Error: ' + error.message, 'error');
            }
        }

        async function restartDevice() {
            if (confirm('Are you sure you want to restart the device?')) {
                try {
                    await fetch('/api/restart', { method: 'POST' });
                    showNotification('Device restarting...');
                } catch (error) {
                    showNotification('Error: ' + error.message, 'error');
                }
            }
        }

        async function refreshStatus() {
            try {
                const response = await fetch('/api/status');
                const data = await response.json();
                updateStatus(data.gpio);
                showNotification('Status refreshed');
            } catch (error) {
                showNotification('Error: ' + error.message, 'error');
            }
        }

        // Utility Functions
        function showNotification(message, type = 'success') {
            const notification = document.createElement('div');
            notification.style.cssText = `
                position: fixed;
                top: 70px;
                right: 20px;
                padding: 15px 20px;
                border-radius: 5px;
                color: white;
                font-weight: bold;
                z-index: 1001;
                animation: slideIn 0.3s ease-out;
                background: ${type === 'error' ? '#dc3545' : '#28a745'};
            `;
            notification.textContent = message;
            document.body.appendChild(notification);

            setTimeout(() => {
                notification.remove();
            }, 3000);
        }

        // Add CSS animation
        const style = document.createElement('style');
        style.textContent = `
            @keyframes slideIn {
                from { transform: translateX(100%); opacity: 0; }
                to { transform: translateX(0); opacity: 1; }
            }
        `;
        document.head.appendChild(style);

        // Initialize WebSocket on page load
        window.addEventListener('load', function() {
            initWebSocket();
            refreshStatus();
        });

        // Send periodic status requests via WebSocket
        setInterval(() => {
            if (socket && socket.readyState === WebSocket.OPEN) {
                socket.send(JSON.stringify({ command: 'get_status' }));
            }
        }, 5000);
    </script>
</body>
</html>
)rawliteral";

  return html;
}
