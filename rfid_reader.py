#!/usr/bin/env python3
"""
RFID Reader for Raspberry Pi
Reads RFID cards using RC522 module and sends data to webhook
"""

import hashlib
import logging
import os
import sqlite3
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import requests
import tomllib

try:
    import RPi.GPIO as GPIO
    from mfrc522 import SimpleMFRC522
except ImportError as e:
    print(f"Error: Required libraries not found. Please install: pip install mfrc522 RPi.GPIO requests")
    print(f"Import error: {e}")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/rfid_reader.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_path: str = "/var/lib/rfid_reader/card_reads.db"):
        self.db_path = db_path
        self.ensure_db_directory()
        self.init_database()
    
    def ensure_db_directory(self):
        """Ensure the database directory exists"""
        try:
            db_dir = os.path.dirname(self.db_path)
            os.makedirs(db_dir, exist_ok=True)
            logger.info(f"Database directory ensured: {db_dir}")
        except Exception as e:
            logger.error(f"Error creating database directory: {e}")
            raise
    
    def init_database(self):
        """Initialize the database with required tables"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create card_reads table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS card_reads (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        device_id TEXT NOT NULL,
                        card_id TEXT NOT NULL,
                        card_value TEXT NOT NULL,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        sync_status TEXT DEFAULT 'pending',
                        sync_attempts INTEGER DEFAULT 0,
                        last_sync_attempt DATETIME,
                        next_retry DATETIME,
                        webhook_response TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create index for efficient querying
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_sync_status 
                    ON card_reads(sync_status)
                ''')
                
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_next_retry 
                    ON card_reads(next_retry)
                ''')
                
                conn.commit()
                logger.info(f"Database initialized: {self.db_path}")
                
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise
    
    def insert_card_read(self, device_id: str, card_id: str, card_value: str) -> int:
        """Insert a new card read into the database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO card_reads (device_id, card_id, card_value, next_retry)
                    VALUES (?, ?, ?, datetime('now'))
                ''', (device_id, card_id, card_value))
                conn.commit()
                row_id = cursor.lastrowid
                logger.info(f"Card read stored in database: ID={card_id}, Value='{card_value}' (DB ID: {row_id})")
                return row_id
        except Exception as e:
            logger.error(f"Error inserting card read: {e}")
            raise
    
    def get_pending_syncs(self, max_age_days: int = 7) -> List[Tuple]:
        """Get all pending syncs that are ready for retry"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, device_id, card_id, card_value, timestamp, sync_attempts, last_sync_attempt
                    FROM card_reads 
                    WHERE sync_status = 'pending' 
                    AND (next_retry IS NULL OR next_retry <= datetime('now'))
                    AND created_at >= datetime('now', '-{} days')
                    ORDER BY created_at ASC
                '''.format(max_age_days))
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting pending syncs: {e}")
            return []
    
    def update_sync_status(self, row_id: int, status: str, response: str = None, attempts: int = None):
        """Update the sync status of a card read"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if status == 'success':
                    cursor.execute('''
                        UPDATE card_reads 
                        SET sync_status = ?, webhook_response = ?, last_sync_attempt = datetime('now')
                        WHERE id = ?
                    ''', (status, response, row_id))
                else:
                    # Calculate next retry time with exponential backoff
                    if attempts is None:
                        cursor.execute('SELECT sync_attempts FROM card_reads WHERE id = ?', (row_id,))
                        attempts = cursor.fetchone()[0] + 1
                    
                    # Exponential backoff: 1min, 2min, 4min, 8min, 16min, 32min, 1hour, 2hours, 4hours, 8hours, 12hours, 24hours
                    backoff_minutes = min(2 ** (attempts - 1), 1440)  # Max 24 hours
                    next_retry = datetime.now() + timedelta(minutes=backoff_minutes)
                    
                    cursor.execute('''
                        UPDATE card_reads 
                        SET sync_status = ?, sync_attempts = ?, last_sync_attempt = datetime('now'), 
                            next_retry = ?, webhook_response = ?
                        WHERE id = ?
                    ''', (status, attempts, next_retry.strftime('%Y-%m-%d %H:%M:%S'), response, row_id))
                
                conn.commit()
                logger.info(f"Updated sync status for row {row_id}: {status}")
                
        except Exception as e:
            logger.error(f"Error updating sync status: {e}")
    
    def get_sync_stats(self) -> Dict[str, int]:
        """Get synchronization statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT sync_status, COUNT(*) 
                    FROM card_reads 
                    GROUP BY sync_status
                ''')
                stats = dict(cursor.fetchall())
                return stats
        except Exception as e:
            logger.error(f"Error getting sync stats: {e}")
            return {}

class RFIDReader:
    def __init__(self, config_path: str = "/etc/rfid_reader/config.toml"):
        self.config_path = config_path
        self.config = self.load_config()
        self.device_id = self.get_device_id()
        
        # Initialize database first
        logger.info("Initializing database manager...")
        try:
            self.db_manager = DatabaseManager()
            logger.info("Database manager initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database manager: {e}")
            raise
        
        # Initialize RFID reader
        logger.info("Initializing RFID reader...")
        
        # Check if SPI is available
        try:
            import spidev
            logger.info("SPI interface check passed")
        except ImportError:
            logger.warning("spidev not available, SPI interface may not work properly")
        
        # Check SPI interface status
        try:
            with open('/proc/cpuinfo', 'r') as f:
                if 'Raspberry Pi' in f.read():
                    logger.info("Running on Raspberry Pi")
                    
                    # Check if SPI is enabled in config
                    try:
                        with open('/boot/config.txt', 'r') as config:
                            if 'dtparam=spi=on' in config.read():
                                logger.info("SPI enabled in /boot/config.txt")
                            else:
                                logger.warning("SPI not enabled in /boot/config.txt")
                    except Exception as e:
                        logger.warning(f"Could not check /boot/config.txt: {e}")
                    
                    # Check if SPI module is loaded
                    try:
                        result = subprocess.run(['lsmod'], capture_output=True, text=True)
                        if 'spi_bcm2835' in result.stdout:
                            logger.info("SPI kernel module loaded")
                        else:
                            logger.warning("SPI kernel module not loaded")
                    except Exception as e:
                        logger.warning(f"Could not check loaded modules: {e}")
                else:
                    logger.info("Not running on Raspberry Pi")
        except Exception as e:
            logger.warning(f"Could not check system info: {e}")
        
        try:
            self.reader = SimpleMFRC522()
            logger.info("RFID reader initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize RFID reader: {e}")
            logger.error("This might be due to:")
            logger.error("1. SPI not enabled in /boot/config.txt")
            logger.error("2. SPI kernel module not loaded")
            logger.error("3. Hardware not connected properly")
            logger.error("4. Insufficient permissions")
            raise
        
        self.last_card_id = None
        self.sync_thread = None
        self.running = False
        
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from TOML file"""
        try:
            with open(self.config_path, 'rb') as f:
                config = tomllib.load(f)
            logger.info(f"Configuration loaded from {self.config_path}")
            return config
        except FileNotFoundError:
            logger.error(f"Configuration file not found: {self.config_path}")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            sys.exit(1)
    
    def generate_device_id(self) -> str:
        """Generate a unique device ID based on hardware info"""
        try:
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
            
            # Create unique ID
            unique_string = f"{serial}_{mac}_{int(time.time())}"
            device_id = hashlib.md5(unique_string.encode()).hexdigest()[:12]
            
            return device_id
        except Exception as e:
            logger.error(f"Error generating device ID: {e}")
            return f"rfid_{int(time.time())}"
    
    def get_device_id(self) -> str:
        """Get or generate device ID"""
        device_id = self.config.get('device_id')
        
        if not device_id:
            # Generate new device ID
            device_id = self.generate_device_id()
            
            # Update config file
            self.update_config_device_id(device_id)
            logger.info(f"Generated new device ID: {device_id}")
        else:
            logger.info(f"Using existing device ID: {device_id}")
        
        return device_id
    
    def update_config_device_id(self, device_id: str):
        """Update the config file with the new device ID"""
        try:
            # Read current config
            with open(self.config_path, 'r') as f:
                content = f.read()
            
            # Add or update device_id
            if 'device_id' in content:
                # Update existing device_id
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if line.strip().startswith('device_id'):
                        lines[i] = f'device_id = "{device_id}"'
                        break
                content = '\n'.join(lines)
            else:
                # Add device_id at the end
                content += f'\ndevice_id = "{device_id}"\n'
            
            # Write back to file
            with open(self.config_path, 'w') as f:
                f.write(content)
                
            logger.info(f"Updated config file with device ID: {device_id}")
        except Exception as e:
            logger.error(f"Error updating config file: {e}")
    
    def send_webhook(self, card_id: str, card_value: str) -> Tuple[bool, str]:
        """Send RFID data to webhook and return success status and response"""
        webhook_url = self.config.get('webhook_url')
        if not webhook_url:
            logger.warning("No webhook URL configured, skipping webhook call")
            return False, "No webhook URL configured"
        
        payload = {
            'device_id': self.device_id,
            'card_id': card_id,
            'card_value': card_value
        }
        
        # Prepare headers
        headers = {'Content-Type': 'application/json'}
        
        # Add API key if configured
        api_key = self.config.get('api_key')
        if api_key:
            headers['x-api-key'] = api_key
            logger.debug("API key included in webhook request")
        
        try:
            response = requests.post(
                webhook_url,
                json=payload,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"Webhook sent successfully: {card_value}")
                return True, response.text
            else:
                logger.error(f"Webhook failed with status {response.status_code}: {response.text}")
                return False, f"HTTP {response.status_code}: {response.text}"
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending webhook: {e}")
            return False, str(e)
    
    def read_card(self) -> Optional[tuple]:
        """Read RFID card and return (card_id, card_value) tuple"""
        try:
            id, text = self.reader.read()
            card_id = str(id)
            card_value = text.strip() if text else ""
            
            if card_id != self.last_card_id:
                self.last_card_id = card_id
                logger.info(f"Card detected: ID={card_id}, Value='{card_value}'")
                return (card_id, card_value)
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error reading RFID card: {e}")
            return None
    
    def sync_pending_data(self):
        """Sync all pending data to the webhook"""
        pending_syncs = self.db_manager.get_pending_syncs()
        
        if not pending_syncs:
            return
        
        logger.info(f"Attempting to sync {len(pending_syncs)} pending records...")
        
        for row_id, device_id, card_id, card_value, timestamp, attempts, last_attempt in pending_syncs:
            try:
                success, response = self.send_webhook(card_id, card_value)
                
                if success:
                    self.db_manager.update_sync_status(row_id, 'success', response)
                    logger.info(f"Successfully synced card read {row_id}: ID={card_id}, Value='{card_value}'")
                else:
                    new_attempts = attempts + 1
                    self.db_manager.update_sync_status(row_id, 'pending', response, new_attempts)
                    logger.warning(f"Failed to sync card read {row_id}: ID={card_id}, Value='{card_value}' (attempt {new_attempts})")
                    
            except Exception as e:
                logger.error(f"Error syncing card read {row_id}: {e}")
                new_attempts = attempts + 1
                self.db_manager.update_sync_status(row_id, 'pending', str(e), new_attempts)
    
    def sync_worker(self):
        """Background worker for syncing data"""
        while self.running:
            try:
                self.sync_pending_data()
                
                # Log sync statistics
                stats = self.db_manager.get_sync_stats()
                if stats:
                    logger.info(f"Sync stats: {stats}")
                
                # Wait before next sync attempt
                time.sleep(30)  # Sync every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in sync worker: {e}")
                time.sleep(60)  # Wait longer on error
    
    def run(self):
        """Main loop to continuously read RFID cards"""
        logger.info("Starting RFID reader service...")
        logger.info(f"Device ID: {self.device_id}")
        logger.info(f"Webhook URL: {self.config.get('webhook_url', 'Not configured')}")
        
        # Start sync worker thread
        self.running = True
        self.sync_thread = threading.Thread(target=self.sync_worker, daemon=True)
        self.sync_thread.start()
        logger.info("Background sync worker started")
        
        try:
            while True:
                card_data = self.read_card()
                
                if card_data:
                    card_id, card_value = card_data
                    # Store in database immediately (write-through)
                    try:
                        row_id = self.db_manager.insert_card_read(self.device_id, card_id, card_value)
                        logger.info(f"Card read stored: ID={card_id}, Value='{card_value}' (DB ID: {row_id})")
                    except Exception as e:
                        logger.error(f"Failed to store card read in database: {e}")
                
                # Small delay to prevent excessive CPU usage
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            logger.info("RFID reader service stopped by user")
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}")
        finally:
            self.running = False
            if self.sync_thread:
                self.sync_thread.join(timeout=5)
            GPIO.cleanup()
            logger.info("GPIO cleanup completed")

def main():
    """Main entry point"""
    try:
        logger.info("Starting RFID reader application...")
        reader = RFIDReader()
        logger.info("RFID reader initialized successfully, starting main loop...")
        reader.run()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        sys.exit(1)

if __name__ == "__main__":
    main() 