# Arduino Setup Guide

## Arduino Hardware Requirements

### ✅ Required Hardware
- **Arduino Micro** (USB HID support required)
- **USB Micro-B Cable** for connection to computer
- **Windows Computer** with available USB port

### ❌ Not Compatible
- Arduino Uno (no native USB HID support)
- Arduino Nano (no native USB HID support)
- Other Arduino boards without native USB HID

## Arduino IDE Setup

### Step 1: Install Arduino IDE
1. Download Arduino IDE from: https://www.arduino.cc/en/software
2. Install Arduino IDE on your Windows system
3. Connect Arduino Micro to computer via USB cable

### Step 2: Configure Arduino IDE
1. Open Arduino IDE
2. Go to **Tools > Board > Arduino AVR Boards > Arduino Micro**
3. Go to **Tools > Port** and select the COM port for your Arduino Micro
   - Usually shows as "COM3", "COM4", "COM5", etc.
   - Note: Remember this COM port for Python configuration

### Step 3: Verify Libraries
Required libraries (should be included by default):
- **Mouse.h** - USB HID Mouse control
- **Keyboard.h** - USB HID Keyboard control

If missing, install via **Tools > Manage Libraries**

### Step 4: Upload Arduino Code
1. Open file: `arduino_automation_controller.ino`
2. Click **Verify** button (checkmark) to compile
3. Click **Upload** button (arrow) to upload to Arduino Micro
4. Wait for "Done uploading" message

### Step 5: Test Communication
1. Open **Tools > Serial Monitor**
2. Set baud rate to **9600**
3. Arduino should send "READY" message
4. Type "PING" and press Enter
5. Arduino should respond with "PONG"

## Arduino Code Features

### Supported Commands
- **CLICK:x,y** - Click mouse at coordinates
- **TYPE:text** - Type text string
- **KEY:keycode** - Press single key (ENTER, ESC, TAB, etc.)
- **HOTKEY:combination** - Press hotkey combos (CTRL+C, ALT+TAB, etc.)
- **DELAY:milliseconds** - Execute delay (1-30000ms)
- **PING** - Test connectivity (responds with PONG)

### Response Messages
- **OK** - Command executed successfully
- **ERROR:description** - Command failed with reason
- **READY** - Arduino ready for commands
- **HEARTBEAT** - Periodic connectivity check

### Error Handling
- Invalid command format detection
- Coordinate range validation
- Text length limits
- Delay range validation
- Connection timeout monitoring

## Troubleshooting

### Arduino Not Detected
1. Check USB cable connection
2. Try different USB ports
3. Install Arduino drivers if needed
4. Restart Arduino IDE

### Upload Failed
1. Ensure correct board selected (Arduino Micro)
2. Ensure correct COM port selected
3. Close Serial Monitor before uploading
4. Press reset button on Arduino if needed

### Serial Communication Issues
1. Verify baud rate is 9600
2. Check COM port selection
3. Ensure no other programs using COM port
4. Try unplugging and reconnecting Arduino

### Mouse/Keyboard Not Working
1. Verify Arduino Micro (not Uno/Nano)
2. Check if Mouse.h and Keyboard.h libraries installed
3. Restart computer after first Arduino connection
4. Check Windows USB device recognition

## Windows COM Port Detection

### Find Arduino COM Port
1. Connect Arduino Micro
2. Open **Device Manager** (Windows key + X, then M)
3. Expand **Ports (COM & LPT)**
4. Look for "Arduino Micro (COMx)"
5. Note the COM port number (e.g., COM3)

### If Arduino Not Listed
1. Update Arduino drivers
2. Try different USB cable
3. Check Arduino board power LED
4. Restart Windows USB services

## Security Considerations

### Windows Security
- Windows may prompt for Arduino driver installation
- Allow Arduino IDE to access USB devices
- Antivirus may flag Arduino USB HID activity as suspicious
- Add Arduino IDE to antivirus exceptions if needed

### USB HID Permissions
- Arduino Micro acts as USB keyboard/mouse
- No additional permissions required on Windows
- System will recognize Arduino as HID device automatically

## Production Setup Notes

### Stable Connection
- Use quality USB cable for reliable connection
- Avoid USB hubs if possible (direct connection preferred)
- Ensure stable power supply to computer
- Consider USB cable strain relief

### Performance Optimization
- Close unnecessary programs during automation
- Disable Windows power management for USB ports
- Set Arduino IDE to stay open during operation
- Monitor serial buffer for command backlog

### Backup Configuration
- Save Arduino code configuration
- Document COM port assignments
- Keep spare Arduino Micro for redundancy
- Backup working Arduino IDE setup