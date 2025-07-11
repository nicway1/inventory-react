import sys
import time
import logging

# Set up logging for this module
logger = logging.getLogger(__name__)


# Force direct API key
API_KEY = "7yyp17vj-t0bh-jtg0-xjf0-v9m3335cjbtc"
logger.info("Using API Key: {API_KEY}")

# Try to import trackingmore
try:
    import trackingmore
    logger.info("Successfully imported trackingmore v0.2")
    
    # Set API key
    logger.info("Setting API key...")
    trackingmore.set_api_key(API_KEY)
    logger.info("API key set successfully")
    
    # Print available methods
    logger.info("Available methods: {[m for m in dir(trackingmore) if not m.startswith('_')]}")
except ImportError as e:
    logger.info("Error importing trackingmore: {str(e)}")
    sys.exit(1)
except Exception as e:
    logger.info("Error initializing TrackingMore: {str(e)}")
    sys.exit(1)

# Test tracking number - using the user's specific tracking number
TRACKING_NUMBER = "XZD0002657586"  # User's tracking number

# First test carrier detection
try:
    logger.info("\nTesting carrier detection...")
    carrier = trackingmore.detect_carrier_from_code(TRACKING_NUMBER)
    logger.info("Detected carrier: {carrier}")
except Exception as e:
    logger.info("Carrier detection error: {str(e)}")

# Try available Singapore Post carrier codes
carrier_codes = ['singapore-post', 'singpost', 'singapore-speedpost']

for code in carrier_codes:
    logger.info("\n\nTrying carrier code: {code}")
    try:
        logger.info("\nTesting create_tracking_item with {code}...")
        create_params = {
            'tracking_number': TRACKING_NUMBER,
            'carrier_code': code
        }
        logger.info("Params: {create_params}")
        result = trackingmore.create_tracking_item(create_params)
        logger.info("Result: {result}")
        
        # Wait a moment
        logger.info("Waiting 2 seconds...")
        time.sleep(2)
        
        logger.info("\nTesting realtime_tracking with {code}...")
        realtime_params = {
            'tracking_number': TRACKING_NUMBER,
            'carrier_code': code
        }
        tracking_result = trackingmore.realtime_tracking(realtime_params)
        logger.info("Result: {tracking_result}")
        
        if tracking_result and 'items' in tracking_result and tracking_result['items']:
            logger.info("Success with carrier code:", code)
            break
            
    except Exception as e:
        logger.info("\nERROR with {code}: {str(e)}")
        logger.info("Error type: {type(e)}")
        logger.info("Error args: {e.args}")

# Also try get_tracking_item
try:
    logger.info("\n\nTesting get_tracking_item...")
    get_result = trackingmore.get_tracking_item(TRACKING_NUMBER, carrier_codes[0])
    logger.info("Get tracking item result: {get_result}")
except Exception as e:
    logger.info("\nERROR with get_tracking_item: {str(e)}")
    logger.info("Error type: {type(e)}")
    logger.info("Error args: {e.args}") 