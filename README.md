# RFID Reader for Raspberry Pi

A Python-based RFID reader service for Raspberry Pi that reads RFID cards using the RC522 module and sends data to a webhook endpoint.

## Features

- **RFID Card Reading**: Continuously reads RFID cards using the RC522 module
- **Webhook Integration**: Sends card data to a configurable webhook URL
- **Local Database Storage**: SQLite database for storing all card reads with timestamps
- **Offline Resilience**: Stores events locally when offline and syncs when connection is restored
- **Retry Logic**: Exponential backoff retry system with up to 1 week persistence
- **Write-Through Architecture**: All card reads are immediately stored in database
- **Device ID Management**: Auto-generates unique device IDs or uses configured ones
- **Background Service**: Runs as a systemd service that starts on boot
- **Logging**: Comprehensive logging to both file and system journal
- **Error Handling**: Robust error handling with automatic service restart
- **Raspbian Compatible**: Designed specifically for Raspberry Pi running Raspbian OS

## Hardware Requirements

- Raspberry Pi (any model)
- RC522 RFID Reader Module
- RFID cards/tags

## Wiring Diagram

Connect the RC522 module to your Raspberry Pi as follows:

| RC522 Pin | Raspberry Pi GPIO |
|-----------|-------------------|
| SDA       | GPIO 8 (Pin 24)  |
| SCK       | GPIO 11 (Pin 23) |
| MOSI      | GPIO 10 (Pin 19) |
| MISO      | GPIO 9 (Pin 21)  |
| RST       | GPIO 25 (Pin 22) |
| VCC       | 3.3V             |
| GND       | GND              |

## Installation

### Quick Install

1. Clone this repository:
   ```bash
   git clone <repository-url>
   cd rfid-reader
   ```

2. Run the installation script:
   ```bash
   sudo chmod +x install.sh
   sudo ./install.sh
   ```

### Manual Installation

1. Install system dependencies:
   ```bash
   sudo apt-get update
   sudo apt-get install python3-pip python3-dev
   ```

2. Install Python dependencies:
   ```bash
   pip3 install -r requirements.txt
   ```

3. Copy files to system locations:
   ```bash
   sudo mkdir -p /etc/rfid_reader
   sudo cp rfid_reader.py /usr/local/bin/
   sudo cp config.toml /etc/rfid_reader/
   sudo cp rfid-reader.service /etc/systemd/system/
   sudo chmod +x /usr/local/bin/rfid_reader.py
   ```

4. Enable SPI interface:
   ```bash
   echo "dtparam=spi=on" | sudo tee -a /boot/config.txt
   ```

5. Enable and start the service:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable rfid-reader.service
   sudo systemctl start rfid-reader.service
   ```

## Configuration

Edit the configuration file at `/etc/rfid_reader/config.toml`:

```toml
# Device ID (auto-generated if not set)
# device_id = "your_device_id_here"

# Webhook URL to send RFID data
webhook_url = "https://your-webhook-endpoint.com/rfid"

# API Key for webhook authentication (optional)
# api_key = "your_api_key_here"

# Optional: GPIO pins for RC522 (default values)
# sda_pin = 8
# sck_pin = 11
# mosi_pin = 10
# miso_pin = 9
# rst_pin = 25

# Optional: Logging level
# log_level = "INFO"
```

### Configuration Options

- **device_id**: Unique identifier for this device. If not set, a unique ID will be generated based on hardware information.
- **webhook_url**: URL where RFID data will be sent via POST requests.
- **api_key**: API key for webhook authentication. If set, will be included as `x-api-key` header.
- **GPIO pins**: Customize the GPIO pins used for the RC522 module (optional).
- **log_level**: Set logging verbosity (DEBUG, INFO, WARNING, ERROR).

## Webhook Data Format

The service sends POST requests to your webhook URL with the following JSON payload:

```json
{
  "device_id": "abc123def456",
  "value": "123456789"
}
```

### Headers
- **Content-Type**: `application/json`
- **x-api-key**: `your_api_key` (if api_key is configured in config.toml)

### Payload Fields
- **device_id**: The unique identifier for this RFID reader device
- **value**: The RFID card ID that was read

## Service Management

### Start the service:
```bash
sudo systemctl start rfid-reader.service
```

### Stop the service:
```bash
sudo systemctl stop rfid-reader.service
```

### Check service status:
```bash
sudo systemctl status rfid-reader.service
```

### View logs:
```bash
# View systemd logs
sudo journalctl -u rfid-reader -f

# View application logs
sudo tail -f /var/log/rfid_reader.log
```

### Restart the service:
```bash
sudo systemctl restart rfid-reader.service
```

## Database Management

The RFID reader uses SQLite to store all card reads locally. The database is located at `/var/lib/rfid_reader/card_reads.db`.

### View database statistics:
```bash
sudo db_manager.py stats
```

### View recent card reads:
```bash
sudo db_manager.py recent --limit 50
```

### View pending syncs:
```bash
sudo db_manager.py pending
```

### Force retry of failed syncs:
```bash
sudo db_manager.py retry
```

### Clean up old successful records:
```bash
sudo db_manager.py cleanup --days 30
```

### Export data to CSV:
```bash
sudo db_manager.py export /tmp/rfid_data.csv
```

## Troubleshooting

### Service won't start

1. Check if SPI is enabled:
   ```bash
   grep spi /boot/config.txt
   ```

2. Check if SPI module is loaded:
   ```bash
   lsmod | grep spi
   ```

3. View service logs:
   ```bash
   sudo journalctl -u rfid-reader -n 50
   ```

### RFID cards not being read

1. Verify wiring connections
2. Check if the RC522 module is properly powered
3. Ensure RFID cards are compatible with RC522
4. Check GPIO pin configuration in config file

### Webhook not receiving data

1. Verify webhook URL is correct and accessible
2. Check network connectivity
3. View application logs for webhook errors:
   ```bash
   sudo tail -f /var/log/rfid_reader.log
   ```

## Development

### Running in development mode

1. Install dependencies:
   ```bash
   pip3 install -r requirements.txt
   ```

2. Create a local config file:
   ```bash
   cp config.toml local_config.toml
   # Edit local_config.toml with your settings
   ```

3. Run the script directly:
   ```bash
   python3 rfid_reader.py
   ```

### Testing without hardware

You can test the webhook functionality by modifying the `read_card()` method to return a test card ID:

```python
def read_card(self) -> Optional[str]:
    # For testing without hardware
    time.sleep(5)  # Simulate card reading delay
    return "test_card_123"
```

### Testing with API key authentication

To test the webhook server with API key authentication:

```bash
# Start test server with API key
python3 test_webhook_server.py --api-key "your_test_api_key"

# In another terminal, test with curl
curl -X POST http://localhost:8080 \
  -H "Content-Type: application/json" \
  -H "x-api-key: your_test_api_key" \
  -d '{"device_id":"test123","value":"card456"}'
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly on Raspberry Pi
5. Submit a pull request

## Support

For issues and questions:
1. Check the troubleshooting section above
2. View the logs for error messages
3. Create an issue in the repository
