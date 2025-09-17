"""Setup script for Voice-to-AI Streaming System."""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_path = Path(__file__).parent / "README.md"
long_description = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""

# Read requirements
requirements_path = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_path.exists():
    with open(requirements_path, 'r', encoding='utf-8') as f:
        requirements = [
            line.strip() 
            for line in f 
            if line.strip() and not line.startswith('#') and not line.startswith('-')
        ]

setup(
    name="voice-ai-streaming-system",
    version="1.0.0",
    description="Real-time voice-to-AI streaming system with invisible overlay",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Voice-AI Team",
    author_email="support@voice-ai.com",
    url="https://github.com/voice-ai/streaming-system",
    
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    
    install_requires=requirements,
    
    entry_points={
        "console_scripts": [
            "voice-ai=main:main",
            "voice-ai-test=test_system:main",
        ],
    },
    
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: Microsoft :: Windows",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Multimedia :: Sound/Audio :: Capture/Recording",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    
    python_requires=">=3.8",
    
    include_package_data=True,
    package_data={
        "": ["*.json", "*.yaml", "*.yml", "*.txt", "*.md"],
        "config": ["*.json"],
        "data": ["*"],
    },
    
    keywords="voice ai speech recognition streaming overlay hotkeys",
    
    project_urls={
        "Bug Reports": "https://github.com/voice-ai/streaming-system/issues",
        "Source": "https://github.com/voice-ai/streaming-system",
        "Documentation": "https://docs.voice-ai.com",
    },
)