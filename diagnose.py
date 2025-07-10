#!/usr/bin/env python3
"""
Diagnostic script for RFID Reader
Helps identify issues with the RFID reader setup
"""

import logging
import os
import subprocess
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_python_environment():
    """Check Python environment"""
    print("=== Python Environment ===")
    print(f"Python version: {sys.version}")
    print(f"Python executable: {sys.executable}")
    print(f"Current working directory: {os.getcwd()}")
    
    # Check if running in virtual environment
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("✓ Running in virtual environment")
    else:
        print("⚠ Not running in virtual environment")

def check_dependencies():
    """Check if required dependencies are available"""
    print("\n=== Dependencies ===")
    
    dependencies = [
        ('RPi.GPIO', 'GPIO access'),
        ('mfrc522', 'RFID reader library'),
        ('requests', 'HTTP requests'),
        ('tomllib', 'TOML configuration'),
        ('sqlite3', 'Database support'),
        ('spidev', 'SPI interface')
    ]
    
    for module, description in dependencies:
        try:
            __import__(module)
            print(f"✓ {module} - {description}")
        except ImportError as e:
            print(f"✗ {module} - {description} ({e})")

def check_file_permissions():
    """Check file permissions and existence"""
    print("\n=== File Permissions ===")
    
    files_to_check = [
        '/usr/local/bin/rfid_reader.py',
        '/usr/local/bin/db_manager.py',
        '/etc/rfid_reader/config.toml',
        '/var/lib/rfid_reader',
        '/opt/rfid_reader/venv/bin/python'
    ]
    
    for file_path in files_to_check:
        path = Path(file_path)
        if path.exists():
            try:
                stat = path.stat()
                print(f"✓ {file_path} - exists, permissions: {oct(stat.st_mode)[-3:]}")
            except Exception as e:
                print(f"✗ {file_path} - exists but error accessing: {e}")
        else:
            print(f"✗ {file_path} - does not exist")

def check_spi_interface():
    """Check SPI interface status"""
    print("\n=== SPI Interface ===")
    
    # Check if running on Raspberry Pi
    try:
        with open('/proc/cpuinfo', 'r') as f:
            if 'Raspberry Pi' in f.read():
                print("✓ Running on Raspberry Pi")
            else:
                print("⚠ Not running on Raspberry Pi")
    except Exception as e:
        print(f"✗ Could not check CPU info: {e}")
    
    # Check SPI config
    try:
        with open('/boot/config.txt', 'r') as f:
            content = f.read()
            if 'dtparam=spi=on' in content:
                print("✓ SPI enabled in /boot/config.txt")
            else:
                print("✗ SPI not enabled in /boot/config.txt")
    except Exception as e:
        print(f"✗ Could not check /boot/config.txt: {e}")
    
    # Check loaded modules
    try:
        result = subprocess.run(['lsmod'], capture_output=True, text=True)
        if 'spi_bcm2835' in result.stdout:
            print("✓ SPI kernel module loaded")
        else:
            print("✗ SPI kernel module not loaded")
    except Exception as e:
        print(f"✗ Could not check loaded modules: {e}")
    
    # Check SPI device files
    spi_devices = ['/dev/spidev0.0', '/dev/spidev0.1']
    for device in spi_devices:
        if Path(device).exists():
            print(f"✓ {device} exists")
        else:
            print(f"✗ {device} does not exist")

def check_database_access():
    """Check database access"""
    print("\n=== Database Access ===")
    
    db_path = "/var/lib/rfid_reader/card_reads.db"
    db_dir = Path(db_path).parent
    
    try:
        # Check if directory can be created
        db_dir.mkdir(parents=True, exist_ok=True)
        print(f"✓ Database directory accessible: {db_dir}")
        
        # Test database creation
        import sqlite3
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS test_table (id INTEGER)")
        conn.commit()
        conn.close()
        print("✓ Database creation test passed")
        
        # Clean up test table
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("DROP TABLE test_table")
        conn.commit()
        conn.close()
        
    except Exception as e:
        print(f"✗ Database access failed: {e}")

