"""
Patch to enable .env file support for API key configuration.
Run this file once to modify settings.py for .env support.
"""

import os
from pathlib import Path

def patch_settings_file():
    """Add .env support to settings.py file."""
    
    settings_file = Path("src/config/settings.py")
    
    if not settings_file.exists():
        print("❌ Error: settings.py not found")
        return False
    
    # Read current content
    content = settings_file.read_text(encoding='utf-8')
    
    # Check if already patched
    if "from dotenv import load_dotenv" in content:
        print("✅ Settings.py already patched for .env support")
        return True
    
    # Add dotenv import after other imports
    import_section = '''import json
import os
from pathlib import Path'''
    
    new_import_section = '''import json
import os
from pathlib import Path
try:
    from dotenv import load_dotenv
    load_dotenv()  # Load .env file if available
except ImportError:
    pass  # dotenv not installed, continue without it'''
    
    content = content.replace(import_section, new_import_section)
    
    # Modify the API key loading to check environment first
    old_api_key_line = "api_key=ocr_data['api_key'],"
    new_api_key_line = '''api_key=os.getenv('YANDEX_API_KEY') or ocr_data['api_key'],'''
    
    content = content.replace(old_api_key_line, new_api_key_line)
    
    # Write back
    settings_file.write_text(content, encoding='utf-8')
    
    print("✅ Settings.py patched successfully!")
    print("📝 Now you can use .env file with YANDEX_API_KEY=your_key")
    return True

if __name__ == "__main__":
    print("🔧 Patching settings.py for .env support...")
    patch_settings_file()