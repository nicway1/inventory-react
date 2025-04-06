import sys
import time

# Force direct API key
API_KEY = "7yyp17vj-t0bh-jtg0-xjf0-v9m3335cjbtc"
print(f"Using API Key: {API_KEY}")

# Try to import trackingmore
try:
    import trackingmore
    print(f"Successfully imported trackingmore v0.2")
    
    # Set API key
    print("Setting API key...")
    trackingmore.set_api_key(API_KEY)
    print("API key set successfully")
    
    # Print available methods
    print(f"Available methods: {[m for m in dir(trackingmore) if not m.startswith('_')]}")
except ImportError as e:
    print(f"Error importing trackingmore: {str(e)}")
    sys.exit(1)
except Exception as e:
    print(f"Error initializing TrackingMore: {str(e)}")
    sys.exit(1)

# Test tracking number - using the user's specific tracking number
TRACKING_NUMBER = "XZD0002657586"  # User's tracking number

# First test carrier detection
try:
    print("\nTesting carrier detection...")
    carrier = trackingmore.detect_carrier_from_code(TRACKING_NUMBER)
    print(f"Detected carrier: {carrier}")
except Exception as e:
    print(f"Carrier detection error: {str(e)}")

# Try available Singapore Post carrier codes
carrier_codes = ['singapore-post', 'singpost', 'singapore-speedpost']

for code in carrier_codes:
    print(f"\n\nTrying carrier code: {code}")
    try:
        print(f"\nTesting create_tracking_item with {code}...")
        create_params = {
            'tracking_number': TRACKING_NUMBER,
            'carrier_code': code
        }
        print(f"Params: {create_params}")
        result = trackingmore.create_tracking_item(create_params)
        print(f"Result: {result}")
        
        # Wait a moment
        print("Waiting 2 seconds...")
        time.sleep(2)
        
        print(f"\nTesting realtime_tracking with {code}...")
        realtime_params = {
            'tracking_number': TRACKING_NUMBER,
            'carrier_code': code
        }
        tracking_result = trackingmore.realtime_tracking(realtime_params)
        print(f"Result: {tracking_result}")
        
        if tracking_result and 'items' in tracking_result and tracking_result['items']:
            print("Success with carrier code:", code)
            break
            
    except Exception as e:
        print(f"\nERROR with {code}: {str(e)}")
        print(f"Error type: {type(e)}")
        print(f"Error args: {e.args}")

# Also try get_tracking_item
try:
    print("\n\nTesting get_tracking_item...")
    get_result = trackingmore.get_tracking_item(TRACKING_NUMBER, carrier_codes[0])
    print(f"Get tracking item result: {get_result}")
except Exception as e:
    print(f"\nERROR with get_tracking_item: {str(e)}")
    print(f"Error type: {type(e)}")
    print(f"Error args: {e.args}") 