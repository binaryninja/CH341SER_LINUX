# CH341SER Linux Driver & ESP Development Suite

A comprehensive Linux driver and development environment for CH340/CH341 USB-to-serial converters with integrated ESP8266/ESP32 web server deployment capabilities.

## 🚀 Overview

This project provides:
- **CH340/CH341 Linux kernel driver** with support for modern Linux kernels
- **Complete ESP development pipeline** for web server deployment
- **Arduino firmware flashing tools** for ESP8266/ESP32 modules
- **Web-based monitoring and management** system
- **Automated deployment scripts** with WiFi configuration

## 📋 Features

### CH340/CH341 Driver
- ✅ Support for Linux kernel versions 2.6.25 to 6.x+
- ✅ 32-bit and 64-bit system compatibility
- ✅ CH340 and CH341 chip support
- ✅ High-speed serial communication
- ✅ Modern kernel API compatibility

### ESP Development Suite
- 🌐 **Web Server Deployment** - Deploy complete web servers to ESP modules
- 📱 **Mobile-Responsive Interface** - Modern HTML/CSS/JavaScript interface
- 🔧 **GPIO Control** - Real-time control of LEDs, relays, and sensors
- 📡 **RESTful API** - JSON endpoints for automation and integration
- 📊 **Live Monitoring** - Real-time device status and monitoring
- ⚡ **Over-The-Air Updates** - Wireless firmware updates
- 🏠 **Home Automation Ready** - Integration with Home Assistant and similar platforms

## 🛠️ Installation

### Prerequisites
```bash
# Install required dependencies
sudo apt update
sudo apt install build-essential linux-headers-$(uname -r) python3 python3-pip

# Install Python dependencies
pip3 install pyserial requests
```

### 1. Install CH340/CH341 Driver
```bash
# Clone the repository
git clone <repository-url>
cd CH341SER_LINUX

# Compile and install the driver
make
sudo make load

# Verify installation
lsmod | grep ch34x
```

### 2. Set Up ESP Development Environment
```bash
# Make scripts executable
chmod +x deploy.sh
chmod +x *.py

# Verify system setup
python3 verify_setup.py

# Run automated setup (optional)
sudo python3 verify_setup.py --fix-issues
```

## 🚀 Quick Start

### Basic ESP Web Server Deployment
```bash
# Interactive deployment with WiFi setup
sudo ./deploy.sh

# Automated deployment
sudo ./deploy.sh --wifi-ssid "YourWiFi" --wifi-password "YourPassword"

# Deploy with Arduino firmware (recommended)
sudo ./deploy.sh --arduino --wifi-ssid "YourWiFi" --wifi-password "YourPassword"
```

### Hardware Setup
```
ESP Module Connection:
ESP VCC  → 3.3V
ESP GND  → GND
ESP TX   → CH340/CH341 RX
ESP RX   → CH340/CH341 TX
ESP EN   → 3.3V (via 10kΩ pull-up resistor)
ESP GPIO0→ 3.3V (normal operation) or GND (programming mode)
```

## 📁 Project Structure

```
CH341SER_LINUX/
├── 🔧 Driver Components
│   ├── ch34x.c                 # Main driver source code
│   ├── ch34x.ko               # Compiled kernel module
│   ├── Makefile               # Driver compilation rules
│   └── readme.txt             # Original driver documentation
│
├── 🚀 Deployment Tools
│   ├── deploy.sh              # Main deployment orchestrator
│   ├── flash_arduino_firmware.py  # Arduino firmware flasher
│   ├── deploy_webserver.py    # ESP web server deployment
│   ├── esp_monitor.py         # Device monitoring tools
│   ├── verify_setup.py        # System verification
│   └── probe_device.py        # Device detection
│
├── 🔌 Arduino Firmware
│   ├── arduino_firmware/
│   │   ├── ESP8266_WebServer.ino    # Advanced web server
│   │   ├── ESP8266_Simple_WebServer.ino  # Basic web server
│   │   ├── ESP32_WebServer.ino      # ESP32 variant
│   │   └── README_ARDUINO_SETUP.md  # Arduino setup guide
│   │
│   ├── bin/
│   │   └── arduino-cli         # Arduino CLI tool
│   └── arduino-cli.yaml        # Arduino configuration
│
├── 🌐 Web Interface
│   ├── http_handler.py         # HTTP request handler
│   └── esp_config.json         # ESP configuration
│
└── 📚 Documentation
    ├── README_ESP_DEPLOYMENT.md    # ESP deployment guide
    ├── DEPLOYMENT_SUCCESS.md       # Success documentation
    └── NEXT_STEPS.md              # Post-deployment guide
```

## 🔧 Usage Examples

### Basic Driver Operations
```bash
# Load driver
sudo make load

# Unload driver
sudo make unload

# Check driver status
lsmod | grep ch34x
dmesg | grep ch34x
```

### ESP Web Server Control
```bash
# Deploy web server to ESP
sudo ./deploy.sh --arduino

# Monitor deployment
sudo ./deploy.sh --monitor

# Check device status
python3 verify_setup.py --detailed

# Web-based monitoring
sudo ./deploy.sh --web-monitor
```

### API Usage Examples
Once your ESP web server is deployed, you can control it via REST API:

