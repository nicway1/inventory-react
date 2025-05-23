from utils.firecrawl_client import FirecrawlClient
import os
import sys
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logging.getLogger('urllib3').setLevel(logging.DEBUG)

# Check if we have an API key
api_key = os.environ.get('FIRECRAWL_API_KEY')
if not api_key:
    print("Warning: FIRECRAWL_API_KEY environment variable not set")
    
# Get tracking number from command line or use default
tracking_number = sys.argv[1] if len(sys.argv) > 1 else "XZD0002556450"

print(f"Testing FirecrawlClient with tracking number: {tracking_number}")

# Create client
client = FirecrawlClient()

# Debug output the constructed URL
print(f"Base URL: {client.base_url}")
print(f"Endpoint: {client.base_url}/scrape")

# Test tracking info retrieval
try:
    print("Calling scrape_ship24...")
    result = client.scrape_ship24(tracking_number)
    print(f"Result: {result}")
except Exception as e:
    print(f"Error: {str(e)}")
    import traceback
    traceback.print_exc() 