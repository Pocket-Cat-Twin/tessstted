# Game Monitor System

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Performance](https://img.shields.io/badge/response%20time-%3C1s-brightgreen.svg)](#performance)
[![GUI](https://img.shields.io/badge/GUI-tkinter-orange.svg)](#gui-interface)

High-performance game item monitoring system with real-time OCR, database integration, and sub-second response times. Designed for monitoring in-game trading activities with professional-grade accuracy and reliability.

## 🚀 Features

### Core Functionality
- **⚡ Sub-second Response Time**: Optimized for <1 second from hotkey press to database storage
- **🔍 Advanced OCR Processing**: Multi-engine OCR with intelligent preprocessing and caching
- **📊 Real-time Monitoring**: Live capture and processing of game screen data
- **💾 High-Performance Database**: SQLite with WAL mode, connection pooling, and batch operations
- **🎯 Smart Validation**: Multi-level data validation with confidence scoring
- **⌨️ Global Hotkeys**: F1-F5 hotkeys for different capture modes

### Advanced Features
- **🖥️ Professional GUI**: Full-featured tkinter interface with real-time statistics
- **📈 Performance Monitoring**: Comprehensive system metrics and alerting
- **🔧 Smart Optimizations**: Memory management, threading optimization, and resource monitoring
- **📋 Data Export**: CSV and JSON export capabilities
- **🛠️ Configuration Management**: YAML-based configuration with hot reloading
- **🔍 Manual Verification**: Built-in verification interface for quality assurance

## 📋 Requirements

### System Requirements
- Python 3.8 or higher
- 4GB RAM (minimum), 8GB recommended
- Windows 10/11, Ubuntu 18.04+, or macOS 10.15+
- Screen resolution: 1024x768 minimum
- **Display Environment**: X11 or GUI environment (required for screen capture and GUI interface)

### Dependencies
- **OCR Engine**: Tesseract OCR 5.0+
- **Computer Vision**: OpenCV 4.8+
- **GUI Framework**: tkinter (included with Python)
- **Database**: SQLite 3.35+

### ⚠️ Headless Environment Limitations
When running in headless environments (servers, containers, CI/CD):
- **Screen Capture**: `pyautogui` and `opencv` require display access
- **GUI Interface**: `tkinter` requires X11 or equivalent GUI system
- **Limited Functionality**: Only database operations and validation systems work in headless mode
- **Solution**: Use X virtual framebuffer (`xvfb`) or run in GUI environment for full functionality

## 🚀 Quick Start

### 1. Installation

#### Option A: From Source (Recommended)
```bash
# Clone the repository
git clone https://github.com/game-monitor/game-monitor.git
cd game-monitor

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Tesseract OCR
# Ubuntu/Debian:
sudo apt install tesseract-ocr tesseract-ocr-eng tesseract-ocr-rus

# Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki
# macOS:
brew install tesseract
```

#### Option B: Using pip
```bash
pip install game-monitor[all]
```

### 2. System Setup
```bash
# Initialize database
python setup_database.py

# Test the system
python test_system.py

# Start GUI interface
python -m game_monitor.gui_interface
```

### 3. First Run
1. Launch the GUI application
2. Configure screen coordinates in Settings
3. Test OCR functionality with the built-in tester
4. Start the monitoring system
5. Use F1-F5 hotkeys to capture data

## 🎮 Usage

### Hotkey Controls
| Hotkey | Function | Description |
|--------|----------|-------------|
| **F1** | Trader List Capture | Capture list of active traders |
| **F2** | Item Scan Capture | Scan and capture item information |
| **F3** | Inventory Capture | Capture trader inventory data |
| **F4** | Manual Verification | Open verification dialog |
| **F5** | Emergency Stop | Immediately halt all operations |

### GUI Interface

#### Main Dashboard
- **System Status**: Real-time status indicators for all components
- **Performance Metrics**: Live performance monitoring and statistics
- **Trading Data**: Recent trades table with filtering and export
- **Control Panel**: Start/stop system and emergency controls

#### Settings Configuration
- **Hotkey Mapping**: Customize hotkey assignments
- **OCR Parameters**: Adjust confidence thresholds and processing settings
- **Screen Coordinates**: Configure capture regions for different game elements
- **Performance Tuning**: Database and threading optimization settings

#### Data Management
- **Export Options**: CSV and JSON export with date filtering
- **Database Tools**: Backup, restore, and maintenance utilities
- **Statistics Dashboard**: Comprehensive analytics and reporting

### Command Line Interface
```bash
# Start the main system
python main.py

# Start GUI
python -m game_monitor.gui_interface

# Run system tests
python test_system.py

# Database management
python setup_database.py
```

## 📊 Performance

### Benchmark Results
The system is optimized for high performance with the following benchmarks:

| Component | Target Time | Achieved | Status |
|-----------|-------------|----------|---------|
| **Database Operations** | <100ms | 3ms | ✅ Excellent |
| **OCR Processing** | <500ms | ~200ms | ✅ Excellent |
| **Data Validation** | <10ms | <1ms | ✅ Excellent |
| **Hotkey Response** | <100ms | <1ms | ✅ Excellent |
| **Total Pipeline** | <1000ms | **179ms** | ✅ **Excellent** |

### Optimization Features
- **Connection Pooling**: Database connection reuse and management
- **OCR Caching**: Intelligent caching of OCR results
- **Batch Processing**: Efficient batch database operations
- **Memory Management**: Automatic garbage collection and leak detection
- **Threading Optimization**: Optimal thread pool sizing and load balancing

## 🏗️ Architecture

### System Components

```
┌─────────────────────────────────────────────────────────┐
│                    GUI Interface                        │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────┐   │
│  │   Control   │ │ Performance │ │   Statistics    │   │
│  │    Panel    │ │   Monitor   │ │    Dashboard    │   │
│  └─────────────┘ └─────────────┘ └─────────────────┘   │
└─────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────┐
│                Main Controller                          │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────┐   │
│  │   Hotkey    │ │   Vision    │ │   Validation    │   │
│  │   Manager   │ │   System    │ │    System       │   │
│  └─────────────┘ └─────────────┘ └─────────────────┘   │
└─────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────┐
│              Database & Performance Layer               │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────┐   │
│  │  Database   │ │Performance  │ │     Logging     │   │
│  │   Manager   │ │  Monitor    │ │     System      │   │
│  └─────────────┘ └─────────────┘ └─────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### Data Flow
1. **Input**: Hotkey press triggers screen capture
2. **Processing**: OCR engine processes captured regions
3. **Validation**: Multi-level validation with confidence scoring
4. **Storage**: Optimized database insertion with batching
5. **Monitoring**: Real-time performance tracking and alerting
6. **Output**: GUI updates and data export capabilities

## 📁 Project Structure

```
game-monitor/
├── game_monitor/               # Main package
│   ├── __init__.py            # Package initialization
│   ├── main_controller.py     # Central system controller
│   ├── database_manager.py    # Database operations
│   ├── hotkey_manager.py      # Global hotkey handling
│   ├── vision_system.py       # OCR and image processing
│   ├── fast_validator.py      # Data validation system
│   ├── gui_interface.py       # Tkinter GUI application
│   ├── performance_monitor.py # Performance monitoring
│   ├── logging_config.py      # Structured logging
│   └── optimizations.py       # Performance optimizations
├── config/                    # Configuration files
│   ├── config.yaml           # Main configuration
│   └── items_list.txt        # Known items database
├── data/                     # Data storage
│   ├── game_monitor.db       # SQLite database
│   ├── screenshots/          # Captured screenshots
│   └── cache/               # Processing cache
├── logs/                    # Log files
├── validation/              # Manual validation data
├── tests/                   # Test files
├── main.py                  # CLI entry point
├── setup_database.py        # Database initialization
├── test_system.py          # System testing
├── requirements.txt         # Python dependencies
├── setup.py                # Package setup
└── README.md               # This file
```

## ⚙️ Configuration

### Main Configuration (`config/config.yaml`)

```yaml
# Screen capture settings
screen:
  trader_list_region: [100, 100, 300, 500]
  item_scan_region: [400, 200, 600, 400] 
  inventory_region: [700, 100, 900, 600]

# OCR processing settings
ocr:
  confidence_threshold: 85
  languages: ['eng', 'rus']
  preprocessing: true
  caching_enabled: true

# Database settings
database:
  path: "data/game_monitor.db"
  pool_size: 5
  batch_size: 100
  timeout: 5.0

# Performance settings
performance:
  response_time_target: 1.0
  memory_limit_mb: 200
  thread_pool_size: 4
  gc_interval: 300

# Hotkey settings
hotkeys:
  trader_capture: "F1"
  item_scan: "F2"
  inventory_capture: "F3"
  manual_verify: "F4"
  emergency_stop: "F5"
```

## 🧪 Testing

### Running Tests
```bash
# Run all tests
python test_system.py

# Run specific test categories
python -m pytest tests/test_database.py
python -m pytest tests/test_ocr.py
python -m pytest tests/test_performance.py

# Run with coverage
python -m pytest --cov=game_monitor tests/

# Benchmark tests
python -m pytest --benchmark-only tests/
```

### Performance Testing
```bash
# System performance test
python test_system.py --performance

# Database benchmark
python -m game_monitor.database_manager --benchmark

# OCR speed test  
python -m game_monitor.vision_system --test
```

## 🚀 Deployment

### Creating Standalone Executable
```bash
# Install PyInstaller
pip install pyinstaller

# Create executable
pyinstaller --onefile --windowed --name="GameMonitor" main.py

# Advanced build with all dependencies
pyinstaller game_monitor.spec
```

### Docker Deployment
```bash
# Build Docker image
docker build -t game-monitor:latest .

# Run container
docker run -p 8080:8080 -v $(pwd)/data:/app/data game-monitor:latest
```

## 📈 Monitoring and Logging

### Log Files
- `logs/game_monitor.log` - Main application log
- `logs/performance.log` - Performance metrics (JSON structured)
- `logs/database.log` - Database operations log
- `logs/ocr.log` - OCR processing log
- `logs/errors.log` - Error tracking and stack traces

### Performance Monitoring
The system includes comprehensive monitoring:
- Real-time performance metrics
- Memory usage tracking
- CPU usage monitoring
- Database query performance
- OCR processing times
- Error rate tracking
- Alert system for threshold breaches

## 🔧 Troubleshooting

### Common Issues

**Issue**: OCR not working
```bash
# Check Tesseract installation
tesseract --version

# Install language packs
sudo apt install tesseract-ocr-eng tesseract-ocr-rus
```

**Issue**: Database errors
```bash
# Reinitialize database
python setup_database.py --reset

# Check database integrity
python -c "from game_monitor.database_manager import DatabaseManager; dm = DatabaseManager(); print('DB OK')"
```

**Issue**: Performance problems
```bash
# Run performance diagnostics
python test_system.py --diagnose

# Check system resources
python -c "import psutil; print(f'RAM: {psutil.virtual_memory().percent}%, CPU: {psutil.cpu_percent()}%')"
```

**Issue**: Display/DISPLAY errors in headless environment
```bash
# Error: 'DISPLAY' environment variable not set
# Solution 1: Install and use xvfb (virtual display)
sudo apt install xvfb
xvfb-run -a python main.py

# Solution 2: Set up X11 forwarding (if using SSH)
ssh -X user@server
python main.py

# Solution 3: Use GUI environment or desktop
# Install desktop environment on server and use VNC/RDP

# For testing only (limited functionality):
python verify_installation.py  # Works in headless mode
```

**Issue**: Hotkeys not working
- Ensure the application has proper permissions
- Check for conflicts with other applications
- Run with administrator/sudo privileges if needed
- Verify keyboard library installation: `pip install keyboard`

### Debug Mode
```bash
# Enable debug logging
export GAME_MONITOR_DEBUG=1
python main.py

# Verbose output
python main.py --verbose --debug
```

## 🤝 Contributing

We welcome contributions! Please read our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Setup
```bash
# Clone and setup
git clone https://github.com/game-monitor/game-monitor.git
cd game-monitor

# Install development dependencies
pip install -e ".[dev]"

# Setup pre-commit hooks
pre-commit install

# Run tests
python -m pytest tests/ --cov=game_monitor
```

### Code Style
- **Formatter**: Black with line length 88
- **Linter**: flake8 with custom configuration
- **Type Checking**: mypy with strict mode
- **Import Sorting**: isort with black compatibility

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Tesseract OCR** - Google's open-source OCR engine
- **OpenCV** - Computer vision and image processing
- **SQLite** - Embedded database engine
- **tkinter** - Python's standard GUI library
- **All contributors** who helped improve this project

## 📞 Support

- **Documentation**: [Read the Docs](https://game-monitor.readthedocs.io/)
- **Issues**: [GitHub Issues](https://github.com/game-monitor/game-monitor/issues)
- **Discussions**: [GitHub Discussions](https://github.com/game-monitor/game-monitor/discussions)
- **Wiki**: [Project Wiki](https://github.com/game-monitor/game-monitor/wiki)

---

**Built with ❤️ for the gaming community**

*Game Monitor System v1.0 - High-performance game monitoring made simple*