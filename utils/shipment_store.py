from datetime import datetime
from utils.db_manager import DatabaseManager

class ShipmentStore:
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.shipments = {}
        self.load_shipments()
    
    def load_shipments(self):
        """Load shipments from the database"""
        # This is a placeholder - in the future, we'll load from the database
        self.shipments = {}
    
    def get_user_shipments(self, user_id):
        """Get all shipments for a specific user"""
        return [shipment for shipment in self.shipments.values() 
                if shipment.get('user_id') == user_id]
    
    def add_shipment(self, user_id, tracking_number, description=None):
        """Add a new shipment"""
        shipment_id = len(self.shipments) + 1
        shipment = {
            'id': shipment_id,
            'user_id': user_id,
            'tracking_number': tracking_number,
            'description': description,
            'status': 'Pending',
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        self.shipments[shipment_id] = shipment
        return shipment
    
    def update_shipment(self, shipment_id, status):
        """Update shipment status"""
        if shipment_id in self.shipments:
            self.shipments[shipment_id]['status'] = status
            self.shipments[shipment_id]['updated_at'] = datetime.utcnow()
            return True
        return False
    
    def get_shipment(self, shipment_id):
        """Get a specific shipment"""
        return self.shipments.get(shipment_id)

# Create singleton instance
shipment_store = ShipmentStore() 