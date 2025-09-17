# Voice-to-AI Streaming System

Enterprise-grade real-time voice processing system with invisible overlay for AI-powered responses. 

## Features

### Core Functionality
- **Dual Audio Capture**: Separate recording from microphone (user) and system output (interlocutor)
- **Hotkey System**: Global hotkeys for start/stop recording with configurable key combinations
- **Real-time STT**: Speech-to-text conversion with multiple provider support (Google, Azure, Whisper)
- **AI Integration**: Streaming responses from OpenAI GPT-4 and Anthropic Claude
- **Invisible Overlay**: Transparent window display with always-on-top functionality
- **Voice Activity Detection**: Smart detection of speech vs. silence

### Architecture Highlights
- **Event-driven**: Decoupled components communicating via event bus
- **Multi-threaded**: Separate threads for audio, STT, AI, and UI operations  
- **State Management**: Centralized state tracking with real-time updates
- **Configuration**: Comprehensive settings with JSON persistence
- **Logging**: Multi-level logging with component-specific outputs
- **Performance Monitoring**: Real-time CPU, memory, and latency tracking

## Project Structure

```
voice_ai_streaming_system/
├── README.md                    # This file
├── requirements.txt             # Python dependencies
├── todo.md                      # Development roadmap
├── config/
│   ├── default_config.json      # Default configuration
│   ├── settings.py              # Configuration management
│   └── user_config.json         # User customizations (created at runtime)
├── src/
│   ├── main.py                  # Application entry point
│   ├── audio/                   # Audio processing modules
│   │   ├── capture_service.py   # Dual audio capture (mic + system)
│   │   ├── buffer_manager.py    # Audio buffer management
│   │   └── vad_detector.py      # Voice activity detection
│   ├── hotkeys/                 # Global hotkey system
│   │   └── hotkey_manager.py    # Hotkey registration and handling
│   ├── stt/                     # Speech-to-text services
│   │   ├── base_stt.py          # STT service interface
│   │   ├── google_stt.py        # Google Cloud Speech
│   │   ├── azure_stt.py         # Azure Speech Services
│   │   └── whisper_stt.py       # Local Whisper processing
│   ├── ai/                      # AI response services
│   │   ├── base_ai.py           # AI service interface
│   │   ├── openai_client.py     # OpenAI GPT integration
│   │   └── anthropic_client.py  # Anthropic Claude integration
│   ├── overlay/                 # Invisible overlay system
│   │   ├── invisible_window.py  # Windows overlay implementation
│   │   └── overlay_manager.py   # Overlay control logic
│   ├── ui/                      # User interface components
│   │   ├── settings_window.py   # Configuration UI
│   │   └── system_tray.py       # System tray integration
│   ├── core/                    # Core system components
│   │   ├── event_bus.py         # Inter-component communication
│   │   ├── state_manager.py     # Global state management
│   │   └── thread_coordinator.py # Threading management
│   └── utils/                   # Utility modules
│       └── logger.py            # Logging framework
├── tests/                       # Unit and integration tests
└── data/
    ├── logs/                    # Application logs
    └── recordings/              # Temporary audio storage
```

## Installation

### Prerequisites
- Python 3.8+
- Windows 10/11 (for overlay functionality)
- Audio input/output devices

### Setup
1. Clone or extract the project
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Configure API keys in `config/user_config.json`
4. Run the application:
   ```bash
   python src/main.py
   ```

## Configuration

### Audio Settings
- **Sample Rate**: 16kHz (recommended) or higher
- **Buffer Size**: 1024 samples for optimal latency
- **Device Selection**: Automatic detection with manual override
- **VAD**: Voice Activity Detection with WebRTC or energy-based algorithms

### Hotkey Configuration
Default hotkeys (customizable):
- `Ctrl+Shift+F1`: Start recording
- `Ctrl+Shift+F2`: Stop recording and process
- `Ctrl+Shift+F3`: Toggle overlay visibility
- `Ctrl+Shift+F4`: Toggle settings window
- `Ctrl+Shift+Esc`: Emergency stop

### API Configuration
Required API keys:
- **Google Cloud Speech**: Service account credentials
- **Azure Speech**: Subscription key and region
- **OpenAI**: API key for GPT models
- **Anthropic**: API key for Claude models

## Usage Workflow

1. **Start Application**: Launch with `python src/main.py`
2. **Configure Settings**: Set audio devices and API credentials
3. **Begin Recording**: Press `Ctrl+Shift+F1` to start capturing interlocutor audio
4. **Process Voice**: Press `Ctrl+Shift+F2` to stop recording and send to AI
5. **View Response**: AI response appears in invisible overlay
6. **Repeat**: Continue conversation cycle

## Performance Targets

- **Audio Latency**: < 50ms buffer latency
- **STT Processing**: < 500ms for short phrases  
- **AI Response**: < 2000ms for first token
- **Resource Usage**: < 20% CPU, < 300MB RAM
- **Overlay Rendering**: < 16ms for smooth display

## Development Status

### Completed Components ✅
- [x] Project structure and configuration system
- [x] Comprehensive logging framework  
- [x] Event-driven architecture with event bus
- [x] Global state management system
- [x] Thread coordination and management
- [x] Dual audio capture (microphone + system output)
- [x] Audio buffer management with circular buffers
- [x] Voice activity detection (WebRTC + energy-based)
- [x] Global hotkey system with multiple backends
- [x] Core infrastructure and base classes

### Next Development Phases 🚧
- [ ] STT service implementation (Google, Azure, Whisper)
- [ ] AI response services (OpenAI, Anthropic)  
- [ ] Invisible overlay system (Windows-specific)
- [ ] Settings UI and system tray integration
- [ ] End-to-end integration testing
- [ ] Performance optimization and monitoring
- [ ] Error handling and recovery mechanisms
- [ ] Packaging and distribution

## Architecture Patterns

### Event-Driven Communication
```python
# Components communicate via events
event_bus.emit(EventType.RECORDING_STARTED, "audio_capture", {
    "device": "microphone",
    "timestamp": time.time()
})
```

### State Management
```python
# Centralized state updates
state_manager.update_recording_state(
    is_recording=True,
    start_time=time.time()
)
```

### Thread Coordination
```python
# Managed thread lifecycle
thread_coordinator.start_thread(
    "audio_capture",
    audio_capture_function,
    ThreadType.AUDIO_CAPTURE
)
```

### Configuration Management
```python
# Type-safe configuration
settings = config_manager.get_settings()
audio_config = settings.audio
```

## Security & Privacy

- **No persistent audio storage**: Audio deleted after processing
- **API key encryption**: Secure credential storage using Windows DPAPI
- **Local processing**: Minimize data transmission to external services
- **User consent**: Clear disclosure of data usage and processing

## Contributing

This is an enterprise-grade implementation focusing on:
- **Code Quality**: Type hints, comprehensive error handling
- **Performance**: Optimized for real-time processing
- **Maintainability**: Clear separation of concerns
- **Testability**: Modular design with dependency injection
- **Documentation**: Comprehensive inline and external documentation

## License

Internal development project - see organization licensing terms.

## Support

For technical issues or feature requests, refer to the development team or internal documentation systems.