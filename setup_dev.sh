#!/bin/bash

# Development Setup Script for RFID Reader
# This script sets up the development environment for testing

set -e

# Colors for output
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

print_status "Setting up RFID Reader development environment..."

# Create virtual environment
print_status "Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
print_status "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
print_status "Installing Python dependencies..."
pip install -r requirements.txt

# Create local config
print_status "Creating local configuration..."
mkdir -p local_config
cp config.toml local_config/

print_status "Development environment setup complete!"
echo ""
print_status "To activate the environment:"
echo "  source venv/bin/activate"
echo ""
print_status "To run the RFID reader in development mode:"
echo "  python rfid_reader.py"
echo ""
print_status "To run the test webhook server:"
echo "  python test_webhook_server.py"
echo ""
print_status "To run tests:"
echo "  python test_rfid.py" 