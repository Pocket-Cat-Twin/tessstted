/*
  Arduino Automation Controller
  For Arduino Micro (USB HID Support)
  
  Receives commands via Serial from Python system and executes:
  - Mouse clicks at specific coordinates
  - Keyboard text input
  - Single key presses
  - Hotkey combinations
  - Randomized delays
  
  Communication Protocol:
  Python -> Arduino:
  - CLICK:x,y - Click at coordinates
  - TYPE:text - Type text string
  - KEY:keycode - Press single key
  - HOTKEY:combination - Press hotkey combo
  - DELAY:milliseconds - Execute delay
  
  Arduino -> Python:
  - OK - Command executed successfully
  - ERROR - Command failed
  - READY - Arduino ready for commands
*/

#include <Mouse.h>
#include <Keyboard.h>

// Global variables
String inputCommand = "";
bool commandComplete = false;
unsigned long lastActivityTime = 0;
const unsigned long ACTIVITY_TIMEOUT = 30000; // 30 seconds timeout

void setup() {
    // Initialize serial communication
    Serial.begin(9600);
    
    // Initialize HID devices
    Mouse.begin();
    Keyboard.begin();
    
    // Wait for serial connection
    while (!Serial) {
        delay(100);
    }
    
    // Send ready signal
    Serial.println("READY");
    lastActivityTime = millis();
}

void loop() {
    // Check for incoming serial data
    if (Serial.available()) {
        char inChar = (char)Serial.read();
        
        if (inChar == '\n') {
            commandComplete = true;
        } else {
            inputCommand += inChar;
        }
        
        lastActivityTime = millis();
    }
    
    // Process complete command
    if (commandComplete) {
        inputCommand.trim();
        processCommand(inputCommand);
        inputCommand = "";
        commandComplete = false;
    }
    
    // Periodic heartbeat for connection monitoring
    if (millis() - lastActivityTime > ACTIVITY_TIMEOUT) {
        Serial.println("HEARTBEAT");
        lastActivityTime = millis();
    }
    
    delay(10); // Small delay to prevent CPU overload
}

void processCommand(String cmd) {
    if (cmd.length() == 0) {
        Serial.println("ERROR:EMPTY_COMMAND");
        return;
    }
    
    // Parse and execute CLICK command
    if (cmd.startsWith("CLICK:")) {
        executeClickCommand(cmd);
    }
    // Parse and execute MOVE command
    else if (cmd.startsWith("MOVE:")) {
        executeMoveCommand(cmd);
    }
    // Parse and execute TYPE command
    else if (cmd.startsWith("TYPE:")) {
        executeTypeCommand(cmd);
    }
    // Parse and execute KEY command
    else if (cmd.startsWith("KEY:")) {
        executeKeyCommand(cmd);
    }
    // Parse and execute HOTKEY command
    else if (cmd.startsWith("HOTKEY:")) {
        executeHotkeyCommand(cmd);
    }
    // Parse and execute DELAY command
    else if (cmd.startsWith("DELAY:")) {
        executeDelayCommand(cmd);
    }
    // Handle PING command for connectivity test
    else if (cmd == "PING") {
        Serial.println("PONG");
    }
    // Unknown command
    else {
        Serial.println("ERROR:UNKNOWN_COMMAND");
    }
}

void executeClickCommand(String cmd) {
    // Expected format: CLICK:x,y
    int colonIndex = cmd.indexOf(':');
    int commaIndex = cmd.indexOf(',', colonIndex);
    
    if (colonIndex == -1 || commaIndex == -1) {
        Serial.println("ERROR:INVALID_CLICK_FORMAT");
        return;
    }
    
    String xStr = cmd.substring(colonIndex + 1, commaIndex);
    String yStr = cmd.substring(commaIndex + 1);
    
    int x = xStr.toInt();
    int y = yStr.toInt();
    
    // Validate coordinates (basic range check)
    if (x < 0 || y < 0 || x > 3840 || y > 2160) {
        Serial.println("ERROR:INVALID_COORDINATES");
        return;
    }
    
    try {
        // Move mouse to position (relative movement)
        Mouse.move(x, y);
        delay(50); // Small delay for mouse movement
        
        // Perform left click
        Mouse.click(MOUSE_LEFT);
        
        Serial.println("OK");
    } catch (...) {
        Serial.println("ERROR:CLICK_FAILED");
    }
}

void executeTypeCommand(String cmd) {
    // Expected format: TYPE:text
    int colonIndex = cmd.indexOf(':');
    
    if (colonIndex == -1 || colonIndex == cmd.length() - 1) {
        Serial.println("ERROR:INVALID_TYPE_FORMAT");
        return;
    }
    
    String text = cmd.substring(colonIndex + 1);
    
    // Validate text length (prevent extremely long strings)
    if (text.length() > 1000) {
        Serial.println("ERROR:TEXT_TOO_LONG");
        return;
    }
    
    try {
        // Type the text
        Keyboard.print(text);
        Serial.println("OK");
    } catch (...) {
        Serial.println("ERROR:TYPE_FAILED");
    }
}

