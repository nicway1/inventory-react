from utils.firecrawl_client import FirecrawlClient
import os
import sys
import logging

# Set up logging for this module
logger = logging.getLogger(__name__)


# Set up logging
logging.basicConfig(level=logging.DEBUG)
logging.getLogger('urllib3').setLevel(logging.DEBUG)

# Check if we have an API key
api_key = os.environ.get('FIRECRAWL_API_KEY')
if not api_key:
    logger.info("Warning: FIRECRAWL_API_KEY environment variable not set")
    
# Get tracking number from command line or use default
tracking_number = sys.argv[1] if len(sys.argv) > 1 else "XZD0002556450"

logger.info("Testing FirecrawlClient with tracking number: {tracking_number}")

# Create client
client = FirecrawlClient()

# Debug output the constructed URL
logger.info("Base URL: {client.base_url}")
logger.info("Endpoint: {client.base_url}/scrape")

# Test tracking info retrieval
try:
    logger.info("Calling scrape_ship24...")
    result = client.scrape_ship24(tracking_number)
    logger.info("Result: {result}")
except Exception as e:
    logger.info("Error: {str(e)}")
    import traceback
    traceback.print_exc() 