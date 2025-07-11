import requests
import logging

# Set up logging for this module
logger = logging.getLogger(__name__)


# Ticket ID to update
ticket_id = 3

# The URL to call the track_claw endpoint with force_refresh=true
url = f"http://localhost:5010/tickets/{ticket_id}/track_claw?force_refresh=true"

# Make the request
try:
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        logger.info("Successfully updated tracking information:")
        logger.info("Status: {data.get('shipping_status')}")
        if data.get('tracking_info'):
            logger.info("\nTracking events:")
            for event in data.get('tracking_info', []):
                logger.info("- {event.get('date')}: {event.get('status')} at {event.get('location')}")
    else:
        logger.info("Error: {response.status_code}")
        logger.info(response.text)
except Exception as e:
    logger.info("Error calling API: {str(e)}") 