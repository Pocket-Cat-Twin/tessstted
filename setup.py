#!/usr/bin/env python3
"""
Setup configuration for Game Monitor System

Professional packaging and distribution setup for the high-performance
game item monitoring system with all dependencies and configurations.
"""

from setuptools import setup, find_packages
import os
import sys
from pathlib import Path

# Read version from package
def read_version():
    """Read version from game_monitor/__init__.py"""
    version_file = Path(__file__).parent / "game_monitor" / "__init__.py"
    try:
        with open(version_file, 'r') as f:
            for line in f:
                if line.startswith('__version__'):
                    return line.split('=')[1].strip().strip('"\'')
    except FileNotFoundError:
        pass
    return "1.0.0"

# Read long description from README
def read_long_description():
    """Read long description from README.md"""
    readme_file = Path(__file__).parent / "README.md"
    try:
        with open(readme_file, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return "High-performance game item monitoring system with real-time OCR and database integration."

# Check Python version
if sys.version_info < (3, 8):
    raise RuntimeError("Game Monitor requires Python 3.8 or higher")

# Define package data
package_data = {
    'game_monitor': [
        'py.typed',  # Type hint marker
    ],
    '': [
        'config/*.yaml',
        'config/*.txt',
        'logs/.gitkeep',
        'data/.gitkeep',
        'validation/.gitkeep',
    ]
}

# Core dependencies
install_requires = [
    # Core dependencies
    'pyautogui>=0.9.54',
    'opencv-python>=4.8.0.76', 
    'pytesseract>=0.3.10',
    'Pillow>=10.0.1',
    'numpy>=1.24.3',
    'keyboard>=0.13.5',
    'PyYAML>=6.0.1',
    
    # Performance and utilities
    'psutil>=5.9.0',
    
    # Development dependencies (optional)
    'pytest>=7.0.0',
    'pytest-cov>=4.0.0',
    'mypy>=1.0.0',
    'black>=22.0.0',
    'flake8>=5.0.0',
    'isort>=5.10.0',
]

# Extra dependencies for different use cases
extras_require = {
    'dev': [
        'pytest>=7.0.0',
        'pytest-cov>=4.0.0',
        'pytest-benchmark>=4.0.0',
        'mypy>=1.0.0',
        'black>=22.0.0',
        'flake8>=5.0.0',
        'isort>=5.10.0',
        'pre-commit>=2.20.0',
    ],
    'gui': [
        # GUI is built with tkinter (included in Python standard library)
    ],
    'analysis': [
        'matplotlib>=3.5.0',
        'pandas>=1.5.0',
        'jupyter>=1.0.0',
        'plotly>=5.0.0',
    ],
    'packaging': [
        'pyinstaller>=5.0.0',
        'cx-Freeze>=6.0.0',
        'auto-py-to-exe>=2.0.0',
    ]
}

# Add 'all' extras
extras_require['all'] = list(set(sum(extras_require.values(), [])))

# Entry points for command-line interface
entry_points = {
    'console_scripts': [
        'game-monitor=game_monitor.main:main',
        'game-monitor-gui=game_monitor.gui_interface:main',
        'game-monitor-setup=game_monitor.setup_database:main',
        'game-monitor-test=game_monitor.test_system:main',
    ],
}

# Classifiers for PyPI
classifiers = [
    'Development Status :: 5 - Production/Stable',
    'Intended Audience :: End Users/Desktop',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: MIT License',
    'Operating System :: OS Independent',
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 3.8',
    'Programming Language :: Python :: 3.9',
    'Programming Language :: Python :: 3.10',
    'Programming Language :: Python :: 3.11',
    'Programming Language :: Python :: 3.12',
    'Topic :: Games/Entertainment',
    'Topic :: Software Development :: Libraries :: Python Modules',
    'Topic :: System :: Monitoring',
    'Topic :: Multimedia :: Graphics :: Capture :: Screen Capture',
    'Typing :: Typed',
]

# Project URLs
project_urls = {
    'Bug Tracker': 'https://github.com/game-monitor/game-monitor/issues',
    'Documentation': 'https://game-monitor.readthedocs.io/',
    'Source Code': 'https://github.com/game-monitor/game-monitor',
    'Changelog': 'https://github.com/game-monitor/game-monitor/blob/main/CHANGELOG.md',
}

# Keywords for discovery
keywords = [
    'game', 'monitoring', 'ocr', 'screen-capture', 'automation', 
    'trading', 'inventory', 'performance', 'real-time', 'database',
    'tkinter', 'gui', 'tesseract', 'opencv', 'sqlite'
]

setup(
    # Basic package information
    name='game-monitor',
    version=read_version(),
    author='Game Monitor Development Team',
    author_email='dev@game-monitor.local',
    description='High-performance game item monitoring system with real-time OCR and database integration',
    long_description=read_long_description(),
    long_description_content_type='text/markdown',
    url='https://github.com/game-monitor/game-monitor',
    project_urls=project_urls,
    
    # Package discovery
    packages=find_packages(exclude=['tests*', 'docs*', 'examples*']),
    package_data=package_data,
    include_package_data=True,
    
    # Dependencies
    python_requires='>=3.8',
    install_requires=install_requires,
    extras_require=extras_require,
    
    # Entry points
    entry_points=entry_points,
    
    # Metadata
    license='MIT',
    classifiers=classifiers,
    keywords=keywords,
    
    # Additional options
    zip_safe=False,  # Required for some data files
    platforms=['any'],
    
    # Custom commands
    cmdclass={},
    
    # Test suite
    test_suite='tests',
    
    # Options
    options={
        'build_py': {
            'compile': True,
            'optimize': 2,
        },
        'egg_info': {
            'tag_build': '',
            'tag_date': False,
        },
    },
)

# Post-installation setup
def post_install():
    """Post-installation setup tasks"""
    import subprocess
    import sys
    from pathlib import Path
    
    print("Setting up Game Monitor...")
    
    # Create necessary directories
    directories = ['logs', 'data/screenshots', 'data/cache', 'validation/screenshots',
                  'validation/failed_reads', 'validation/manual_confirmations']
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"Created directory: {directory}")
    
    # Check system dependencies
    print("Checking system dependencies...")
    
    # Check Tesseract OCR
    try:
        result = subprocess.run(['tesseract', '--version'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("✓ Tesseract OCR is installed")
        else:
            print("⚠ Tesseract OCR not found - OCR functionality will be limited")
    except (subprocess.TimeoutExpired, FileNotFoundError):
        print("⚠ Tesseract OCR not found - please install tesseract-ocr")
        print("  Ubuntu/Debian: sudo apt install tesseract-ocr tesseract-ocr-eng tesseract-ocr-rus")
        print("  Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki")
        print("  macOS: brew install tesseract")
    
    # Initialize database
    try:
        from game_monitor.database_manager import DatabaseManager
        db_manager = DatabaseManager()
        print("✓ Database initialized successfully")
    except Exception as e:
        print(f"⚠ Database initialization failed: {e}")
    
    print("Game Monitor setup completed!")
    print("\nQuick start:")
    print("1. Run 'game-monitor-setup' to initialize the database")
    print("2. Run 'game-monitor-test' to test the system")
    print("3. Run 'game-monitor-gui' to start the GUI")
    print("4. Run 'game-monitor' to start the command-line interface")

if __name__ == '__main__':
    # Run post-install setup if installing
    if 'install' in sys.argv:
        try:
            post_install()
        except Exception as e:
            print(f"Post-installation setup failed: {e}")
            print("You can run setup manually later with 'game-monitor-setup'")