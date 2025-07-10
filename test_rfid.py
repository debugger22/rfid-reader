#!/usr/bin/env python3
"""
Test script for RFID Reader
This script can be used to test the RFID reader functionality
"""

import logging
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_imports():
    """Test if all required modules can be imported"""
    logger.info("Testing imports...")
    
    try:
        import RPi.GPIO as GPIO
        logger.info("✓ RPi.GPIO imported successfully")
    except ImportError as e:
        logger.error(f"✗ Failed to import RPi.GPIO: {e}")
        return False
    
    try:
        from mfrc522 import SimpleMFRC522
        logger.info("✓ mfrc522 imported successfully")
    except ImportError as e:
        logger.error(f"✗ Failed to import mfrc522: {e}")
        return False
    
    try:
        import requests
        logger.info("✓ requests imported successfully")
    except ImportError as e:
        logger.error(f"✗ Failed to import requests: {e}")
        return False
    
    try:
        import tomllib
        logger.info("✓ tomllib imported successfully")
    except ImportError as e:
        logger.error(f"✗ Failed to import tomllib: {e}")
        return False
    
    return True

def test_config():
    """Test configuration file loading"""
    logger.info("Testing configuration...")
    
    config_path = "/etc/rfid_reader/config.toml"
    
    if not Path(config_path).exists():
        logger.error(f"✗ Configuration file not found: {config_path}")
        return False
    
    try:
        import tomllib
        with open(config_path, 'rb') as f:
            config = tomllib.load(f)
        
        logger.info("✓ Configuration file loaded successfully")
        logger.info(f"  Webhook URL: {config.get('webhook_url', 'Not set')}")
        logger.info(f"  Device ID: {config.get('device_id', 'Will be auto-generated')}")
        
        return True
    except Exception as e:
        logger.error(f"✗ Failed to load configuration: {e}")
        return False

def test_gpio():
    """Test GPIO access"""
    logger.info("Testing GPIO access...")
    
    try:
        import RPi.GPIO as GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(18, GPIO.OUT)  # Test pin
        GPIO.output(18, GPIO.LOW)
        GPIO.output(18, GPIO.HIGH)
        GPIO.cleanup()
        logger.info("✓ GPIO access successful")
        return True
    except Exception as e:
        logger.error(f"✗ GPIO access failed: {e}")
        return False

def test_rfid_reader():
    """Test RFID reader initialization"""
    logger.info("Testing RFID reader...")
    
    try:
        from mfrc522 import SimpleMFRC522
        reader = SimpleMFRC522()
        logger.info("✓ RFID reader initialized successfully")
        return True
    except Exception as e:
        logger.error(f"✗ RFID reader initialization failed: {e}")
        return False

def test_webhook():
    """Test webhook connectivity"""
    logger.info("Testing webhook connectivity...")
    
    try:
        import requests
        import tomllib
        
        config_path = "/etc/rfid_reader/config.toml"
        if Path(config_path).exists():
            with open(config_path, 'rb') as f:
                config = tomllib.load(f)
            
            webhook_url = config.get('webhook_url')
            if webhook_url and webhook_url != "https://your-webhook-endpoint.com/rfid":
                try:
                    response = requests.get(webhook_url, timeout=5)
                    logger.info(f"✓ Webhook URL accessible (Status: {response.status_code})")
                    return True
                except requests.exceptions.RequestException as e:
                    logger.warning(f"⚠ Webhook URL not accessible: {e}")
                    return True  # Don't fail the test for webhook issues
            else:
                logger.info("✓ Webhook URL not configured (this is OK)")
                return True
        else:
            logger.info("✓ No config file found (this is OK for testing)")
            return True
    except Exception as e:
        logger.error(f"✗ Webhook test failed: {e}")
        return False

def test_database():
    """Test database functionality"""
    logger.info("Testing database functionality...")
    
    try:
        import sqlite3
        from pathlib import Path
        
        db_path = "/var/lib/rfid_reader/card_reads.db"
        db_dir = Path(db_path).parent
        
        # Check if database directory exists
        if not db_dir.exists():
            logger.warning("⚠ Database directory doesn't exist yet (will be created on first run)")
            return True
        
        # Try to connect to database
        if Path(db_path).exists():
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='card_reads'")
            if cursor.fetchone():
                logger.info("✓ Database exists and has required table")
            else:
                logger.warning("⚠ Database exists but missing required table (will be created on first run)")
            conn.close()
        else:
            logger.info("✓ Database doesn't exist yet (will be created on first run)")
        
        return True
    except Exception as e:
        logger.error(f"✗ Database test failed: {e}")
        return False

def main():
    """Run all tests"""
    logger.info("Starting RFID Reader tests...")
    
    tests = [
        ("Import Test", test_imports),
        ("Configuration Test", test_config),
        ("GPIO Test", test_gpio),
        ("RFID Reader Test", test_rfid_reader),
        ("Webhook Test", test_webhook),
        ("Database Test", test_database)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\n--- {test_name} ---")
        if test_func():
            passed += 1
        else:
            logger.error(f"{test_name} failed!")
    
    logger.info(f"\n--- Test Results ---")
    logger.info(f"Passed: {passed}/{total}")
    
    if passed == total:
        logger.info("✓ All tests passed! RFID reader should work correctly.")
        return 0
    else:
        logger.error("✗ Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 