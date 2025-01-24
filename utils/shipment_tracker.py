from datetime import datetime

class ShipmentTracker:
    def __init__(self):
        pass

    def get_tracking_info(self, tracking_number):
        # Return basic info since we'll use the embedded widget
        return {
            'status': 'Click to view tracking details',
            'tracking_number': tracking_number,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'details': []
        }

    def format_tracking_url(self, tracking_number):
        """Generate a direct link to 17track website"""
        return f"https://t.17track.net/en#nums={tracking_number}" 