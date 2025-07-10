#!/usr/bin/env python3
"""
Database Management Utility for RFID Reader
Provides tools to view and manage the SQLite database
"""

import argparse
import sqlite3
import sys
from pathlib import Path


def connect_db(db_path: str = "/var/lib/rfid_reader/card_reads.db"):
    """Connect to the database"""
    if not Path(db_path).exists():
        print(f"Database not found: {db_path}")
        sys.exit(1)
    
    return sqlite3.connect(db_path)

def show_stats(db_path: str):
    """Show database statistics"""
    conn = connect_db(db_path)
    cursor = conn.cursor()
    
    print("=== RFID Reader Database Statistics ===")
    
    # Total records
    cursor.execute("SELECT COUNT(*) FROM card_reads")
    total = cursor.fetchone()[0]
    print(f"Total records: {total}")
    
    # Sync status breakdown
    cursor.execute("""
        SELECT sync_status, COUNT(*) 
        FROM card_reads 
        GROUP BY sync_status
    """)
    status_counts = cursor.fetchall()
    
    print("\nSync Status Breakdown:")
    for status, count in status_counts:
        percentage = (count / total * 100) if total > 0 else 0
        print(f"  {status}: {count} ({percentage:.1f}%)")
    
    # Recent activity
    cursor.execute("""
        SELECT COUNT(*) 
        FROM card_reads 
        WHERE created_at >= datetime('now', '-1 hour')
    """)
    recent = cursor.fetchone()[0]
    print(f"\nRecords in last hour: {recent}")
    
    # Failed syncs
    cursor.execute("""
        SELECT COUNT(*) 
        FROM card_reads 
        WHERE sync_status = 'pending' AND sync_attempts > 0
    """)
    failed = cursor.fetchone()[0]
    print(f"Failed syncs (with attempts): {failed}")
    
    conn.close()

def show_recent(db_path: str, limit: int = 20):
    """Show recent card reads"""
    conn = connect_db(db_path)
    cursor = conn.cursor()
    
    print(f"=== Recent Card Reads (Last {limit}) ===")
    
    cursor.execute("""
        SELECT id, device_id, card_id, card_value, timestamp, sync_status, sync_attempts, created_at
        FROM card_reads 
        ORDER BY created_at DESC 
        LIMIT ?
    """, (limit,))
    
    records = cursor.fetchall()
    
    if not records:
        print("No records found.")
        return
    
    print(f"{'ID':<5} {'Card ID':<15} {'Card Value':<20} {'Status':<10} {'Attempts':<10} {'Created':<20}")
    print("-" * 85)
    
    for record in records:
        row_id, device_id, card_id, card_value, timestamp, sync_status, attempts, created_at = record
        # Truncate long values for display
        display_card_id = card_id[:14] + "..." if len(card_id) > 14 else card_id
        display_card_value = card_value[:19] + "..." if len(card_value) > 19 else card_value
        print(f"{row_id:<5} {display_card_id:<15} {display_card_value:<20} {sync_status:<10} {attempts:<10} {created_at:<20}")
    
    conn.close()

def show_pending(db_path: str):
    """Show pending syncs"""
    conn = connect_db(db_path)
    cursor = conn.cursor()
    
    print("=== Pending Syncs ===")
    
    cursor.execute("""
        SELECT id, card_id, card_value, sync_attempts, last_sync_attempt, next_retry, created_at
        FROM card_reads 
        WHERE sync_status = 'pending'
        ORDER BY created_at ASC
    """)
    
    records = cursor.fetchall()
    
    if not records:
        print("No pending syncs found.")
        return
    
    print(f"{'ID':<5} {'Card ID':<15} {'Card Value':<20} {'Attempts':<10} {'Last Attempt':<20} {'Next Retry':<20}")
    print("-" * 95)
    
    for record in records:
        row_id, card_id, card_value, attempts, last_attempt, next_retry, created_at = record
        last_attempt_str = last_attempt if last_attempt else "Never"
        next_retry_str = next_retry if next_retry else "Now"
        # Truncate long values for display
        display_card_id = card_id[:14] + "..." if len(card_id) > 14 else card_id
        display_card_value = card_value[:19] + "..." if len(card_value) > 19 else card_value
        print(f"{row_id:<5} {display_card_id:<15} {display_card_value:<20} {attempts:<10} {last_attempt_str:<20} {next_retry_str:<20}")
    
    conn.close()

def retry_failed(db_path: str):
    """Reset failed syncs to retry immediately"""
    conn = connect_db(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE card_reads 
        SET next_retry = datetime('now')
        WHERE sync_status = 'pending'
    """)
    
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    
    print(f"Reset {affected} pending records to retry immediately.")

def cleanup_old(db_path: str, days: int = 30):
    """Clean up old successful records"""
    conn = connect_db(db_path)
    cursor = conn.cursor()
    
    # Count records to be deleted
    cursor.execute("""
        SELECT COUNT(*) 
        FROM card_reads 
        WHERE sync_status = 'success' 
        AND created_at < datetime('now', '-{} days')
    """.format(days))
    
    count = cursor.fetchone()[0]
    
    if count == 0:
        print("No old successful records to clean up.")
        return
    
    # Delete old successful records
    cursor.execute("""
        DELETE FROM card_reads 
        WHERE sync_status = 'success' 
        AND created_at < datetime('now', '-{} days')
    """.format(days))
    
    conn.commit()
    conn.close()
    
    print(f"Cleaned up {count} old successful records (older than {days} days).")

def export_data(db_path: str, output_file: str):
    """Export data to CSV"""
    import csv
    
    conn = connect_db(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT device_id, card_id, card_value, timestamp, sync_status, sync_attempts, 
               last_sync_attempt, created_at
        FROM card_reads 
        ORDER BY created_at DESC
    """)
    
    records = cursor.fetchall()
    conn.close()
    
    with open(output_file, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Device ID', 'Card ID', 'Card Value', 'Timestamp', 'Sync Status', 
                        'Sync Attempts', 'Last Sync Attempt', 'Created At'])
        writer.writerows(records)
    
    print(f"Exported {len(records)} records to {output_file}")

def main():
    parser = argparse.ArgumentParser(description="RFID Reader Database Manager")
    parser.add_argument('--db', default="/var/lib/rfid_reader/card_reads.db", 
                       help="Database file path")
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Stats command
    subparsers.add_parser('stats', help='Show database statistics')
    
    # Recent command
    recent_parser = subparsers.add_parser('recent', help='Show recent card reads')
    recent_parser.add_argument('--limit', type=int, default=20, 
                              help='Number of records to show')
    
    # Pending command
    subparsers.add_parser('pending', help='Show pending syncs')
    
    # Retry command
    subparsers.add_parser('retry', help='Reset failed syncs to retry immediately')
    
    # Cleanup command
    cleanup_parser = subparsers.add_parser('cleanup', help='Clean up old successful records')
    cleanup_parser.add_argument('--days', type=int, default=30, 
                               help='Delete records older than N days')
    
    # Export command
    export_parser = subparsers.add_parser('export', help='Export data to CSV')
    export_parser.add_argument('output', help='Output CSV file path')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        if args.command == 'stats':
            show_stats(args.db)
        elif args.command == 'recent':
            show_recent(args.db, args.limit)
        elif args.command == 'pending':
            show_pending(args.db)
        elif args.command == 'retry':
            retry_failed(args.db)
        elif args.command == 'cleanup':
            cleanup_old(args.db, args.days)
        elif args.command == 'export':
            export_data(args.db, args.output)
    
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 