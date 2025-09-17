"""Build script for Voice-to-AI Streaming System distribution."""

import os
import sys
import shutil
import subprocess
from pathlib import Path
import zipfile
import json

# Project information
PROJECT_NAME = "voice-ai-streaming-system"
VERSION = "1.0.0"
BUILD_DIR = Path("build")
DIST_DIR = Path("dist")
SOURCE_DIR = Path("src")

def clean_build_dirs():
    """Clean build and dist directories."""
    print("Cleaning build directories...")
    
    for dir_path in [BUILD_DIR, DIST_DIR]:
        if dir_path.exists():
            shutil.rmtree(dir_path)
            print(f"  Removed {dir_path}")
        
        dir_path.mkdir(exist_ok=True)
        print(f"  Created {dir_path}")

def copy_source_files():
    """Copy source files to build directory."""
    print("Copying source files...")
    
    # Copy src directory
    src_build = BUILD_DIR / "src"
    shutil.copytree(SOURCE_DIR, src_build)
    print(f"  Copied {SOURCE_DIR} to {src_build}")
    
    # Copy configuration files
    config_files = ["requirements.txt", "README.md", "setup.py"]
    for file_name in config_files:
        if Path(file_name).exists():
            shutil.copy2(file_name, BUILD_DIR)
            print(f"  Copied {file_name}")
    
    # Copy config directory
    config_dir = Path("config")
    if config_dir.exists():
        shutil.copytree(config_dir, BUILD_DIR / "config")
        print(f"  Copied {config_dir}")

def create_launcher_scripts():
    """Create launcher scripts for the application."""
    print("Creating launcher scripts...")
    
    # Windows batch script
    bat_content = f"""@echo off
echo Starting Voice-to-AI Streaming System...
cd /d "%~dp0"
python src/main.py
pause
"""
    
    bat_file = BUILD_DIR / f"{PROJECT_NAME}.bat"
    with open(bat_file, 'w') as f:
        f.write(bat_content)
    print(f"  Created {bat_file}")
    
    # Python launcher script
    launcher_content = f'''#!/usr/bin/env python3
"""Launcher script for Voice-to-AI Streaming System."""

import sys
import os
from pathlib import Path

# Add src directory to path
project_dir = Path(__file__).parent
src_dir = project_dir / "src"
sys.path.insert(0, str(src_dir))

# Change to project directory
os.chdir(project_dir)

try:
    from main import main
    sys.exit(main())
except ImportError as e:
    print(f"Import error: {{e}}")
    print("Please ensure all dependencies are installed:")
    print("pip install -r requirements.txt")
    sys.exit(1)
except Exception as e:
    print(f"Error starting application: {{e}}")
    sys.exit(1)
'''
    
    launcher_file = BUILD_DIR / f"{PROJECT_NAME}.py"
    with open(launcher_file, 'w') as f:
        f.write(launcher_content)
    print(f"  Created {launcher_file}")

def create_installation_guide():
    """Create installation guide."""
    print("Creating installation guide...")
    
    guide_content = f"""# Voice-to-AI Streaming System v{VERSION}
# Installation Guide

## Quick Start

1. Extract all files to a directory of your choice
2. Open command prompt in the extracted directory
3. Install dependencies:
   pip install -r requirements.txt
4. Run the application:
   python {PROJECT_NAME}.py
   OR
   Double-click {PROJECT_NAME}.bat

## System Requirements

- Windows 10/11
- Python 3.8 or higher
- Microphone and audio output device
- Internet connection for AI services

## Configuration

1. Run the application for the first time
2. Use Ctrl+Shift+F4 to open settings
3. Configure audio devices
4. Add API keys for STT and AI services
5. Customize hotkeys and overlay settings

## API Keys Required

### Speech-to-Text (choose one):
- Google Cloud Speech API key
- Azure Speech Services key
- Local Whisper (no key needed)

### AI Services (choose one):
- OpenAI API key (for GPT models)
- Anthropic API key (for Claude models)

## Troubleshooting

### Audio Issues:
- Check microphone permissions
- Verify audio device selection in settings
- Try running as administrator

### Hotkey Issues:
- Check for conflicting applications
- Run as administrator
- Try different hotkey combinations

### API Issues:
- Verify API keys are correct
- Check internet connection
- Monitor API usage limits

## Support

For issues or questions, refer to:
- README.md for detailed documentation
- test_system.py for system validation
- Log files in data/logs/ for error details

---
Voice-to-AI Streaming System v{VERSION}
Built with enterprise-grade architecture for reliable real-time voice processing.
"""
    
    guide_file = BUILD_DIR / "INSTALLATION.txt"
    with open(guide_file, 'w', encoding='utf-8') as f:
        f.write(guide_content)
    print(f"  Created {guide_file}")

