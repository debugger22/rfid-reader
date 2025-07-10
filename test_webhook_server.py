#!/usr/bin/env python3
"""
Simple webhook test server for RFID reader testing
This server receives webhook requests from the RFID reader and logs them
"""

import json
import logging
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class WebhookHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, expected_api_key=None, **kwargs):
        self.expected_api_key = expected_api_key
        super().__init__(*args, **kwargs)
    
    def do_POST(self):
        """Handle POST requests from RFID reader"""
        try:
            # Check API key if expected
            if self.expected_api_key:
                auth_header = self.headers.get('x-api-key', '')
                if not auth_header:
                    logger.warning(f"Missing or invalid x-api-key header: {auth_header}")
                    self.send_response(401)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    error_response = {
                        'status': 'error',
                        'message': 'Missing or invalid x-api-key header'
                    }
                    self.wfile.write(json.dumps(error_response).encode())
                    return
                
                provided_api_key = auth_header
                if provided_api_key != self.expected_api_key:
                    logger.warning(f"Invalid API key provided: {provided_api_key[:8]}...")
                    self.send_response(401)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    error_response = {
                        'status': 'error',
                        'message': 'Invalid API key'
                    }
                    self.wfile.write(json.dumps(error_response).encode())
                    return
                
                logger.info("API key authentication successful")
            
            # Get content length
            content_length = int(self.headers.get('Content-Length', 0))
            
            # Read request body
            post_data = self.rfile.read(content_length)
            
            # Parse JSON
            data = json.loads(post_data.decode('utf-8'))
            
            # Log the received data
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            logger.info(f"Received webhook at {timestamp}:")
            logger.info(f"  Device ID: {data.get('device_id', 'Unknown')}")
            logger.info(f"  Card Value: {data.get('value', 'Unknown')}")
            logger.info(f"  Remote Address: {self.client_address[0]}")
            
            # Send response
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            response = {
                'status': 'success',
                'message': 'Webhook received successfully',
                'timestamp': timestamp
            }
            
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            logger.error(f"Error processing webhook: {e}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            error_response = {
                'status': 'error',
                'message': str(e)
            }
            
            self.wfile.write(json.dumps(error_response).encode())
    
    def do_GET(self):
        """Handle GET requests (health check)"""
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'RFID Webhook Test Server is running')
    
    def log_message(self, format, *args):
        """Override to use our logger"""
        logger.info(f"{self.address_string()} - {format % args}")

def run_server(port=8080, expected_api_key=None):
    """Run the webhook test server"""
    server_address = ('', port)
    
    # Create a custom handler class with the expected API key
    class CustomWebhookHandler(WebhookHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, expected_api_key=expected_api_key, **kwargs)
    
    httpd = HTTPServer(server_address, CustomWebhookHandler)
    
    logger.info(f"Starting webhook test server on port {port}")
    logger.info(f"Server will receive POST requests at http://localhost:{port}")
    if expected_api_key:
        logger.info(f"API key authentication enabled: {expected_api_key[:8]}...")
    else:
        logger.info("API key authentication disabled")
    logger.info("Press Ctrl+C to stop the server")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down webhook test server...")
        httpd.server_close()

if __name__ == "__main__":
    import sys
    
    port = 8080
    expected_api_key = None
    
    # Parse command line arguments
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == '--port' and i + 1 < len(sys.argv):
            try:
                port = int(sys.argv[i + 1])
                i += 2
            except ValueError:
                logger.error("Invalid port number")
                sys.exit(1)
        elif sys.argv[i] == '--api-key' and i + 1 < len(sys.argv):
            expected_api_key = sys.argv[i + 1]
            i += 2
        else:
            i += 1
    
    run_server(port, expected_api_key) 