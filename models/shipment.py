from datetime import datetime

class Shipment:
    def __init__(self, tracking_number, description=None, status='Pending', tracking_history=None, created_at=None):
        self.tracking_number = tracking_number
        self.description = description or ''
        self.status = status
        self.tracking_history = tracking_history or []
        self.created_at = created_at or datetime.now()
        self.last_update = None
        self.current_location = None

    def update_tracking(self, status, details=None):
        """Update tracking status and history from 17track"""
        self.status = status
        self.last_update = datetime.now()
        
        if isinstance(details, dict):
            # Handle 17track format
            event = {
                'status': status,
                'details': details.get('message', ''),
                'location': details.get('location', ''),
                'timestamp': details.get('time', datetime.now().isoformat())
            }
            self.tracking_history.append(event)
            self.current_location = details.get('location')
        elif details:
            # Handle other formats
            self.tracking_history.append({
                'status': status,
                'details': details,
                'timestamp': datetime.now().isoformat()
            })

    @staticmethod
    def from_dict(data):
        """Create a Shipment instance from a dictionary"""
        return Shipment(
            tracking_number=data['tracking_number'],
            description=data.get('description', ''),
            status=data.get('status', 'Pending'),
            tracking_history=data.get('tracking_history', []),
            created_at=datetime.fromisoformat(data['created_at']) if 'created_at' in data else None
        )

    def to_dict(self):
        """Convert shipment to dictionary for JSON serialization"""
        return {
            'tracking_number': self.tracking_number,
            'description': self.description,
            'status': self.status,
            'tracking_history': self.tracking_history,
            'created_at': self.created_at.isoformat(),
            'last_update': self.last_update.isoformat() if self.last_update else None,
            'current_location': self.current_location
        } 