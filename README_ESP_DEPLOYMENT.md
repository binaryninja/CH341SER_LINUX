# ESP Web Server Deployment via CH340/CH341

A complete deployment pipeline for ESP modules connected through CH340/CH341 USB-to-serial converters. This system allows you to easily deploy web servers to ESP8266/ESP32 modules and manage them remotely.

## 🚀 Quick Start

### Prerequisites
- Linux system with CH340/CH341 drivers installed
- ESP module (ESP8266/ESP32) with AT firmware
- USB-to-serial converter (CH340/CH341)
- Python 3.6+ with pip

### 1. Hardware Setup
```
ESP Module <-- Serial --> CH340/CH341 <-- USB --> Computer
```

**Wiring:**
- ESP VCC → 3.3V
- ESP GND → GND  
- ESP TX → CH340 RX
- ESP RX → CH340 TX
- ESP EN/RST → 3.3V (via pull-up resistor)

### 2. Quick Deployment
```bash
# Make deployment script executable
chmod +x deploy.sh

# Run interactive deployment
sudo ./deploy.sh

# Or automated deployment
sudo ./deploy.sh --wifi-ssid "YourWiFi" --wifi-password "YourPassword"
```

### 3. Access Your Web Server
After successful deployment, your ESP module will be accessible via:
- Web interface at the assigned IP address
- Management dashboard at `http://localhost:8080` (if using web monitoring)

## 📁 Project Structure

```
CH341SER_LINUX/
├── ch34x.c                    # CH340/CH341 driver source
├── ch34x.ko                   # Compiled driver module
├── Makefile                   # Driver compilation
├── deploy.sh                  # Main deployment orchestrator
├── deploy_webserver.py        # ESP web server deployment
├── esp_monitor.py            # ESP monitoring and management
├── probe_device.py           # Device detection and probing
├── esp_config.json           # Configuration file
├── README_ESP_DEPLOYMENT.md  # This file
└── deployment.log            # Deployment logs
```

## 🛠️ Detailed Usage

### Device Detection and Probing
```bash
# Detect and probe connected ESP module
python3 probe_device.py

# Use custom serial port
python3 probe_device.py /dev/ttyUSB1
```

### Web Server Deployment
```bash
# Interactive deployment
python3 deploy_webserver.py

# Automated deployment
python3 deploy_webserver.py --wifi-ssid "MyNetwork" --wifi-password "MyPassword"

# Monitor deployment process
python3 deploy_webserver.py --monitor
```

### Monitoring and Management
```bash
# Start command-line monitoring  
python3 esp_monitor.py

# Get device status
python3 esp_monitor.py --status

# Execute AT command
python3 esp_monitor.py --command "AT+GMR"

# Reset device
python3 esp_monitor.py --reset

# Start web management interface
python3 esp_monitor.py --web-interface --web-port 8080
```

### Using the Deployment Orchestrator
```bash
# Interactive deployment wizard  
./deploy.sh

# Automated deployment
./deploy.sh --auto

# Check deployment status
./deploy.sh --status

# Start monitoring
./deploy.sh --monitor

# Start web-based monitoring
./deploy.sh --web-monitor

# Reset and redeploy
./deploy.sh --reset

# Recovery mode
./deploy.sh --recovery
```

## ⚙️ Configuration

### ESP Configuration File (`esp_config.json`)
```json
{
  "device": {
    "port": "/dev/ttyUSB0",
    "baudrate": 115200,
    "timeout": 5
  },
  "wifi": {
    "ssid": "",
    "password": "",
    "mode": "station",
    "auto_connect": true
  },
  "webserver": {
    "port": 80,
    "enable_multiple_connections": true,
    "max_connections": 4
  }
}
```

### Supported AT Commands
- `AT` - Test connection
- `AT+GMR` - Get firmware version
- `AT+CWMODE=1` - Set WiFi station mode
- `AT+CWJAP="SSID","PASSWORD"` - Connect to WiFi
- `AT+CIFSR` - Get IP address
- `AT+CIPMUX=1` - Enable multiple connections
- `AT+CIPSERVER=1,80` - Start HTTP server
- `AT+RST` - Reset module

## 🌐 Web Interface Features

### Main Dashboard
- Real-time device status
- Performance metrics
- Connection monitoring
- Command interface

### API Endpoints
- `/` - Main web interface
- `/status` - Device status (text)
- `/api/info` - Device info (JSON)
- `/api/wifi` - WiFi status (JSON)
- `/reset` - Reset device

