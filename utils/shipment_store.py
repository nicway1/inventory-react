from models.shipment import Shipment
from datetime import datetime

class ShipmentStore:
    def __init__(self):
        self.shipments = {}

    def create_shipment(self, user_id, tracking_number, description=None):
        shipment = Shipment.create(
            user_id=user_id,
            tracking_number=tracking_number,
            description=description
        )
        self.shipments[shipment.id] = shipment
        return shipment

    def get_shipment(self, shipment_id):
        return self.shipments.get(shipment_id)

    def get_user_shipments(self, user_id):
        return [s for s in self.shipments.values() if s.user_id == user_id]

    def update_tracking(self, shipment_id, tracking_info):
        shipment = self.shipments.get(shipment_id)
        if shipment and tracking_info:
            shipment.status = tracking_info.get('status', 'Unknown')
            shipment.last_tracked = datetime.now()
            shipment.tracking_history.append({
                'timestamp': datetime.now(),
                'status': tracking_info.get('status'),
                'details': tracking_info.get('details', [])
            })
        return shipment 

# Create singleton instance
shipment_store = ShipmentStore() 