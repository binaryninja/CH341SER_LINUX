# Arduino Firmware Setup Guide for ESP Web Server

This guide will help you flash custom Arduino firmware to your ESP8266/ESP32 module to create a powerful web server with GPIO control.

## 🎯 Why Arduino Firmware?

The AT firmware is limited - it can only handle basic commands. With Arduino firmware, you get:
- **Full web server** with HTML interface
- **Real-time GPIO control** (LEDs, relays, sensors)
- **WebSocket support** for live updates
- **API endpoints** for automation
- **Mobile-responsive interface**
- **OTA updates** for remote firmware updates

## 📋 Prerequisites

### Hardware Required
- ESP8266 or ESP32 module
- CH340/CH341 USB-to-serial converter (already connected)
- Breadboard and jumper wires
- LEDs, resistors, buttons (optional for testing)

### Software Required
- Arduino IDE 2.0 or newer
- ESP8266/ESP32 board packages
- Required libraries

## 🔧 Arduino IDE Setup

### 1. Install Arduino IDE
Download from: https://www.arduino.cc/en/software

### 2. Add ESP Board Packages

**For ESP8266:**
1. Open Arduino IDE
2. Go to `File` → `Preferences`
3. Add this URL to "Additional Board Manager URLs":
   ```
   https://arduino.esp8266.com/stable/package_esp8266com_index.json
   ```
4. Go to `Tools` → `Board` → `Board Manager`
5. Search for "ESP8266" and install "esp8266 by ESP8266 Community"

**For ESP32:**
1. Add this URL to Board Manager URLs:
   ```
   https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
   ```
2. Search for "ESP32" and install "esp32 by Espressif Systems"

### 3. Install Required Libraries

Go to `Tools` → `Manage Libraries` and install:

**For ESP8266:**
- `ESPAsyncWebServer` by lacamera
- `ESPAsyncTCP` by dvarrel
- `ArduinoJson` by Benoit Blanchon
- `LittleFS_esp32` (if using LittleFS)

**For ESP32:**
- `ESPAsyncWebServer` by lacamera  
- `AsyncTCP` by dvarrel
- `ArduinoJson` by Benoit Blanchon

## 📁 Firmware Files

Your firmware files are located in:
```
CH341SER_LINUX/arduino_firmware/
├── ESP8266_WebServer.ino    # ESP8266 firmware
├── ESP32_WebServer.ino      # ESP32 firmware
└── README_ARDUINO_SETUP.md  # This file
```

## ⚡ Quick Flash Instructions

### Method 1: Using Arduino IDE (Recommended)

1. **Open the firmware:**
   - For ESP8266: Open `ESP8266_WebServer.ino`
   - For ESP32: Open `ESP32_WebServer.ino`

2. **Configure WiFi settings:**
   ```cpp
   const char* ssid = "YOUR_WIFI_SSID";        // Change this!
   const char* password = "YOUR_WIFI_PASSWORD"; // Change this!
   ```

3. **Select your board:**
   - `Tools` → `Board` → Select your ESP model
   - Common options:
     - ESP8266: "NodeMCU 1.0 (ESP-12E Module)"
     - ESP32: "ESP32 Dev Module"

4. **Configure port:**
   - `Tools` → `Port` → Select `/dev/ttyUSB0` (or your CH340 port)

5. **Upload:**
   - Click the Upload button (→) or press `Ctrl+U`
   - Wait for "Done uploading"

### Method 2: Using Command Line

```bash
# Install Arduino CLI (if not installed)
curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh | sh

# For ESP8266
arduino-cli compile --fqbn esp8266:esp8266:nodemcuv2 ESP8266_WebServer.ino
arduino-cli upload --port /dev/ttyUSB0 --fqbn esp8266:esp8266:nodemcuv2 ESP8266_WebServer.ino

# For ESP32
arduino-cli compile --fqbn esp32:esp32:esp32 ESP32_WebServer.ino
arduino-cli upload --port /dev/ttyUSB0 --fqbn esp32:esp32:esp32 ESP32_WebServer.ino
```

## 🔌 Hardware Connections

### ESP8266 (NodeMCU/Wemos D1 Mini)
```
ESP8266 Pin  →  Component
GPIO2 (D4)   →  Built-in LED
GPIO5 (D1)   →  External LED + 220Ω resistor → GND
GPIO4 (D2)   →  Button → GND (with pull-up)
GPIO12 (D6)  →  Relay module
GPIO14 (D5)  →  Sensor input
3.3V         →  Power rail
GND          →  Ground rail
```

### ESP32 (DevKit/WROOM)
```
ESP32 Pin    →  Component
GPIO2        →  Built-in LED
GPIO5        →  External LED + 220Ω resistor → GND
GPIO4        →  Button → GND (with pull-up)
GPIO12       →  Relay module
GPIO14       →  Analog sensor
GPIO15       →  Touch sensor
3.3V         →  Power rail
GND          →  Ground rail
```

## 🌐 After Flashing

### 1. Monitor Serial Output
- Open `Tools` → `Serial Monitor`
- Set baud rate to `115200`
- Reset your ESP module
- You should see connection information

### 2. Find Your ESP's IP Address
Look for output like:
```
WiFi connected successfully!
IP address: 192.168.1.100
Web Interface: http://192.168.1.100/
```

### 3. Access Web Interface
- Open browser and go to the IP address shown
- You'll see a modern web interface with:
  - Real-time device status
  - GPIO controls (LED toggles, relay control)
  - System information
  - API endpoints

## 🎛️ Web Interface Features

### Main Dashboard
- **Device Status**: Uptime, memory, WiFi signal
- **GPIO Controls**: Toggle LEDs, relay, read sensors
- **Real-time Updates**: WebSocket-powered live data
- **Mobile Responsive**: Works on phones/tablets

