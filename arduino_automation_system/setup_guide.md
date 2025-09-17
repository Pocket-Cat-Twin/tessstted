# Arduino Automation System - Complete Setup Guide

## 🎯 System Overview

This is a hybrid Python-Arduino automation system that provides:

- **Main Thread**: Database monitoring + chat automation + OCR screen monitoring
- **Secondary Thread**: Array processing with click automation  
- **Arduino Micro**: Physical mouse clicks and keyboard input via USB HID
- **Free Tesseract OCR**: Alternative to Yandex OCR for screen monitoring
- **Windows Optimized**: Designed for Windows with Arduino Micro

## 📋 Prerequisites

### Hardware Requirements
- **Arduino Micro** (USB HID support required)
  - ✅ Arduino Micro (recommended)
  - ✅ Arduino Leonardo (compatible)
  - ❌ Arduino Uno (no native USB HID)
- **USB Micro-B Cable** for Arduino connection
- **Windows Computer** with available USB port

### Software Requirements
- **Python 3.8+** (Python 3.9+ recommended)
- **Arduino IDE 1.8.0+** (Arduino IDE 2.0+ preferred)
- **Tesseract OCR** system installation

## 🛠️ Installation Steps

### Step 1: Install Python Dependencies

```bash
# Navigate to project directory
cd arduino_automation_system

# Install Python dependencies
pip install -r requirements.txt
```

**Required packages:**
- `pytesseract>=0.3.10` - Free OCR
- `Pillow>=10.0.0` - Image processing
- `opencv-python>=4.8.0` - Image preprocessing
- `pyserial>=3.5` - Arduino communication
- `mss>=9.0.1` - Screen capture

### Step 2: Install Tesseract OCR System

**Windows Installation:**
1. Download Tesseract installer from: https://github.com/UB-Mannheim/tesseract/wiki
2. Run installer and select "Additional language data" including Russian
3. Add Tesseract to Windows PATH:
   - Default path: `C:\Program Files\Tesseract-OCR`
   - Add to System Environment Variables

**Verify Tesseract Installation:**
```bash
tesseract --version
tesseract --list-langs
```

Expected output should include `rus` and `eng` languages.

### Step 3: Setup Arduino Hardware

1. **Connect Arduino Micro** to computer via USB cable
2. **Install Arduino IDE** from https://www.arduino.cc/en/software
3. **Configure Arduino IDE:**
   - Go to `Tools > Board > Arduino AVR Boards > Arduino Micro`
   - Go to `Tools > Port` and select Arduino COM port (usually COM3, COM4, etc.)

4. **Upload Arduino Code:**
   - Open `arduino_code/arduino_automation_controller.ino`
   - Click **Verify** (checkmark) to compile
   - Click **Upload** (arrow) to upload to Arduino
   - Wait for "Done uploading" message

5. **Test Arduino Communication:**
   - Open `Tools > Serial Monitor`
   - Set baud rate to **9600**
   - Arduino should send "READY" message
   - Type "PING" and press Enter - Arduino should respond "PONG"

### Step 4: Configure System

1. **Edit Configuration Files:**
   ```
   python_system/config/automation_config.json
   ```

2. **Replace Placeholders:**
   
   **Coordinates (find using screen measurement tools):**
   ```json
   "point1": {"x": 100, "y": 200},           // Replace PLACEHOLDER_POINT1_X/Y
   "point2": {"x": 300, "y": 400},           // Replace PLACEHOLDER_POINT2_X/Y
   "ocr_region": {                            // Replace PLACEHOLDER_OCR_*
       "x": 500, "y": 100, 
       "width": 200, "height": 100
   },
   "target_area": {"x": 600, "y": 300}       // Replace PLACEHOLDER_TARGET_AREA_*
   ```
   
   **Hotkeys:**
   ```json
   "hotkeys": {
       "main_hotkey": "F1",                   // Replace PLACEHOLDER_MAIN_HOTKEY
       "secondary_hotkey": "F2"               // Replace PLACEHOLDER_SECONDARY_HOTKEY
   }
   ```
   
   **Names Array:**
   ```json
   "names_array": [
       "PlayerName1",                         // Replace PLACEHOLDER_NAME_1
       "TargetName2",                         // Replace PLACEHOLDER_NAME_2
       "ItemName3"                            // Replace PLACEHOLDER_NAME_3
   ]
   ```

3. **Update Arduino COM Port:**
   
   The system will auto-detect Arduino port, or manually set:
   ```json
   "arduino": {
       "serial_port": "COM3"                  // Your Arduino COM port
   }
   ```

