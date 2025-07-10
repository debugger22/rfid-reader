#!/bin/bash

# SPI Fix Script for Raspberry Pi
# This script fixes common SPI interface issues

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

print_status "Starting SPI interface fix..."

# Check if running on Raspberry Pi
if ! grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then
    print_error "This script is designed for Raspberry Pi only"
    exit 1
fi

print_status "Running on Raspberry Pi"

# Check current SPI status
print_status "Checking current SPI status..."

# Check if SPI is enabled in config
if grep -q "dtparam=spi=on" /boot/config.txt; then
    print_status "✓ SPI enabled in /boot/config.txt"
else
    print_warning "SPI not enabled in /boot/config.txt, adding it..."
    echo "dtparam=spi=on" >> /boot/config.txt
    print_status "✓ Added SPI configuration to /boot/config.txt"
fi

# Check if SPI module is loaded
if lsmod | grep -q spi_bcm2835; then
    print_status "✓ SPI kernel module is loaded"
else
    print_warning "SPI kernel module not loaded, attempting to load it..."
    
    # Try to load the module
    if modprobe spi_bcm2835 2>/dev/null; then
        print_status "✓ Successfully loaded SPI kernel module"
    else
        print_error "Failed to load SPI kernel module"
        print_error "This might require a reboot"
    fi
fi

# Check SPI device files
spi_devices=("/dev/spidev0.0" "/dev/spidev0.1")
spi_found=false

for device in "${spi_devices[@]}"; do
    if [ -e "$device" ]; then
        print_status "✓ Found SPI device: $device"
        spi_found=true
    else
        print_warning "Missing SPI device: $device"
    fi
done

if [ "$spi_found" = false ]; then
    print_error "No SPI devices found!"
    print_error "This usually means the SPI kernel module is not loaded"
    print_error "or the system needs a reboot"
    
    # Try to load SPI module again
    print_status "Attempting to load SPI modules..."
    modprobe spi_bcm2835 2>/dev/null || true
    modprobe spi_bcm2708 2>/dev/null || true
    
    # Check again
    for device in "${spi_devices[@]}"; do
        if [ -e "$device" ]; then
            print_status "✓ SPI device now available: $device"
            spi_found=true
        fi
    done
    
    if [ "$spi_found" = false ]; then
        print_warning "SPI devices still not available"
        print_warning "A reboot may be required"
    fi
fi

# Check GPIO permissions
print_status "Checking GPIO permissions..."

# Add user to gpio group if it exists
if getent group gpio >/dev/null 2>&1; then
    print_status "GPIO group exists"
    # Note: We're running as root, so this is not needed for the service
else
    print_status "GPIO group does not exist (this is normal)"
fi

# Check if we can access GPIO
if python3 -c "import RPi.GPIO as GPIO; GPIO.setmode(GPIO.BCM); GPIO.cleanup()" 2>/dev/null; then
    print_status "✓ GPIO access test passed"
else
    print_warning "GPIO access test failed"
fi

# Summary
print_status "SPI fix completed!"
echo ""
if [ "$spi_found" = true ]; then
    print_status "✓ SPI interface should be working"
    print_status "You can now restart the RFID reader service:"
    echo "  sudo systemctl restart rfid-reader"
else
    print_warning "SPI interface may need a reboot to work properly"
    print_status "Please reboot the Raspberry Pi:"
    echo "  sudo reboot"
fi 