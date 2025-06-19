/*
 * ESP8266 Simple Web Server with GPIO Control
 * ===========================================
 *
 * A simplified, working web server for ESP8266 modules with GPIO control.
 * This firmware provides a clean web interface for controlling LEDs and relays.
 *
 * Features:
 * - WiFi connection with fallback AP mode
 * - Simple web server on port 80
 * - GPIO control (LEDs, relay)
 * - JSON API endpoints
 * - Mobile-responsive interface
 * - Serial debugging
 *
 * Hardware connections:
 * - Built-in LED: GPIO2 (D4) - inverted logic
 * - External LED: GPIO5 (D1)
 * - Button: GPIO4 (D2) with pull-up
 * - Relay: GPIO12 (D6)
 *
 * Author: ESP Deployment System
 * Version: 1.0.0
 */

#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>
#include <ESP8266mDNS.h>

// ==================== CONFIGURATION ====================

// WiFi Configuration - WILL BE REPLACED BY SCRIPT
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

// Access Point Configuration (fallback)
const char* ap_ssid = "ESP8266-WebServer";
const char* ap_password = "12345678";

// Device Configuration
const char* hostname = "esp8266-webserver";
const char* device_name = "ESP8266 Simple Web Server";
const char* firmware_version = "1.0.0";

// GPIO Pin Definitions
const int BUILTIN_LED_PIN = 2;     // D4 - Built-in LED (inverted)
const int EXTERNAL_LED_PIN = 5;    // D1 - External LED
const int BUTTON_PIN = 4;          // D2 - Button with pull-up
const int RELAY_PIN = 12;          // D6 - Relay control

// ==================== GLOBAL VARIABLES ====================

ESP8266WebServer server(80);

// Device state
bool builtin_led_state = false;
bool external_led_state = false;
bool relay_state = false;
bool button_pressed = false;
int sensor_value = 0;

// Statistics
unsigned long boot_time = 0;
unsigned long total_requests = 0;
unsigned long gpio_toggles = 0;

// Timing
unsigned long last_button_check = 0;
bool last_button_state = HIGH;
const unsigned long BUTTON_DEBOUNCE = 50;

// ==================== SETUP FUNCTION ====================

void setup() {
  Serial.begin(115200);
  Serial.println();
  Serial.println("=========================================");
  Serial.println("ESP8266 Simple Web Server Starting...");
  Serial.println("=========================================");

  boot_time = millis();

  // Initialize GPIO
  initializeGPIO();

  // Initialize WiFi
  initializeWiFi();

  // Initialize mDNS
  if (MDNS.begin(hostname)) {
    Serial.printf("mDNS responder started: http://%s.local\n", hostname);
  }

  // Initialize web server
  initializeWebServer();

  // Start server
  server.begin();
  Serial.println("HTTP server started on port 80");

  // Print connection info
  printConnectionInfo();

  Serial.println("Setup completed successfully!");
  Serial.println("=========================================");

  // Flash LED to indicate ready
  flashBuiltinLED(3);
}

// ==================== MAIN LOOP ====================

void loop() {
  // Handle web server
  server.handleClient();

  // Handle mDNS
  MDNS.update();

  // Check button
  if (millis() - last_button_check > BUTTON_DEBOUNCE) {
    checkButton();
    last_button_check = millis();
  }

  // Read sensor
  sensor_value = analogRead(A0);

  // Small delay
  delay(10);
}

// ==================== GPIO FUNCTIONS ====================

void initializeGPIO() {
  Serial.println("Initializing GPIO pins...");

  // Configure pins
  pinMode(BUILTIN_LED_PIN, OUTPUT);
  pinMode(EXTERNAL_LED_PIN, OUTPUT);
  pinMode(RELAY_PIN, OUTPUT);
  pinMode(BUTTON_PIN, INPUT_PULLUP);

  // Set initial states
  setBuiltinLED(false);
  setExternalLED(false);
  setRelay(false);

  Serial.println("GPIO pins initialized");
}

void setBuiltinLED(bool state) {
  builtin_led_state = state;
  digitalWrite(BUILTIN_LED_PIN, !state);  // Inverted logic
  gpio_toggles++;
  Serial.printf("Built-in LED: %s\n", state ? "ON" : "OFF");
}

