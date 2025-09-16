# Arduino Automation System - Implementation Plan

## Project Overview
Hybrid Python-Arduino automation system with two threads:
- **Main Thread**: Database monitoring + chat automation + OCR screen monitoring  
- **Secondary Thread**: Array processing with click automation
- **Arduino Micro**: Physical mouse clicks and keyboard input via USB HID
- **Python System**: Logic coordination, database operations, Tesseract OCR
- **Target Platform**: Windows with Arduino Micro

## Implementation Tasks

### Phase 1: Core Infrastructure
- [ ] Create project directory structure
- [ ] Setup Arduino IDE code (.ino file) with Mouse/Keyboard HID
- [ ] Implement Python-Arduino serial communication protocol
- [ ] Create configuration system with placeholders
- [ ] Setup database integration with existing market monitoring system
- [ ] Create Tesseract OCR integration replacing Yandex OCR

### Phase 2: Arduino Components  
- [ ] Implement Arduino controller (.ino) with command processor
- [ ] Add Mouse click functionality (CLICK:x,y command)
- [ ] Add Keyboard input functionality (TYPE:text command)
- [ ] Add single key press (KEY:keycode command)
- [ ] Add hotkey combination support (HOTKEY:combination command)
- [ ] Add randomized delay functionality (DELAY:ms command)
- [ ] Test Arduino serial communication and responses

### Phase 3: Python System Core
- [ ] Create ArduinoController class for serial communication
- [ ] Implement connection management and error handling
- [ ] Create DelayManager with 1-2 second randomization
- [ ] Setup database table for automation_targets
- [ ] Integrate with existing DatabaseManager from market monitoring
- [ ] Create TesseractOCR system for screen region monitoring

### Phase 4: Main Thread (Database Monitor)
- [ ] Implement DatabaseMonitorThread class
- [ ] Add database polling for NEW automation targets
- [ ] Implement chat automation sequence:
  - Press Enter via Arduino
  - Insert "/target <название>" text via Arduino
  - Press Enter again via Arduino  
  - Trigger hotkey via Arduino
- [ ] Start OCR screen monitoring after hotkey
- [ ] Implement OCR change detection using Tesseract
- [ ] Execute 9-step mouse movement pattern when OCR changes
- [ ] Update database status after processing

### Phase 5: Secondary Thread (Array Processor)
- [ ] Implement ArrayProcessorThread class
- [ ] Create placeholder name array system
- [ ] Implement click automation sequence:
  - Click Point1 via Arduino
  - Input name from array via Arduino
  - Click Point2 via Arduino
  - Press hotkey via Arduino
- [ ] Add continuous loop with randomized delays
- [ ] Integrate with main thread coordination

### Phase 6: OCR Integration
- [ ] Setup Tesseract OCR with Russian+English support
- [ ] Implement screen region capture for monitoring
- [ ] Add image preprocessing for better OCR accuracy
- [ ] Create OCR change detection logic
- [ ] Implement OCRSequenceManager for 9-step mouse patterns
- [ ] Add pixel offset calculation system
- [ ] Test OCR monitoring with real screen changes

### Phase 7: Configuration & Setup
- [ ] Create automation_config.json with all placeholders
- [ ] Add Arduino connection configuration (COM port detection)
- [ ] Create coordinate placeholder system
- [ ] Add hotkey placeholder configuration  
- [ ] Create name array placeholder system
- [ ] Add pixel offset placeholders for 9-step pattern
- [ ] Create setup guide for replacing placeholders

### Phase 8: Testing & Integration
- [ ] Test Arduino serial communication with Python
- [ ] Test individual Arduino commands (click, type, keys)
- [ ] Test database integration and target processing
- [ ] Test Tesseract OCR accuracy and performance
- [ ] Test thread synchronization and coordination
- [ ] Test complete workflow with placeholder values
- [ ] Performance testing with real automation scenarios

### Phase 9: Documentation & Finalization
- [ ] Create Arduino setup instructions
- [ ] Write Python dependencies and installation guide
- [ ] Document placeholder replacement process
- [ ] Create troubleshooting guide for common issues
- [ ] Add Windows-specific setup instructions
- [ ] Document COM port configuration for Arduino Micro
- [ ] Create complete user manual

### Phase 10: Error Handling & Robustness
- [ ] Add Arduino connection retry logic
- [ ] Implement command failure recovery
- [ ] Add database transaction error handling
- [ ] Create OCR processing error recovery
- [ ] Add thread crash protection and restart
- [ ] Implement logging for all system components
- [ ] Add health monitoring and status reporting

## Technical Specifications

### Hardware Requirements
- **Arduino Micro** (USB HID support for Mouse/Keyboard)
- **Windows System** for COM port communication
- **USB Cable** for Arduino connection

### Software Dependencies

**Python System:**
- pytesseract>=0.3.10 (Free OCR)
- Pillow>=10.0.0 (Image processing)
- opencv-python>=4.8.0 (Image preprocessing)
- pyserial>=3.5 (Arduino communication)
- sqlite3 (Database - built-in)

**Arduino Libraries:**
- Mouse.h (USB HID mouse control)
- Keyboard.h (USB HID keyboard control)

### Communication Protocol
```
Python → Arduino Commands:
- CLICK:x,y (click coordinates)
- TYPE:text (type text string)  
- KEY:keycode (single key press)
- HOTKEY:combination (hotkey combo)
- DELAY:milliseconds (random delay)

Arduino → Python Responses:
- OK (command successful)
- ERROR (command failed)
- READY (Arduino ready for commands)
```

### Database Schema Addition
```sql
CREATE TABLE IF NOT EXISTS automation_targets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    target_name TEXT NOT NULL UNIQUE,
    status TEXT CHECK(status IN ('NEW', 'PROCESSING', 'COMPLETED')) DEFAULT 'NEW',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    processed_at DATETIME,
    processing_attempts INTEGER DEFAULT 0
);
```

### Configuration Structure
- automation_config.json with placeholder system
- Arduino connection settings (COM port, baudrate)
- Coordinate placeholders for all click positions
- Hotkey placeholders for all key combinations
- Name array placeholders for processing sequences
- OCR region and pixel offset placeholders
- Delay randomization configuration (1-2 seconds)

## File Structure
```
arduino_automation_system/
├── todo.md                          # This file
├── arduino_code/
│   ├── arduino_automation_controller.ino
│   └── README_arduino_setup.md
├── python_system/
│   ├── src/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── arduino_controller.py
│   │   ├── database_monitor.py
│   │   ├── array_processor.py
│   │   ├── tesseract_ocr.py
│   │   ├── ocr_sequence_manager.py
│   │   ├── delay_manager.py
│   │   └── database_integration.py
│   ├── config/
│   │   ├── automation_config.json
│   │   └── arduino_setup.json
│   └── tests/
├── requirements.txt
└── setup_guide.md
```

## Success Criteria
- [ ] Arduino Micro successfully controls mouse and keyboard
- [ ] Python system communicates reliably with Arduino via Serial
- [ ] Database integration works with existing market monitoring system
- [ ] Tesseract OCR accurately detects screen region changes
- [ ] Two-thread system operates independently without conflicts
- [ ] All placeholder systems allow easy configuration
- [ ] Complete system runs stable automation sequences
- [ ] Error handling prevents system crashes
- [ ] Documentation enables easy setup and configuration

## Review Section
*[To be filled during implementation with learnings and changes]*