void executeKeyCommand(String cmd) {
    // Expected format: KEY:keycode
    int colonIndex = cmd.indexOf(':');
    
    if (colonIndex == -1 || colonIndex == cmd.length() - 1) {
        Serial.println("ERROR:INVALID_KEY_FORMAT");
        return;
    }
    
    String keyStr = cmd.substring(colonIndex + 1);
    
    try {
        // Handle special keys
        if (keyStr == "ENTER" || keyStr == "\\n") {
            Keyboard.press(KEY_RETURN);
            Keyboard.release(KEY_RETURN);
        }
        else if (keyStr == "ESC") {
            Keyboard.press(KEY_ESC);
            Keyboard.release(KEY_ESC);
        }
        else if (keyStr == "TAB") {
            Keyboard.press(KEY_TAB);
            Keyboard.release(KEY_TAB);
        }
        else if (keyStr == "SPACE") {
            Keyboard.press(' ');
            Keyboard.release(' ');
        }
        else if (keyStr == "BACKSPACE") {
            Keyboard.press(KEY_BACKSPACE);
            Keyboard.release(KEY_BACKSPACE);
        }
        else if (keyStr == "DELETE") {
            Keyboard.press(KEY_DELETE);
            Keyboard.release(KEY_DELETE);
        }
        // Handle single character
        else if (keyStr.length() == 1) {
            char key = keyStr.charAt(0);
            Keyboard.press(key);
            Keyboard.release(key);
        }
        else {
            Serial.println("ERROR:UNSUPPORTED_KEY");
            return;
        }
        
        Serial.println("OK");
    } catch (...) {
        Serial.println("ERROR:KEY_FAILED");
    }
}

void executeHotkeyCommand(String cmd) {
    // Expected format: HOTKEY:CTRL+C or HOTKEY:ALT+TAB etc.
    int colonIndex = cmd.indexOf(':');
    
    if (colonIndex == -1 || colonIndex == cmd.length() - 1) {
        Serial.println("ERROR:INVALID_HOTKEY_FORMAT");
        return;
    }
    
    String hotkey = cmd.substring(colonIndex + 1);
    hotkey.toUpperCase();
    
    try {
        // Parse and execute common hotkey combinations
        if (hotkey == "CTRL+C") {
            Keyboard.press(KEY_LEFT_CTRL);
            Keyboard.press('c');
            Keyboard.releaseAll();
        }
        else if (hotkey == "CTRL+V") {
            Keyboard.press(KEY_LEFT_CTRL);
            Keyboard.press('v');
            Keyboard.releaseAll();
        }
        else if (hotkey == "CTRL+A") {
            Keyboard.press(KEY_LEFT_CTRL);
            Keyboard.press('a');
            Keyboard.releaseAll();
        }
        else if (hotkey == "CTRL+Z") {
            Keyboard.press(KEY_LEFT_CTRL);
            Keyboard.press('z');
            Keyboard.releaseAll();
        }
        else if (hotkey == "ALT+TAB") {
            Keyboard.press(KEY_LEFT_ALT);
            Keyboard.press(KEY_TAB);
            Keyboard.releaseAll();
        }
        else if (hotkey == "WIN+R") {
            Keyboard.press(KEY_LEFT_GUI);
            Keyboard.press('r');
            Keyboard.releaseAll();
        }
        // Function keys
        else if (hotkey == "F1") {
            Keyboard.press(KEY_F1);
            Keyboard.release(KEY_F1);
        }
        else if (hotkey == "F2") {
            Keyboard.press(KEY_F2);
            Keyboard.release(KEY_F2);
        }
        else if (hotkey == "F3") {
            Keyboard.press(KEY_F3);
            Keyboard.release(KEY_F3);
        }
        else if (hotkey == "F4") {
            Keyboard.press(KEY_F4);
            Keyboard.release(KEY_F4);
        }
        else if (hotkey == "F5") {
            Keyboard.press(KEY_F5);
            Keyboard.release(KEY_F5);
        }
        // Placeholder for user-defined hotkey
        else if (hotkey == "PLACEHOLDER_HOTKEY") {
            // This will be replaced with actual hotkey during configuration
            // For now, simulate F1 as placeholder
            Keyboard.press(KEY_F1);
            Keyboard.release(KEY_F1);
        }
        else {
            Serial.println("ERROR:UNSUPPORTED_HOTKEY");
            return;
        }
        
        Serial.println("OK");
    } catch (...) {
        Serial.println("ERROR:HOTKEY_FAILED");
    }
}

void executeMoveCommand(String cmd) {
    // Expected format: MOVE:delta_x,delta_y
    int colonIndex = cmd.indexOf(':');
    int commaIndex = cmd.indexOf(',', colonIndex);
    
    if (colonIndex == -1 || commaIndex == -1) {
        Serial.println("ERROR:INVALID_MOVE_FORMAT");
        return;
    }
    
    String deltaXStr = cmd.substring(colonIndex + 1, commaIndex);
    String deltaYStr = cmd.substring(commaIndex + 1);
    
    int deltaX = deltaXStr.toInt();
    int deltaY = deltaYStr.toInt();
    
    // Validate movement range (prevent extreme movements)
    if (abs(deltaX) > 1000 || abs(deltaY) > 1000) {
        Serial.println("ERROR:MOVEMENT_TOO_LARGE");
        return;
    }
    
    try {
        // Move mouse by relative offset
        Mouse.move(deltaX, deltaY);
        Serial.println("OK");
    } catch (...) {
        Serial.println("ERROR:MOVE_FAILED");
    }
}

void executeDelayCommand(String cmd) {
    // Expected format: DELAY:milliseconds
    int colonIndex = cmd.indexOf(':');
    
    if (colonIndex == -1 || colonIndex == cmd.length() - 1) {
        Serial.println("ERROR:INVALID_DELAY_FORMAT");
        return;
    }
    
    String delayStr = cmd.substring(colonIndex + 1);
    unsigned long delayMs = delayStr.toInt();
    
    // Validate delay range (1ms to 30 seconds)
    if (delayMs < 1 || delayMs > 30000) {
        Serial.println("ERROR:INVALID_DELAY_RANGE");
        return;
    }
    
    try {
        delay(delayMs);
        Serial.println("OK");
    } catch (...) {
        Serial.println("ERROR:DELAY_FAILED");
    }
}