#!/bin/bash

# RFID Reader Installation Script for Raspberry Pi
# This script installs the RFID reader service on a Raspberry Pi running Raspbian

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
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   print_error "This script must be run as root (use sudo)"
   exit 1
fi

# Check if running on Raspberry Pi
if ! grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then
    print_warning "This script is designed for Raspberry Pi. Continue anyway? (y/N)"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

print_status "Starting RFID Reader installation..."

# Update package list
print_status "Updating package list..."
apt-get update

# Install required system packages
print_status "Installing required system packages..."
apt-get install -y python3-pip python3-dev python3-venv git

# Install Python dependencies
print_status "Installing Python dependencies..."
pip3 install mfrc522 RPi.GPIO requests

# Create necessary directories
print_status "Creating directories..."
mkdir -p /etc/rfid_reader
mkdir -p /usr/local/bin
mkdir -p /var/log
mkdir -p /var/lib/rfid_reader

# Copy the RFID reader script
print_status "Installing RFID reader script..."
cp rfid_reader.py /usr/local/bin/
cp db_manager.py /usr/local/bin/
chmod +x /usr/local/bin/rfid_reader.py
chmod +x /usr/local/bin/db_manager.py

# Copy configuration file
print_status "Installing configuration file..."
cp config.toml /etc/rfid_reader/
chmod 644 /etc/rfid_reader/config.toml

# Install systemd service
print_status "Installing systemd service..."
cp rfid-reader.service /etc/systemd/system/
chmod 644 /etc/systemd/system/rfid-reader.service

# Reload systemd
print_status "Reloading systemd..."
systemctl daemon-reload

# Enable service to start on boot
print_status "Enabling service to start on boot..."
systemctl enable rfid-reader.service

# Create log file
print_status "Creating log file..."
touch /var/log/rfid_reader.log
chmod 644 /var/log/rfid_reader.log

# Set database permissions
print_status "Setting database permissions..."
chown -R root:root /var/lib/rfid_reader
chmod 755 /var/lib/rfid_reader

# Configure SPI interface
print_status "Configuring SPI interface..."
if ! grep -q "dtparam=spi=on" /boot/config.txt; then
    echo "dtparam=spi=on" >> /boot/config.txt
    print_status "SPI enabled in /boot/config.txt"
else
    print_status "SPI already enabled"
fi

# Check if SPI is loaded
if ! lsmod | grep -q spi_bcm2835; then
    print_warning "SPI module not loaded. You may need to reboot for SPI to work properly."
fi

print_status "Installation completed successfully!"
echo ""
print_status "Next steps:"
echo "1. Edit the configuration file: sudo nano /etc/rfid_reader/config.toml"
echo "2. Set your webhook URL in the config file"
echo "3. Reboot the Raspberry Pi: sudo reboot"
echo "4. Check service status: sudo systemctl status rfid-reader"
echo "5. View logs: sudo journalctl -u rfid-reader -f"
echo ""
print_status "The service will automatically start on boot and restart if it crashes." 