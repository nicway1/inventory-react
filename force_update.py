import requests

# Ticket ID to update
ticket_id = 3

# The URL to call the track_claw endpoint with force_refresh=true
url = f"http://localhost:5010/tickets/{ticket_id}/track_claw?force_refresh=true"

# Make the request
try:
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        print("Successfully updated tracking information:")
        print(f"Status: {data.get('shipping_status')}")
        if data.get('tracking_info'):
            print("\nTracking events:")
            for event in data.get('tracking_info', []):
                print(f"- {event.get('date')}: {event.get('status')} at {event.get('location')}")
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
except Exception as e:
    print(f"Error calling API: {str(e)}") 