void setExternalLED(bool state) {
  external_led_state = state;
  digitalWrite(EXTERNAL_LED_PIN, state);
  gpio_toggles++;
  Serial.printf("External LED: %s\n", state ? "ON" : "OFF");
}

void setRelay(bool state) {
  relay_state = state;
  digitalWrite(RELAY_PIN, state);
  gpio_toggles++;
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

void checkButton() {
  bool current_state = digitalRead(BUTTON_PIN);

  if (current_state == LOW && last_button_state == HIGH) {
    button_pressed = true;
    Serial.println("Button pressed!");

    // Toggle external LED on button press
    setExternalLED(!external_led_state);

    delay(10); // Small delay to show button was pressed
    button_pressed = false;
  }

  last_button_state = current_state;
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

  // Main page
  server.on("/", handleRoot);

  // API endpoints
  server.on("/api/status", handleAPIStatus);
  server.on("/api/builtin_led", HTTP_POST, handleBuiltinLED);
  server.on("/api/external_led", HTTP_POST, handleExternalLED);
  server.on("/api/relay", HTTP_POST, handleRelay);
  server.on("/api/toggle", HTTP_POST, handleToggle);
  server.on("/api/restart", HTTP_POST, handleRestart);

  // 404 handler
  server.onNotFound(handleNotFound);

  Serial.println("Web server routes configured");
}

void handleRoot() {
  total_requests++;

  String html = generateWebPage();
  server.send(200, "text/html", html);
}

void handleAPIStatus() {
  total_requests++;

  String json = "{";
  json += "\"status\":\"online\",";
  json += "\"uptime\":" + String(millis() - boot_time) + ",";
  json += "\"free_heap\":" + String(ESP.getFreeHeap()) + ",";
  json += "\"builtin_led\":" + String(builtin_led_state ? "true" : "false") + ",";
  json += "\"external_led\":" + String(external_led_state ? "true" : "false") + ",";
  json += "\"relay\":" + String(relay_state ? "true" : "false") + ",";
  json += "\"button\":" + String(button_pressed ? "true" : "false") + ",";
  json += "\"sensor\":" + String(sensor_value) + ",";
  json += "\"wifi_rssi\":" + String(WiFi.RSSI()) + ",";
  json += "\"total_requests\":" + String(total_requests) + ",";
  json += "\"gpio_toggles\":" + String(gpio_toggles);
  json += "}";

  server.send(200, "application/json", json);
}

void handleBuiltinLED() {
  total_requests++;

  if (server.hasArg("state")) {
    String state = server.arg("state");
    bool newState = (state == "on" || state == "true" || state == "1");
    setBuiltinLED(newState);

    server.send(200, "application/json", "{\"success\":true,\"state\":" + String(newState ? "true" : "false") + "}");
  } else {
    server.send(400, "application/json", "{\"error\":\"Missing state parameter\"}");
  }
}

void handleExternalLED() {
  total_requests++;

  if (server.hasArg("state")) {
    String state = server.arg("state");
    bool newState = (state == "on" || state == "true" || state == "1");
    setExternalLED(newState);

    server.send(200, "application/json", "{\"success\":true,\"state\":" + String(newState ? "true" : "false") + "}");
  } else {
    server.send(400, "application/json", "{\"error\":\"Missing state parameter\"}");
  }
}

void handleRelay() {
  total_requests++;

  if (server.hasArg("state")) {
    String state = server.arg("state");
    bool newState = (state == "on" || state == "true" || state == "1");
    setRelay(newState);

    server.send(200, "application/json", "{\"success\":true,\"state\":" + String(newState ? "true" : "false") + "}");
  } else {
    server.send(400, "application/json", "{\"error\":\"Missing state parameter\"}");
  }
}

void handleToggle() {
  total_requests++;

  if (server.hasArg("pin")) {
    String pin = server.arg("pin");

    if (pin == "builtin_led") {
      setBuiltinLED(!builtin_led_state);
      server.send(200, "application/json", "{\"success\":true,\"pin\":\"builtin_led\"}");
    } else if (pin == "external_led") {
      setExternalLED(!external_led_state);
      server.send(200, "application/json", "{\"success\":true,\"pin\":\"external_led\"}");
    } else if (pin == "relay") {
      setRelay(!relay_state);
      server.send(200, "application/json", "{\"success\":true,\"pin\":\"relay\"}");
    } else {
      server.send(400, "application/json", "{\"error\":\"Invalid pin\"}");
    }
  } else {
    server.send(400, "application/json", "{\"error\":\"Missing pin parameter\"}");
  }
}

void handleRestart() {
  total_requests++;
  server.send(200, "application/json", "{\"success\":true,\"message\":\"Restarting in 2 seconds\"}");
  delay(2000);
  ESP.restart();
}

void handleNotFound() {
  total_requests++;
  server.send(404, "application/json", "{\"error\":\"Not Found\",\"path\":\"" + server.uri() + "\"}");
}

// ==================== HTML GENERATION ====================

String generateWebPage() {
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
            font-family: Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(45deg, #2196F3, #21CBF3);
            color: white;
            padding: 30px;
            text-align: center;
        }
        .header h1 { font-size: 2.2em; margin-bottom: 10px; }
        .content { padding: 30px; }
        .status-card {
            background: #f8f9fa;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
            border-left: 4px solid #2196F3;
        }
        .controls {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }
        .control-item {
            background: #f8f9fa;
            border-radius: 8px;
            padding: 20px;
            text-align: center;
            border: 1px solid #e9ecef;
        }
        .control-item h3 {
            margin-bottom: 15px;
            color: #495057;
        }
        .btn {
            padding: 10px 20px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 1em;
            margin: 5px;
            transition: all 0.3s;
        }
        .btn-primary { background: #007bff; color: white; }
        .btn-success { background: #28a745; color: white; }
        .btn-danger { background: #dc3545; color: white; }
        .btn-warning { background: #ffc107; color: #212529; }
        .btn:hover { transform: translateY(-2px); box-shadow: 0 4px 8px rgba(0,0,0,0.2); }
        .led-indicator {
            width: 15px;
            height: 15px;
            border-radius: 50%;
            display: inline-block;
            margin-left: 10px;
            border: 2px solid #333;
        }
        .led-on { background: #28a745; box-shadow: 0 0 10px #28a745; }
        .led-off { background: #6c757d; }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }
        .stat-item {
            text-align: center;
            padding: 15px;
            background: white;
            border-radius: 8px;
            border: 1px solid #e9ecef;
        }
        .stat-value {
            font-size: 1.5em;
            font-weight: bold;
            color: #495057;
        }
        .stat-label {
            color: #6c757d;
            font-size: 0.9em;
        }
        @media (max-width: 600px) {
            .controls { grid-template-columns: 1fr; }
            .stats { grid-template-columns: repeat(2, 1fr); }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🌐 ESP8266 Web Server</h1>
            <p>Simple GPIO Control Interface</p>
        </div>

        <div class="content">
            <div class="status-card">
                <h3>📊 Device Status</h3>
                <div class="stats">
                    <div class="stat-item">
                        <div class="stat-value" id="uptime">0s</div>
                        <div class="stat-label">Uptime</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value" id="memory">0KB</div>
                        <div class="stat-label">Free Memory</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value" id="wifi">0dBm</div>
                        <div class="stat-label">WiFi Signal</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value" id="sensor">0</div>
                        <div class="stat-label">Sensor</div>
                    </div>
                </div>
            </div>

            <div class="controls">
                <div class="control-item">
                    <h3>Built-in LED <span class="led-indicator" id="builtinLed"></span></h3>
                    <button class="btn btn-primary" onclick="toggleGPIO('builtin_led')">Toggle</button>
                    <button class="btn btn-success" onclick="setGPIO('builtin_led', 'on')">ON</button>
                    <button class="btn btn-danger" onclick="setGPIO('builtin_led', 'off')">OFF</button>
                </div>

                <div class="control-item">
                    <h3>External LED <span class="led-indicator" id="externalLed"></span></h3>
                    <button class="btn btn-primary" onclick="toggleGPIO('external_led')">Toggle</button>
                    <button class="btn btn-success" onclick="setGPIO('external_led', 'on')">ON</button>
                    <button class="btn btn-danger" onclick="setGPIO('external_led', 'off')">OFF</button>
                </div>

                <div class="control-item">
                    <h3>Relay <span class="led-indicator" id="relay"></span></h3>
                    <button class="btn btn-primary" onclick="toggleGPIO('relay')">Toggle</button>
                    <button class="btn btn-success" onclick="setGPIO('relay', 'on')">ON</button>
                    <button class="btn btn-danger" onclick="setGPIO('relay', 'off')">OFF</button>
                </div>
            </div>

            <div class="status-card">
                <h3>⚡ Quick Actions</h3>
                <button class="btn btn-primary" onclick="refreshStatus()">🔄 Refresh</button>
                <button class="btn btn-success" onclick="allOn()">💡 All ON</button>
                <button class="btn btn-danger" onclick="allOff()">💡 All OFF</button>
                <button class="btn btn-warning" onclick="restart()">🔄 Restart</button>
            </div>
        </div>
    </div>

    <script>
        // Update status every 5 seconds
        setInterval(refreshStatus, 5000);

        // Initial load
        refreshStatus();

        function refreshStatus() {
            fetch('/api/status')
                .then(response => response.json())
                .then(data => {
                    // Update uptime
                    const uptimeSeconds = Math.floor(data.uptime / 1000);
                    const hours = Math.floor(uptimeSeconds / 3600);
                    const minutes = Math.floor((uptimeSeconds % 3600) / 60);
                    const seconds = uptimeSeconds % 60;
                    document.getElementById('uptime').textContent =
                        hours > 0 ? `${hours}h ${minutes}m` : `${minutes}m ${seconds}s`;

                    // Update other stats
                    document.getElementById('memory').textContent = Math.round(data.free_heap / 1024) + 'KB';
                    document.getElementById('wifi').textContent = data.wifi_rssi + 'dBm';
                    document.getElementById('sensor').textContent = data.sensor;

                    // Update LED indicators
                    updateLED('builtinLed', data.builtin_led);
                    updateLED('externalLed', data.external_led);
                    updateLED('relay', data.relay);
                })
                .catch(error => console.error('Error:', error));
        }

        function updateLED(elementId, state) {
            const element = document.getElementById(elementId);
            element.className = 'led-indicator ' + (state ? 'led-on' : 'led-off');
        }

        function toggleGPIO(pin) {
            fetch('/api/toggle', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: 'pin=' + pin
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    refreshStatus();
                    showMessage('Toggled ' + pin.replace('_', ' '));
                }
            })
            .catch(error => showMessage('Error: ' + error, 'error'));
        }

        function setGPIO(pin, state) {
            const endpoint = pin === 'builtin_led' ? '/api/builtin_led' :
                           pin === 'external_led' ? '/api/external_led' : '/api/relay';

            fetch(endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: 'state=' + state
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    refreshStatus();
                    showMessage(pin.replace('_', ' ') + ' turned ' + state.toUpperCase());
                }
            })
            .catch(error => showMessage('Error: ' + error, 'error'));
        }

        function allOn() {
            setGPIO('builtin_led', 'on');
            setTimeout(() => setGPIO('external_led', 'on'), 100);
            setTimeout(() => setGPIO('relay', 'on'), 200);
        }

        function allOff() {
            setGPIO('builtin_led', 'off');
            setTimeout(() => setGPIO('external_led', 'off'), 100);
            setTimeout(() => setGPIO('relay', 'off'), 200);
        }

        function restart() {
            if (confirm('Are you sure you want to restart the ESP8266?')) {
                fetch('/api/restart', { method: 'POST' })
                    .then(() => showMessage('Restarting ESP8266...'))
                    .catch(error => showMessage('Error: ' + error, 'error'));
            }
        }

        function showMessage(message, type = 'success') {
            const div = document.createElement('div');
            div.style.cssText = `
                position: fixed; top: 20px; right: 20px; z-index: 1000;
                padding: 15px 20px; border-radius: 5px; color: white; font-weight: bold;
                background: ${type === 'error' ? '#dc3545' : '#28a745'};
            `;
            div.textContent = message;
            document.body.appendChild(div);

            setTimeout(() => div.remove(), 3000);
        }
    </script>
</body>
</html>
)rawliteral";

  return html;
}