## 🚀 Running the System

### Method 1: Direct Python Execution

```bash
cd arduino_automation_system/python_system/src
python main.py
```

### Method 2: Package Import

```python
from arduino_automation_system.python_system.src import create_automation_system

# Create system coordinator
system = create_automation_system()

# Run the system
system.run()
```

### Expected Output

```
Arduino Automation System
==================================================
2024-XX-XX - INFO - Loading configuration...
2024-XX-XX - INFO - Auto-detected Arduino port: COM3
2024-XX-XX - INFO - Arduino controller initialized
2024-XX-XX - INFO - Database manager initialized
2024-XX-XX - INFO - OCR manager initialized
2024-XX-XX - INFO - Database monitor thread started
2024-XX-XX - INFO - Array processor thread started
2024-XX-XX - INFO - Arduino automation system started successfully
2024-XX-XX - INFO - Entering main run loop...
```

## 🔧 Configuration Guide

### Finding Screen Coordinates

**Windows Built-in Tools:**
1. Use **Screen Snipping Tool** (Win+Shift+S)
2. Coordinates shown in bottom-right when selecting area
3. Use **Steps Recorder** (psr.exe) to record click positions

**Third-party Tools:**
- **Mouse Position Utilities** - Show real-time cursor coordinates
- **AutoHotkey Window Spy** - Advanced coordinate detection

### Testing Coordinates

Use Arduino commands to test positions:
```python
# Test in Python
from arduino_controller import ArduinoController

arduino = ArduinoController('COM3')
arduino.click_position(100, 200)  # Test Point1
arduino.click_position(300, 400)  # Test Point2
```

### OCR Region Setup

1. **Identify Monitoring Area**: Small screen region that changes during automation
2. **Size Recommendations**: 
   - Width: 200-400 pixels
   - Height: 50-200 pixels
   - Keep small for better performance
3. **Position**: Top-left corner coordinates of monitoring region

### Hotkey Configuration

**Supported Hotkeys:**
- Function keys: `F1`, `F2`, `F3`, etc.
- Combinations: `CTRL+C`, `ALT+TAB`, `WIN+R`
- Single keys: `ENTER`, `ESC`, `TAB`, `SPACE`

## 📊 System Operation

### Main Thread (Database Monitor)

1. **Polls Database** for automation targets with `NEW` status
2. **Executes Chat Automation:**
   - Press Enter
   - Type "/target <target_name>"
   - Press Enter again  
   - Press hotkey
3. **Monitors OCR Region** for screen changes
4. **Executes 9-Step Mouse Pattern** when changes detected
5. **Updates Database** status to `COMPLETED`

### Secondary Thread (Array Processor)

1. **Continuously Processes Names Array:**
   - Click Point1
   - Type name from array
   - Click Point2
   - Press hotkey
   - Random delay (1-2 seconds)
2. **Repeats Cycle** with next name in array
3. **Logs Activity** to database

### Database Integration

**Tables Created:**
- `automation_targets` - Targets for main thread processing
- `automation_sessions` - Session tracking
- `automation_commands_log` - Command execution logs

**Adding Targets:**
```python
# Add target manually
system.add_automation_target("TargetName123")

# Or add to database directly
INSERT INTO automation_targets (target_name) VALUES ('TargetName123');
```

## 🐛 Troubleshooting

### Arduino Connection Issues

**Problem**: "Arduino not detected"
```bash
# Check available COM ports
python -c "
import serial.tools.list_ports
for port in serial.tools.list_ports.comports():
    print(f'{port.device}: {port.description}')
"
```

**Solutions:**
1. Try different USB ports
2. Install/update Arduino drivers
3. Check Device Manager for Arduino entry
4. Restart Arduino IDE
5. Press reset button on Arduino

### Tesseract OCR Issues

**Problem**: "Tesseract not found"

**Solutions:**
1. Add Tesseract to Windows PATH
2. Set environment variable: `TESSDATA_PREFIX=C:\Program Files\Tesseract-OCR\tessdata`
3. Reinstall Tesseract with language packs

**Test Tesseract:**
```python
import pytesseract
from PIL import Image

# Test basic functionality
img = Image.new('RGB', (100, 50), color='white')
text = pytesseract.image_to_string(img)
print("Tesseract working!")
```

### Configuration Errors

**Problem**: "Placeholders found in configuration"

**Solution**: Replace all `PLACEHOLDER_*` values with actual coordinates/hotkeys/names