### Management Interface
Access the web management interface at `http://localhost:8080`:
- Device status monitoring
- Performance metrics
- Live connection logs
- Remote command execution
- Device reset capabilities

## 🔧 Troubleshooting

### Common Issues

#### 1. Permission Denied on Serial Port
```bash
# Add user to dialout group
sudo usermod -a -G dialout $USER

# Or temporarily fix permissions
sudo chmod 666 /dev/ttyUSB0
```

#### 2. ESP Module Not Detected
- Check physical connections
- Verify power supply (3.3V)
- Ensure CH340/CH341 driver is loaded
- Try different baudrates (115200, 9600, 57600)

#### 3. WiFi Connection Failed
- Verify SSID and password
- Check signal strength
- Ensure ESP is in station mode
- Try manual connection with AT commands

#### 4. Web Server Won't Start
- Check if port 80 is available
- Verify multiple connections are enabled
- Try restarting the ESP module
- Check AT firmware version

### Recovery Commands
```bash
# Enter recovery mode
./deploy.sh --recovery

# Manual AT command interface
python3 -c "
import serial
ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=1)
# Send commands manually
"

# Reset to factory defaults
AT+RESTORE
AT+RST
```

### Diagnostic Commands
```bash
# Check USB devices
lsusb | grep -i ch34

# Check serial devices  
ls -la /dev/ttyUSB*

# Check driver status
lsmod | grep ch34x

# View system logs
dmesg | grep -i ch34
```

## 📊 Performance Monitoring

### Metrics Tracked
- Total connections
- HTTP requests per hour
- Error count
- Uptime
- Memory usage
- WiFi signal strength

### Log Analysis
```bash
# View deployment logs
tail -f deployment.log

# Monitor real-time connections
python3 esp_monitor.py | grep HTTP

# Export metrics to JSON
python3 esp_monitor.py --status > status.json
```

## 🔒 Security Considerations

### Best Practices
1. Change default WiFi credentials
2. Use WPA2/WPA3 encryption
3. Implement authentication for sensitive endpoints
4. Regularly update ESP firmware
5. Monitor access logs
6. Use HTTPS when possible

### Access Control
```python
# Add basic authentication
def authenticate_request(request):
    # Implement your authentication logic
    pass
```

## 🚀 Advanced Features

### Custom Web Pages
Modify the HTML content in `deploy_webserver.py`:
```python
def create_web_content(self):
    html_content = """
    <!-- Your custom HTML here -->
    """
    return html_content
```

### API Extensions
Add custom endpoints by modifying the HTTP request handler.

### Multiple Device Management
Deploy to multiple ESP modules by running separate instances with different ports.

## 📱 Mobile Access

The web interface is mobile-responsive and can be accessed from smartphones and tablets. Key features work seamlessly on mobile devices:
- Device status monitoring
- Basic command execution
- Log viewing
- Emergency reset

## 🔄 Continuous Integration

### Automated Testing
```bash
# Test deployment pipeline
./test_deployment.sh

# Validate configuration
python3 -c "import json; json.load(open('esp_config.json'))"

# Check device connectivity
python3 probe_device.py --test
```

### Monitoring Integration
Integrate with monitoring systems like:
- Prometheus + Grafana
- InfluxDB + Telegraf
- Custom logging solutions

## 📚 Examples

### Basic Web Server
```python
# Simple HTTP response
response = "HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n<h1>Hello World</h1>"
```

### JSON API Response
```python
import json
data = {"status": "ok", "temperature": 25.5}
response = f"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n{json.dumps(data)}"
```

### Custom Command Handler
```python
def handle_custom_command(command):
    if command == "get_sensor_data":
        return get_sensor_readings()
    elif command == "toggle_led":
        return toggle_onboard_led()
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

### Development Setup
```bash
# Install development dependencies
pip3 install -r requirements-dev.txt

# Run tests
python3 -m pytest tests/

# Format code
black *.py
```

## 📄 License

This project is licensed under the MIT License. See LICENSE file for details.

## 🆘 Support

### Getting Help
- Check the troubleshooting section
- Review the logs in `deployment.log`
- Use recovery mode: `./deploy.sh --recovery`
- Submit issues on GitHub

### Community
- GitHub Discussions
- Stack Overflow (tag: esp-deployment)
- Reddit: r/esp8266, r/esp32

## 🏆 Acknowledgments

- CH341/CH340 driver authors
- ESP8266/ESP32 community
- AT firmware maintainers
- Open source contributors

---

**Happy Deploying! 🎉**

For the latest updates and documentation, visit: https://github.com/your-repo/esp-deployment