### API Endpoints
```
GET  /api/status              # Device status (JSON)
GET  /api/device              # Device information
GET  /api/stats               # Statistics
POST /api/led/builtin         # Control built-in LED
POST /api/led/external        # Control external LED  
POST /api/relay               # Control relay
POST /api/gpio/toggle         # Toggle any GPIO
POST /api/restart             # Restart device
POST /api/reset               # Reset GPIO states
```

### Example API Usage
```bash
# Turn on external LED
curl -X POST http://192.168.1.100/api/led/external -d "state=on"

# Get device status
curl http://192.168.1.100/api/status

# Toggle built-in LED
curl -X POST http://192.168.1.100/api/gpio/toggle -d "pin=builtin_led"
```

## 🔧 Customization

### Modify GPIO Pins
Edit these constants in the firmware:
```cpp
const int BUILTIN_LED_PIN = 2;     // Built-in LED
const int EXTERNAL_LED_PIN = 5;    // External LED
const int BUTTON_PIN = 4;          // Button
const int RELAY_PIN = 12;          // Relay
const int SENSOR_PIN = 14;         // Sensor
```

### Add New Features
1. **New GPIO control:**
   ```cpp
   const int NEW_PIN = 13;
   pinMode(NEW_PIN, OUTPUT);
   ```

2. **New API endpoint:**
   ```cpp
   server.on("/api/new-feature", HTTP_POST, handleNewFeature);
   ```

3. **New sensor reading:**
   ```cpp
   void readNewSensor() {
     int value = analogRead(A0);
     // Process value
   }
   ```

## 🔄 OTA Updates

Once firmware is flashed, you can update wirelessly:

1. **Using Arduino IDE:**
   - `Tools` → `Port` → Select network port (ESP's IP)
   - Upload normally

2. **Using web interface:**
   - Access `http://ESP_IP/update`
   - Upload new firmware file

## 🐛 Troubleshooting

### Upload Issues
```bash
# Check if device is detected
ls -la /dev/ttyUSB*

# Check permissions
sudo chmod 666 /dev/ttyUSB0

# Add user to dialout group
sudo usermod -a -G dialout $USER
```

### Common Board Settings

**ESP8266 NodeMCU:**
- Board: "NodeMCU 1.0 (ESP-12E Module)"
- Upload Speed: 921600
- CPU Frequency: 80 MHz
- Flash Size: 4MB (FS:2MB OTA:~1019KB)

**ESP32 DevKit:**
- Board: "ESP32 Dev Module"
- Upload Speed: 921600
- CPU Frequency: 240MHz
- Flash Mode: DIO
- Flash Size: 4MB

### Serial Monitor Shows Garbage
- Check baud rate (should be 115200)
- Try different upload speeds
- Check connections

### WiFi Connection Failed
- Verify SSID and password in code
- Check WiFi signal strength
- Try different WiFi network
- Check for special characters in password

### Web Interface Not Loading
- Check serial monitor for IP address
- Try `http://esp8266-webserver.local` (mDNS)
- Check firewall settings
- Verify ESP and computer are on same network

## 📱 Mobile Access

The web interface is fully mobile-responsive:
- **Portrait/Landscape** support
- **Touch-friendly** buttons
- **Swipe gestures** for navigation
- **Responsive grid** layout

## 🔒 Security Notes

### Change Default Passwords
```cpp
// OTA password (line ~650)
ArduinoOTA.setPassword("esp8266ota");  // Change this!

// AP password (line ~45)
const char* ap_password = "12345678";  // Change this!
```

### Enable Authentication
Add basic auth to sensitive endpoints:
```cpp
server.on("/api/restart", HTTP_POST, [](AsyncWebServerRequest *request){
  if(!request->authenticate("admin", "password")) {
    return request->requestAuthentication();
  }
  // Handle restart
});
```

## 🚀 Advanced Features

### WebSocket Commands
Send JSON commands via WebSocket:
```javascript
ws.send(JSON.stringify({
  command: "toggle_builtin_led"
}));
```

### JSON API Responses
```json
{
  "status": "online",
  "uptime": 12345,
  "free_heap": 25000,
  "gpio": {
    "builtin_led": true,
    "external_led": false,
    "relay": false
  }
}
```

### Integration Examples

**Home Assistant:**
```yaml
switch:
  - platform: rest
    name: ESP LED
    resource: http://192.168.1.100/api/led/external
    body_on: "state=on"
    body_off: "state=off"
```

**Node-RED:**
- HTTP request nodes for API calls
- WebSocket node for real-time data
- Dashboard UI for control interface

## 📚 Next Steps

1. **Test Basic Functions**: Toggle LEDs, check status
2. **Add Hardware**: Connect sensors, relays, displays
3. **Customize Interface**: Modify HTML/CSS in firmware
4. **Integrate Systems**: Connect to home automation
5. **Scale Up**: Deploy multiple ESPs for IoT network

## 🆘 Support

### Getting Help
- Check serial output for error messages
- Verify all connections and wiring
- Test with minimal hardware first
- Check Arduino IDE error messages

### Useful Commands
```bash
# Reset to factory defaults
esptool.py erase_flash

# Check ESP info
esptool.py flash_id

# Monitor serial output
screen /dev/ttyUSB0 115200
```

---

**🎉 Congratulations!** 

You now have a fully functional ESP web server with:
- ✅ Modern web interface
- ✅ Real-time GPIO control  
- ✅ RESTful API
- ✅ WebSocket updates
- ✅ Mobile support
- ✅ OTA updates

Your ESP module is ready for IoT projects, home automation, or any web-controlled hardware application!