**Validation:**
```python
from config_manager import ConfigManager

config = ConfigManager()
validation = config.validate_configuration_readiness()
print(validation)
```

### Serial Communication Problems

**Problem**: "Command timeout" or "Arduino not responding"

**Solutions:**
1. Check Arduino code uploaded correctly
2. Verify baud rate is 9600
3. Close other programs using COM port
4. Try different USB cable
5. Restart Arduino (press reset button)

### Database Connection Issues

**Problem**: "Database locked" or "Connection failed"

**Solutions:**
1. Close other programs accessing database
2. Check database file permissions
3. Verify database path exists
4. Use absolute paths in configuration

## 📈 Performance Optimization

### System Performance

1. **Close Unnecessary Programs** during automation
2. **Use Direct USB Connection** (avoid USB hubs)
3. **Disable Windows USB Power Management**
4. **Monitor CPU and Memory Usage**

### OCR Performance

1. **Keep OCR Region Small** (200x100 pixels optimal)
2. **Use High Contrast Areas** for monitoring
3. **Avoid Complex Text Areas**
4. **Adjust OCR Confidence Threshold** if needed

### Arduino Performance

1. **Use Quality USB Cable** for reliable connection
2. **Avoid USB Extension Cables**
3. **Monitor Serial Buffer** for command backlog
4. **Set Appropriate Delays** to prevent command flooding

## 🔒 Security Considerations

### Windows Security

- Windows may prompt for Arduino driver installation (allow it)
- Arduino appears as USB keyboard/mouse (this is normal)
- Antivirus may flag Arduino USB activity (add exceptions)
- No additional permissions required for HID functionality

### Safe Operation

- **Test coordinates thoroughly** before production use
- **Monitor system during operation** for unexpected behavior
- **Use emergency stop hotkey** (Ctrl+C in terminal)
- **Keep Arduino code simple** to prevent system interference

## 📝 Maintenance

### Regular Tasks

1. **Check Logs** for errors and performance issues
2. **Clean Database** of old records (automated every 7 days)
3. **Monitor Arduino Connection** stability
4. **Update Coordinates** if screen layout changes
5. **Backup Configuration** files

### Log Files

- **Location**: `automation_system.log` (if file logging enabled)
- **Rotation**: Automatic (50MB max, 3 backups)
- **Level**: Configurable (DEBUG, INFO, WARNING, ERROR)

### Database Maintenance

```python
# Manual cleanup of old records
system.db_manager.cleanup_old_records(days=7)

# Get system statistics
stats = system.get_automation_statistics(hours=24)
print(stats)
```

## 🎓 Advanced Usage

### Custom Automation Sequences

Extend `DatabaseMonitorThread` for custom automation:
```python
class CustomDatabaseMonitor(DatabaseMonitorThread):
    def _execute_custom_sequence(self, target):
        # Your custom automation logic
        pass
```

### Additional OCR Monitors

Create multiple OCR monitors for different screen regions:
```python
ocr_manager.create_screen_monitor(
    "custom_monitor", 
    OCRRegion(x=100, y=100, width=200, height=100)
)
```

### Integration with External Systems

```python
# Add webhook notifications
def on_target_completed(target):
    requests.post('http://your-webhook.com', json={'target': target.name})

# Add email notifications  
def on_error_occurred(error):
    send_email(f"Automation error: {error}")
```

## 📞 Support

### Getting Help

1. **Check Logs** for detailed error messages
2. **Review Configuration** for placeholder replacements
3. **Test Components Individually** (Arduino, OCR, Database)
4. **Consult Arduino Documentation** for hardware issues
5. **Check Python Package Versions** for compatibility

### Common Solutions

| Problem | Solution |
|---------|----------|
| Arduino not found | Check COM port, drivers, USB connection |
| OCR not working | Install Tesseract, check PATH, verify languages |
| Coordinates wrong | Use screen measurement tools, test with Arduino |
| Database locked | Close other programs, check permissions |
| Import errors | Install requirements.txt, check Python version |

### System Requirements Summary

- **Python**: 3.8+ (3.9+ recommended)
- **Arduino**: Micro or Leonardo (USB HID required)
- **OS**: Windows 10+ (primary), Linux/macOS (secondary)
- **Memory**: 512MB+ available RAM
- **Storage**: 100MB+ for installation and logs
- **USB**: Available USB port for Arduino connection

---

**🎉 You're ready to automate!** The system should now be configured and running your dual-thread Arduino automation with OCR monitoring and database integration.