def create_version_info():
    """Create version information file."""
    print("Creating version info...")
    
    version_info = {
        "name": PROJECT_NAME,
        "version": VERSION,
        "build_date": "2024-01-01",
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "platform": sys.platform,
        "components": [
            "Audio Capture Service",
            "Hotkey Manager", 
            "Speech-to-Text Services",
            "AI Integration",
            "Invisible Overlay System",
            "Settings UI",
            "System Tray Integration"
        ],
        "features": [
            "Dual audio capture (microphone + system output)",
            "Global hotkey support",
            "Multi-provider STT (Google, Azure, Whisper)",
            "AI services (OpenAI, Anthropic)",
            "Windows invisible overlay",
            "Real-time voice activity detection",
            "Configurable settings UI",
            "System tray integration",
            "Performance monitoring",
            "Comprehensive error handling"
        ]
    }
    
    version_file = BUILD_DIR / "version.json"
    with open(version_file, 'w', encoding='utf-8') as f:
        json.dump(version_info, f, indent=2)
    print(f"  Created {version_file}")

def create_portable_package():
    """Create portable ZIP package."""
    print("Creating portable package...")
    
    zip_name = f"{PROJECT_NAME}-v{VERSION}-portable.zip"
    zip_path = DIST_DIR / zip_name
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(BUILD_DIR):
            for file in files:
                file_path = Path(root) / file
                arc_name = file_path.relative_to(BUILD_DIR)
                zipf.write(file_path, arc_name)
                print(f"  Added {arc_name}")
    
    print(f"  Created portable package: {zip_path}")
    print(f"  Package size: {zip_path.stat().st_size / 1024 / 1024:.1f} MB")
    return zip_path

def run_tests():
    """Run system tests before building."""
    print("Running system tests...")
    
    try:
        result = subprocess.run([sys.executable, "test_system.py"], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print("  ✓ All tests passed")
            return True
        else:
            print("  ✗ Tests failed:")
            print(result.stdout)
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"  ✗ Test execution failed: {e}")
        return False

def create_installer_script():
    """Create simple installer script."""
    print("Creating installer script...")
    
    installer_content = f'''@echo off
title Voice-to-AI Streaming System Installer
echo.
echo Voice-to-AI Streaming System v{VERSION}
echo Installation Script
echo.

echo Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://python.org
    pause
    exit /b 1
)

echo Python found. Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    echo Please check your internet connection and Python installation
    pause
    exit /b 1
)

echo.
echo Running system test...
python test_system.py
if errorlevel 1 (
    echo WARNING: System test failed. Some features may not work correctly.
    echo You can still run the application, but check the logs for issues.
    pause
)

echo.
echo Installation completed successfully!
echo.
echo To start the application:
echo   1. Run: python {PROJECT_NAME}.py
echo   2. Or double-click: {PROJECT_NAME}.bat
echo.
echo First-time setup:
echo   1. Configure audio devices in settings (Ctrl+Shift+F4)
echo   2. Add your API keys for STT and AI services
echo   3. Customize hotkeys and overlay preferences
echo.
pause
'''
    
    installer_file = BUILD_DIR / "install.bat"
    with open(installer_file, 'w') as f:
        f.write(installer_content)
    print(f"  Created {installer_file}")

def main():
    """Main build process."""
    print(f"Building {PROJECT_NAME} v{VERSION}")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not SOURCE_DIR.exists():
        print(f"Error: {SOURCE_DIR} directory not found")
        print("Please run this script from the project root directory")
        return False
    
    # Run tests first
    if not run_tests():
        response = input("Tests failed. Continue build anyway? (y/N): ")
        if response.lower() != 'y':
            print("Build cancelled.")
            return False
    
    # Build process
    try:
        clean_build_dirs()
        copy_source_files()
        create_launcher_scripts()
        create_installation_guide()
        create_version_info()
        create_installer_script()
        
        # Create packages
        zip_path = create_portable_package()
        
        print("\n" + "=" * 50)
        print("Build completed successfully!")
        print(f"Portable package: {zip_path}")
        print(f"Build directory: {BUILD_DIR}")
        
        print("\nDistribution contents:")
        print(f"  - Source code and dependencies")
        print(f"  - Launcher scripts ({PROJECT_NAME}.py, {PROJECT_NAME}.bat)")
        print(f"  - Installation guide (INSTALLATION.txt)")
        print(f"  - Installer script (install.bat)")
        print(f"  - Version information (version.json)")
        
        print("\nNext steps:")
        print("  1. Test the portable package on a clean system")
        print("  2. Distribute the ZIP file to users")
        print("  3. Provide INSTALLATION.txt for setup instructions")
        
        return True
        
    except Exception as e:
        print(f"Build failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)