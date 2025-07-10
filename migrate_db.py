#!/usr/bin/env python3
"""
Database Migration Script for RFID Reader
Migrates from old schema (card_value only) to new schema (card_id + card_value)
"""

import logging
import sqlite3
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_schema_version(db_path: str) -> str:
    """Check the current schema version of the database"""
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Check if card_id column exists
            cursor.execute("PRAGMA table_info(card_reads)")
            columns = [row[1] for row in cursor.fetchall()]
            
            if 'card_id' in columns:
                return "new"
            else:
                return "old"
                
    except Exception as e:
        logger.error(f"Error checking schema: {e}")
        return "unknown"

def migrate_database(db_path: str):
    """Migrate database from old schema to new schema"""
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Check current schema
            schema_version = check_schema_version(db_path)
            
            if schema_version == "new":
                logger.info("Database already has new schema (card_id + card_value)")
                return
            
            if schema_version == "unknown":
                logger.error("Could not determine database schema")
                return
            
            logger.info("Migrating database from old schema to new schema...")
            
            # Create new table with new schema
            cursor.execute('''
                CREATE TABLE card_reads_new (
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
            
            # Copy data from old table to new table
            # In the old schema, card_value contained the card ID
            # In the new schema, we'll use the old card_value as card_id and set card_value to empty
            cursor.execute('''
                INSERT INTO card_reads_new (
                    id, device_id, card_id, card_value, timestamp, 
                    sync_status, sync_attempts, last_sync_attempt, next_retry, 
                    webhook_response, created_at
                )
                SELECT 
                    id, device_id, card_value, '', timestamp,
                    sync_status, sync_attempts, last_sync_attempt, next_retry,
                    webhook_response, created_at
                FROM card_reads
            ''')
            
            # Drop old table and rename new table
            cursor.execute('DROP TABLE card_reads')
            cursor.execute('ALTER TABLE card_reads_new RENAME TO card_reads')
            
            # Create indexes
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_sync_status 
                ON card_reads(sync_status)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_next_retry 
                ON card_reads(next_retry)
            ''')
            
            conn.commit()
            logger.info("Database migration completed successfully!")
            
    except Exception as e:
        logger.error(f"Error during migration: {e}")
        raise

def main():
    """Main migration function"""
    db_path = "/var/lib/rfid_reader/card_reads.db"
    
    if not Path(db_path).exists():
        logger.info("Database does not exist yet, no migration needed")
        return
    
    try:
        logger.info(f"Checking database schema: {db_path}")
        schema_version = check_schema_version(db_path)
        
        if schema_version == "new":
            logger.info("Database already has the new schema")
        elif schema_version == "old":
            logger.info("Database has old schema, migrating...")
            migrate_database(db_path)
        else:
            logger.error("Could not determine database schema")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 