```bash
# Get device status
curl http://ESP_IP/api/status

# Control built-in LED
curl -X POST -d "state=on" http://ESP_IP/api/builtin_led

# Control external GPIO
curl -X POST -d "state=on" http://ESP_IP/api/relay

# Toggle any GPIO
curl -X POST -d "pin=builtin_led" http://ESP_IP/api/toggle
```

### Python Integration
```python
import requests

# Connect to your ESP web server
esp_ip = "192.168.1.100"  # Replace with your ESP IP

# Turn on LED
response = requests.post(f'http://{esp_ip}/api/builtin_led', 
                        data={'state': 'on'})

# Get device status
status = requests.get(f'http://{esp_ip}/api/status').json()
print(f"Uptime: {status['uptime']} ms")
print(f"Free heap: {status['heap']} bytes")
```

## 🏠 Home Automation Integration

### Home Assistant
```yaml
# configuration.yaml
switch:
  - platform: rest
    name: ESP LED
    resource: http://ESP_IP/api/builtin_led
    body_on: "state=on"
    body_off: "state=off"
    
sensor:
  - platform: rest
    name: ESP Status
    resource: http://ESP_IP/api/status
    json_attributes:
      - uptime
      - heap
      - wifi_signal
```

### Node-RED Integration
Create HTTP request nodes pointing to your ESP API endpoints for visual automation flows.

## 🔍 Troubleshooting

### Driver Issues
```bash
# Check if device is detected
lsusb | grep -i "1a86\|QinHeng"

# Verify port permissions
ls -la /dev/ttyUSB*
sudo chmod 666 /dev/ttyUSB0

# Reinstall driver
sudo make unload
make clean
make
sudo make load
```

### ESP Connection Issues
```bash
# Test serial connection
python3 probe_device.py

# Verify ESP is in correct mode
# GPIO0 should be HIGH for normal operation
# GPIO0 should be LOW for programming mode

# Check power supply (ESP needs stable 3.3V)
```

### Web Server Issues
```bash
# Check ESP is connected to WiFi
python3 esp_monitor.py

# Verify web server is running
curl -v http://ESP_IP/api/status

# Check firewall settings
sudo ufw status
```

## 🌟 Advanced Features

### Over-The-Air (OTA) Updates
The Arduino firmware supports OTA updates for wireless firmware deployment:
```cpp
// OTA updates available in firmware
// Access via http://ESP_IP/update
```

### Custom Firmware Development
1. Modify firmware in `arduino_firmware/` directory
2. Use `flash_arduino_firmware.py` to deploy
3. Monitor via `esp_monitor.py`

### Multi-Device Management
Deploy to multiple ESP modules and manage them from a central dashboard.

## 📊 Performance

- **Driver Performance**: Supports baud rates up to 2Mbps
- **Web Server**: Handles 10+ concurrent connections
- **Memory Usage**: ~32KB free heap on ESP8266
- **Response Time**: <100ms for GPIO operations
- **WiFi Range**: Typical ESP8266/ESP32 range (50-100m)

## 🔒 Security

- Web interface uses HTTP (add HTTPS for production)
- No authentication by default (implement as needed)
- Local network access only (configure firewall for internet access)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Test your changes thoroughly
4. Submit a pull request

## 📄 License

This project contains:
- CH340/CH341 driver: Copyright (C) WCH 2002-2013
- ESP deployment tools: Open source components
- Arduino firmware: MIT License

## 🆘 Support

### Common Issues
- **Permission denied**: Run with `sudo` or add user to `dialout` group
- **Device not found**: Check USB connection and driver installation
- **WiFi connection failed**: Verify credentials and signal strength
- **Web server not responding**: Check ESP power supply and WiFi connection

### Getting Help
1. Check the troubleshooting section above
2. Run `python3 verify_setup.py --detailed` for diagnostic information
3. Check log files in the project directory
4. Review the extensive documentation in the project

## 🎯 Use Cases

- **IoT Development**: Rapid prototyping of IoT devices
- **Home Automation**: Control lights, appliances, sensors
- **Educational Projects**: Learning ESP programming and web development
- **Industrial Automation**: Remote monitoring and control systems
- **Hobbyist Projects**: Custom electronics control
- **Research Projects**: Sensor networks and data collection

## 🏆 Features Comparison

| Feature | AT Firmware | Arduino Firmware |
|---------|-------------|------------------|
| Web Interface | ❌ | ✅ Modern responsive UI |
| GPIO Control | ⚠️ Limited | ✅ Full control |
| API Endpoints | ❌ | ✅ RESTful JSON API |
| OTA Updates | ❌ | ✅ Wireless updates |
| Custom Logic | ❌ | ✅ Full programming |
| Real-time Updates | ❌ | ✅ WebSocket support |

**Recommendation**: Use Arduino firmware for full functionality.

---

## 🎉 Quick Success Path

1. **Install driver**: `make && sudo make load`
2. **Connect ESP module** with proper wiring
3. **Run deployment**: `sudo ./deploy.sh --arduino`
4. **Access web interface** at the provided IP address
5. **Start building** your IoT projects!

**Your ESP web server will be accessible via browser with full GPIO control capabilities.**

---

*Made with ❤️ for the embedded systems community*