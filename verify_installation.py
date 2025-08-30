#!/usr/bin/env python3
"""
Installation Verification Script for Game Monitor System

Comprehensive verification of all components and dependencies
to ensure proper installation and functionality.
"""

import sys
import os
import subprocess
import importlib
import sqlite3
from pathlib import Path
import time


def print_header(title: str):
    """Print formatted header"""
    print(f"\n{'=' * 60}")
    print(f" {title}")
    print(f"{'=' * 60}")


def print_section(title: str):
    """Print formatted section"""
    print(f"\n{'-' * 40}")
    print(f" {title}")
    print(f"{'-' * 40}")


def check_python_version():
    """Check Python version requirements"""
    print_section("Python Version Check")
    
    version = sys.version_info
    print(f"Python Version: {version.major}.{version.minor}.{version.micro}")
    
    if version >= (3, 8):
        print("✅ Python version meets requirements (3.8+)")
        return True
    else:
        print("❌ Python version too old. Requires 3.8 or higher")
        return False


def check_system_dependencies():
    """Check system-level dependencies"""
    print_section("System Dependencies")
    
    all_good = True
    
    # Check Tesseract OCR
    try:
        result = subprocess.run(['tesseract', '--version'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            version = result.stdout.split('\n')[0]
            print(f"✅ Tesseract OCR: {version}")
        else:
            print("❌ Tesseract OCR: Not working properly")
            all_good = False
    except (subprocess.TimeoutExpired, FileNotFoundError):
        print("❌ Tesseract OCR: Not found")
        print("   Install with:")
        print("   Ubuntu/Debian: sudo apt install tesseract-ocr tesseract-ocr-eng tesseract-ocr-rus")
        print("   Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki")
        print("   macOS: brew install tesseract")
        all_good = False
    
    # Check language packs
    try:
        result = subprocess.run(['tesseract', '--list-langs'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            langs = result.stdout.strip().split('\n')[1:]  # Skip header
            if 'eng' in langs:
                print("✅ English OCR support available")
            else:
                print("⚠️  English OCR support missing")
            
            if 'rus' in langs:
                print("✅ Russian OCR support available")
            else:
                print("⚠️  Russian OCR support missing")
    except Exception:
        print("⚠️  Could not check OCR language support")
    
    return all_good


def check_python_dependencies():
    """Check Python package dependencies"""
    print_section("Python Dependencies")
    
    required_packages = [
        ('pyautogui', 'Screen capture functionality'),
        ('cv2', 'Computer vision (OpenCV)'),
        ('pytesseract', 'OCR processing'),
        ('PIL', 'Image processing (Pillow)'),
        ('numpy', 'Numerical operations'),
        ('keyboard', 'Global hotkey support'),
        ('yaml', 'Configuration management'),
        ('psutil', 'System monitoring'),
        ('tkinter', 'GUI framework'),
        ('sqlite3', 'Database operations'),
        ('threading', 'Concurrency support'),
        ('queue', 'Thread-safe queues'),
    ]
    
    all_good = True
    
    for package, description in required_packages:
        try:
            if package == 'cv2':
                importlib.import_module('cv2')
            else:
                importlib.import_module(package)
            print(f"✅ {package:15} - {description}")
        except ImportError as e:
            if package in ['pyautogui', 'cv2'] and ('DISPLAY' in str(e) or 'libGL' in str(e) or 'display' in str(e)):
                print(f"⚠️  {package:15} - {description} (Requires graphics environment)")
            else:
                print(f"❌ {package:15} - {description} (MISSING)")
                all_good = False
        except KeyError as e:
            if "'DISPLAY'" in str(e) and package in ['pyautogui', 'tkinter']:
                print(f"⚠️  {package:15} - {description} (Requires display)")
            else:
                print(f"❌ {package:15} - {description} (ERROR: {e})")
                all_good = False
        except Exception as e:
            error_msg = str(e)
            if package in ['pyautogui', 'cv2'] and ('DISPLAY' in error_msg or 'libGL' in error_msg):
                print(f"⚠️  {package:15} - {description} (Requires graphics environment)")
            else:
                print(f"❌ {package:15} - {description} (ERROR: {error_msg[:50]}...)")
                all_good = False
    
    return all_good


def check_project_structure():
    """Check project directory structure"""
    print_section("Project Structure")
    
    required_dirs = [
        ('game_monitor/', 'Main package directory'),
        ('config/', 'Configuration files'),
        ('data/', 'Database and cache storage'),
        ('logs/', 'Log files'),
        ('validation/', 'Manual validation tools'),
        ('tests/', 'Test suite'),
    ]
    
    required_files = [
        ('main.py', 'CLI entry point'),
        ('setup_database.py', 'Database initialization'),
        ('test_system.py', 'System testing'),
        ('requirements.txt', 'Python dependencies'),
        ('setup.py', 'Package setup'),
        ('README.md', 'Documentation'),
        ('config/config.yaml', 'Main configuration'),
        ('config/items_list.txt', 'Known items list'),
    ]
    
    all_good = True
    
    # Check directories
    for dir_path, description in required_dirs:
        if Path(dir_path).exists():
            print(f"✅ {dir_path:20} - {description}")
        else:
            print(f"❌ {dir_path:20} - {description} (MISSING)")
            all_good = False
    
    # Check files
    for file_path, description in required_files:
        if Path(file_path).exists():
            print(f"✅ {file_path:20} - {description}")
        else:
            print(f"❌ {file_path:20} - {description} (MISSING)")
            all_good = False
    
    return all_good


def check_game_monitor_components():
    """Check Game Monitor system components"""
    print_section("Game Monitor Components")
    
    components = [
        ('database_manager', 'Database operations'),
        ('fast_validator', 'Data validation'),
        ('hotkey_manager', 'Global hotkeys'),
        ('performance_monitor', 'Performance monitoring'),
        ('logging_config', 'Structured logging'),
        ('optimizations', 'Performance optimizations'),
    ]
    
    # Components requiring display (test imports only)
    display_components = [
        ('vision_system', 'OCR and image processing'),
        ('gui_interface', 'GUI application'),
        ('main_controller', 'System controller'),
    ]
    
    all_good = True
    
    # Test core components
    sys.path.insert(0, str(Path.cwd()))
    
    for component, description in components:
        try:
            module = importlib.import_module(f'game_monitor.{component}')
            print(f"✅ {component:20} - {description}")
        except Exception as e:
            print(f"❌ {component:20} - {description} (ERROR: {e})")
            all_good = False
    
    # Test display-dependent components (import only)
    for component, description in display_components:
        try:
            # We expect these to fail in headless environment
            module = importlib.import_module(f'game_monitor.{component}')
            print(f"✅ {component:20} - {description}")
        except KeyError as e:
            if "'DISPLAY'" in str(e):
                print(f"⚠️  {component:20} - {description} (Needs display)")
            else:
                print(f"❌ {component:20} - {description} (ERROR: {e})")
                all_good = False
        except Exception as e:
            print(f"❌ {component:20} - {description} (ERROR: {e})")
            all_good = False
    
    return all_good


def check_database_functionality():
    """Check database functionality"""
    print_section("Database Functionality")
    
    try:
        from game_monitor.database_manager import DatabaseManager
        
        # Initialize database manager
        db_manager = DatabaseManager()
        print("✅ Database manager initialized")
        
        # Test basic operations
        total_trades = db_manager.get_total_trades_count()
        print(f"✅ Database query successful (trades: {total_trades})")
        
        # Test new methods we added
        unique_traders = db_manager.get_unique_traders_count()
        unique_items = db_manager.get_unique_items_count()
        print(f"✅ Statistics queries work (traders: {unique_traders}, items: {unique_items})")
        
        return True
        
    except Exception as e:
        print(f"❌ Database functionality failed: {e}")
        return False


def check_performance_components():
    """Check performance monitoring components"""
    print_section("Performance Components")
    
    try:
        from game_monitor.performance_monitor import PerformanceMonitor
        
        perf_monitor = PerformanceMonitor()
        print("✅ Performance monitor initialized")
        
        # Test memory optimization
        from game_monitor.optimizations import get_memory_optimizer
        mem_opt = get_memory_optimizer()
        
        memory_stats = mem_opt.get_memory_usage()
        print(f"✅ Memory monitoring works ({memory_stats['rss_mb']:.1f}MB)")
        
        return True
        
    except Exception as e:
        print(f"❌ Performance components failed: {e}")
        return False


def run_quick_system_test():
    """Run a quick system functionality test"""
    print_section("Quick System Test")
    
    try:
        # Test core components that don't need display
        from game_monitor.fast_validator import FastValidator
        from game_monitor.hotkey_manager import HotkeyManager
        
        # Test validator
        validator = FastValidator()
        result = validator.validate_trader_nickname("TestTrader123")
        print(f"✅ Validator works (confidence: {result.confidence:.2f})")
        
        # Test hotkey manager in simulation mode
        hotkey_manager = HotkeyManager()
        print("✅ Hotkey manager initialized")
        
        hotkey_manager.stop()
        print("✅ Quick system test completed")
        
        return True
        
    except Exception as e:
        print(f"❌ Quick system test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def print_summary(checks_passed: list, total_checks: int):
    """Print verification summary"""
    print_header("VERIFICATION SUMMARY")
    
    passed = sum(checks_passed)
    
    print(f"Total Checks: {total_checks}")
    print(f"Passed: {passed}")
    print(f"Failed: {total_checks - passed}")
    print(f"Success Rate: {(passed/total_checks)*100:.1f}%")
    
    if passed == total_checks:
        print("\n🎉 ALL CHECKS PASSED!")
        print("✅ Game Monitor System is properly installed and ready to use.")
        print("\n📋 Next Steps:")
        print("1. Run 'python main.py' to start the CLI interface")
        print("2. Run 'python -m game_monitor.gui_interface' to start the GUI (with display)")
        print("3. Use F1-F5 hotkeys to capture game data")
    elif passed >= total_checks * 0.8:
        print("\n✅ MOSTLY WORKING!")
        print("⚠️  Some components have issues but core functionality is available.")
        print("   Check failed components above for details.")
    else:
        print("\n❌ SIGNIFICANT ISSUES FOUND!")
        print("   Please resolve the failed checks before using the system.")
        print("   See installation guide in README.md for help.")


def main():
    """Main verification function"""
    print_header("GAME MONITOR SYSTEM - INSTALLATION VERIFICATION")
    print("Verifying all components and dependencies...")
    
    checks = []
    
    # Run all verification checks
    checks.append(check_python_version())
    checks.append(check_system_dependencies())
    checks.append(check_python_dependencies()) 
    checks.append(check_project_structure())
    checks.append(check_game_monitor_components())
    checks.append(check_database_functionality())
    checks.append(check_performance_components())
    checks.append(run_quick_system_test())
    
    # Print summary
    print_summary(checks, len(checks))
    
    # Return exit code
    if all(checks):
        return 0
    else:
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)