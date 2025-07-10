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

# Create virtual environment
print_status "Creating virtual environment..."
python3 -m venv /opt/rfid_reader/venv

# Activate virtual environment and install Python dependencies
print_status "Installing Python dependencies in virtual environment..."
/opt/rfid_reader/venv/bin/pip install mfrc522 RPi.GPIO requests

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
cp diagnose.py /usr/local/bin/
cp fix_spi.sh /usr/local/bin/
chmod +x /usr/local/bin/rfid_reader.py
chmod +x /usr/local/bin/db_manager.py
chmod +x /usr/local/bin/diagnose.py
chmod +x /usr/local/bin/fix_spi.sh

# Update shebang to use virtual environment
print_status "Updating scripts to use virtual environment..."
sed -i '1s|#!/usr/bin/env python3|#!/opt/rfid_reader/venv/bin/python|' /usr/local/bin/rfid_reader.py
sed -i '1s|#!/usr/bin/env python3|#!/opt/rfid_reader/venv/bin/python|' /usr/local/bin/db_manager.py
sed -i '1s|#!/usr/bin/env python3|#!/opt/rfid_reader/venv/bin/python|' /usr/local/bin/diagnose.py

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

# Set virtual environment permissions
print_status "Setting virtual environment permissions..."
chown -R root:root /opt/rfid_reader
chmod 755 /opt/rfid_reader
chmod 755 /opt/rfid_reader/venv

# Configure SPI interface
print_status "Configuring SPI interface..."
if ! grep -q "dtparam=spi=on" /boot/config.txt; then
    echo "dtparam=spi=on" >> /boot/config.txt
    print_status "SPI enabled in /boot/config.txt"
else
    print_status "SPI already enabled"
fi

# Try to load SPI module
print_status "Loading SPI kernel module..."
if modprobe spi_bcm2835 2>/dev/null; then
    print_status "✓ SPI kernel module loaded successfully"
else
    print_warning "Could not load SPI kernel module (may need reboot)"
fi

# Check SPI devices
spi_devices=("/dev/spidev0.0" "/dev/spidev0.1")
spi_available=false
for device in "${spi_devices[@]}"; do
    if [ -e "$device" ]; then
        print_status "✓ Found SPI device: $device"
        spi_available=true
    fi
done

if [ "$spi_available" = false ]; then
    print_warning "SPI devices not available. Run fix_spi.sh or reboot."
fi

print_status "Installation completed successfully!"
echo ""
print_status "Next steps:"
echo "1. Edit the configuration file: sudo nano /etc/rfid_reader/config.toml"
echo "2. Set your webhook URL in the config file"
echo "3. If SPI is not working, run: sudo fix_spi.sh"
echo "4. Reboot the Raspberry Pi: sudo reboot"
echo "5. Check service status: sudo systemctl status rfid-reader"
echo "6. View logs: sudo journalctl -u rfid-reader -f"
echo ""
print_status "The service will automatically start on boot and restart if it crashes."
echo ""
print_status "Virtual environment created at: /opt/rfid_reader/venv"
print_status "Python dependencies installed in virtual environment"
echo ""
print_status "Troubleshooting tools available:"
echo "  sudo diagnose.py    - Run comprehensive diagnostics"
echo "  sudo fix_spi.sh     - Fix SPI interface issues" 