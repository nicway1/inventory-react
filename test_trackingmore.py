import trackingmore
import sys
import time

# Force direct API key
API_KEY = "7yyp17vj-t0bh-jtg0-xjf0-v9m3335cjbtc"
print(f"Using API Key: {API_KEY}")

# Print debugging info
print(f"TrackingMore module info: {trackingmore}")
print(f"Available methods: {dir(trackingmore)}")

# Set API key
print("Setting API key...")
trackingmore.set_api_key(API_KEY)

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
        
        print(f"\nTesting get_tracking_item with {code}...")
        tracking_result = trackingmore.get_tracking_item(TRACKING_NUMBER, code)
        print(f"Result: {tracking_result}")
        
        if tracking_result:
            print("Success with carrier code:", code)
            break
            
    except Exception as e:
        print(f"\nERROR with {code}: {str(e)}")
        print(f"Error type: {type(e)}")
        print(f"Error args: {e.args}")

# Also try the realtime_tracking method
try:
    print("\n\nTesting realtime_tracking...")
    realtime_params = {
        'tracking_number': TRACKING_NUMBER,
        'carrier_code': 'singapore-post'
    }
    realtime_result = trackingmore.realtime_tracking(realtime_params)
    print(f"Realtime tracking result: {realtime_result}")
except Exception as e:
    print(f"\nERROR with realtime tracking: {str(e)}")
    print(f"Error type: {type(e)}")
    print(f"Error args: {e.args}") 