def check_network_connectivity():
    """Check network connectivity"""
    print("\n=== Network Connectivity ===")
    
    try:
        import requests
        response = requests.get('https://httpbin.org/get', timeout=5)
        if response.status_code == 200:
            print("✓ Internet connectivity test passed")
        else:
            print(f"⚠ Internet connectivity test failed: {response.status_code}")
    except Exception as e:
        print(f"✗ Internet connectivity test failed: {e}")

def check_config_file():
    """Check configuration file"""
    print("\n=== Configuration File ===")
    
    config_path = "/etc/rfid_reader/config.toml"
    
    if Path(config_path).exists():
        print(f"✓ Configuration file exists: {config_path}")
        
        try:
            import tomllib
            with open(config_path, 'rb') as f:
                config = tomllib.load(f)
            
            print("✓ Configuration file is valid TOML")
            
            # Check required fields
            if 'webhook_url' in config:
                print(f"✓ webhook_url configured: {config['webhook_url']}")
            else:
                print("✗ webhook_url not configured")
            
            if 'api_key' in config:
                print(f"✓ api_key configured: {config['api_key'][:8]}...")
            else:
                print("⚠ api_key not configured (optional)")
                
        except Exception as e:
            print(f"✗ Configuration file error: {e}")
    else:
        print(f"✗ Configuration file not found: {config_path}")

def run_step_by_step_test():
    """Run a step-by-step test of the RFID reader initialization"""
    print("\n=== Step-by-Step Test ===")
    
    try:
        print("1. Testing configuration loading...")
        import tomllib
        with open('/etc/rfid_reader/config.toml', 'rb') as f:
            config = tomllib.load(f)
        print("✓ Configuration loaded")
        
        print("2. Testing device ID generation...")
        import hashlib
        import subprocess
        import time

        # Get CPU serial number
        with open('/proc/cpuinfo', 'r') as f:
            for line in f:
                if line.startswith('Serial'):
                    serial = line.split(':')[1].strip()
                    break
            else:
                serial = "unknown"
        
        # Get MAC address
        try:
            result = subprocess.run(['ip', 'link', 'show'], capture_output=True, text=True)
            mac_lines = [line for line in result.stdout.split('\n') if 'link/ether' in line]
            if mac_lines:
                mac = mac_lines[0].split()[1]
            else:
                mac = "unknown"
        except:
            mac = "unknown"
        
        unique_string = f"{serial}_{mac}_{int(time.time())}"
        device_id = hashlib.md5(unique_string.encode()).hexdigest()[:12]
        print(f"✓ Device ID generated: {device_id}")
        
        print("3. Testing database initialization...")
        from rfid_reader import DatabaseManager
        db_manager = DatabaseManager()
        print("✓ Database manager initialized")
        
        print("4. Testing RFID reader initialization...")
        from mfrc522 import SimpleMFRC522
        reader = SimpleMFRC522()
        print("✓ RFID reader initialized")
        
        print("5. Testing GPIO access...")
        import RPi.GPIO as GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(18, GPIO.OUT)
        GPIO.output(18, GPIO.LOW)
        GPIO.output(18, GPIO.HIGH)
        GPIO.cleanup()
        print("✓ GPIO access successful")
        
        print("\n🎉 All tests passed! RFID reader should work correctly.")
        
    except Exception as e:
        print(f"\n❌ Test failed at step: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")

def main():
    """Run all diagnostic checks"""
    print("RFID Reader Diagnostic Tool")
    print("=" * 50)
    
    check_python_environment()
    check_dependencies()
    check_file_permissions()
    check_spi_interface()
    check_database_access()
    check_network_connectivity()
    check_config_file()
    run_step_by_step_test()
    
    print("\n" + "=" * 50)
    print("Diagnostic complete!")

if __name__ == "__main__":
    main() 