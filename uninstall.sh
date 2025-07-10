#!/bin/bash

# RFID Reader Uninstall Script
# This script removes the RFID reader service from the system

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1
}

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   print_error "This script must be run as root (use sudo)"
   exit 1
fi

print_status "Starting RFID Reader uninstallation..."

# Stop and disable the service
print_status "Stopping and disabling service..."
systemctl stop rfid-reader.service 2>/dev/null || true
systemctl disable rfid-reader.service 2>/dev/null || true

# Remove systemd service file
print_status "Removing systemd service file..."
rm -f /etc/systemd/system/rfid-reader.service

# Reload systemd
print_status "Reloading systemd..."
systemctl daemon-reload

# Remove installed files
print_status "Removing installed files..."
rm -f /usr/local/bin/rfid_reader.py
rm -f /usr/local/bin/db_manager.py

# Remove configuration directory (ask user first)
if [ -d "/etc/rfid_reader" ]; then
    print_warning "Do you want to remove the configuration directory (/etc/rfid_reader)? (y/N)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        rm -rf /etc/rfid_reader
        print_status "Configuration directory removed"
    else
        print_status "Configuration directory kept at /etc/rfid_reader"
    fi
fi

# Remove log file (ask user first)
if [ -f "/var/log/rfid_reader.log" ]; then
    print_warning "Do you want to remove the log file (/var/log/rfid_reader.log)? (y/N)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        rm -f /var/log/rfid_reader.log
        print_status "Log file removed"
    else
        print_status "Log file kept at /var/log/rfid_reader.log"
    fi
fi

# Ask about removing virtual environment
print_warning "Do you want to remove the virtual environment (/opt/rfid_reader/venv)? (y/N)"
read -r response
if [[ "$response" =~ ^[Yy]$ ]]; then
    print_status "Removing virtual environment..."
    rm -rf /opt/rfid_reader
    print_status "Virtual environment removed"
else
    print_status "Virtual environment kept at /opt/rfid_reader/venv"
fi

# Ask about removing Python packages (if not using virtual env)
print_warning "Do you want to remove the Python packages (mfrc522, RPi.GPIO, requests) from system Python? (y/N)"
read -r response
if [[ "$response" =~ ^[Yy]$ ]]; then
    print_status "Removing Python packages..."
    pip3 uninstall -y mfrc522 RPi.GPIO requests 2>/dev/null || true
    print_status "Python packages removed"
else
    print_status "Python packages kept (they may be used by other applications)"
fi

print_status "Uninstallation completed successfully!"
print_status "The RFID reader service has been removed from the system." 