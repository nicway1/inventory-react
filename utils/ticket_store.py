import json
import os
from datetime import datetime
from models.ticket import Ticket
from models.shipment import Shipment

class TicketStore:
    def __init__(self):
        self.tickets = {}
        self.TICKETS_FILE = 'data/tickets.json'
        self.load_tickets()

    def load_tickets(self):
        """Load tickets from JSON file"""
        if os.path.exists(self.TICKETS_FILE):
            with open(self.TICKETS_FILE, 'r') as f:
                tickets_data = json.load(f)
                for ticket_data in tickets_data:
                    ticket = Ticket(
                        id=ticket_data['id'],
                        subject=ticket_data['subject'],
                        description=ticket_data['description'],
                        requester_id=ticket_data['requester_id'],
                        status=ticket_data['status'],
                        priority=ticket_data['priority'],
                        category=ticket_data['category'],
                        created_at=datetime.fromisoformat(ticket_data['created_at']),
                        updated_at=datetime.fromisoformat(ticket_data['updated_at'])
                    )
                    
                    # Restore additional fields
                    ticket.assigned_to_id = ticket_data.get('assigned_to_id')
                    ticket.queue_id = ticket_data.get('queue_id')
                    ticket.asset_id = ticket_data.get('asset_id')
                    ticket.accessory_id = ticket_data.get('accessory_id')

                    # Restore shipment if exists
                    if ticket_data.get('shipment'):
                        ticket.shipment = Shipment.from_dict(ticket_data['shipment'])

                    ticket.rma_status = ticket_data.get('rma_status')
                    ticket.warranty_number = ticket_data.get('warranty_number')
                    ticket.serial_number = ticket_data.get('serial_number')
                    
                    if ticket_data.get('return_tracking'):
                        ticket.return_tracking = Shipment.from_dict(ticket_data['return_tracking'])
                    if ticket_data.get('replacement_tracking'):
                        ticket.replacement_tracking = Shipment.from_dict(ticket_data['replacement_tracking'])

                    self.tickets[ticket.id] = ticket

    def save_tickets(self):
        """Save tickets to JSON file"""
        os.makedirs(os.path.dirname(self.TICKETS_FILE), exist_ok=True)
        tickets_data = []
        for ticket in self.tickets.values():
            ticket_data = {
                'id': ticket.id,
                'subject': ticket.subject,
                'description': ticket.description,
                'requester_id': ticket.requester_id,
                'status': ticket.status,
                'priority': ticket.priority,
                'category': ticket.category,
                'created_at': ticket.created_at.isoformat(),
                'updated_at': ticket.updated_at.isoformat(),
                'assigned_to_id': ticket.assigned_to_id,
                'queue_id': ticket.queue_id,
                'asset_id': ticket.asset_id,
                'accessory_id': ticket.accessory_id,
                'shipment': ticket.shipment.to_dict() if ticket.shipment else None,
                'rma_status': ticket.rma_status,
                'warranty_number': ticket.warranty_number,
                'serial_number': ticket.serial_number,
                'return_tracking': ticket.return_tracking.to_dict() if ticket.return_tracking else None,
                'replacement_tracking': ticket.replacement_tracking.to_dict() if ticket.replacement_tracking else None
            }
            tickets_data.append(ticket_data)

        with open(self.TICKETS_FILE, 'w') as f:
            json.dump(tickets_data, f, indent=2)

    def create_ticket(self, subject, description, requester_id, priority, category, queue_id=None):
        """Create a new ticket"""
        ticket = Ticket.create(subject, description, requester_id, priority, category, queue_id)
        self.tickets[ticket.id] = ticket
        self.save_tickets()  # Save immediately after creating
        return ticket

    def get_ticket(self, ticket_id):
        """Get a ticket by ID"""
        return self.tickets.get(ticket_id)

    def get_user_tickets(self, user_id, user_type):
        """Get tickets for a user"""
        if user_type == 'admin':
            return list(self.tickets.values())
        return [
            ticket for ticket in self.tickets.values()
            if ticket.requester_id == user_id
        ]

    def assign_ticket(self, ticket_id, assigned_to_id, queue_id):
        """Assign a ticket to a user and/or queue"""
        ticket = self.tickets.get(ticket_id)
        if ticket:
            if assigned_to_id is not None:
                ticket.assigned_to_id = assigned_to_id
            if queue_id is not None:
                ticket.queue_id = queue_id
            ticket.updated_at = datetime.now()
            self.save_tickets()  # Save after updating
        return ticket 

    def save_template(self, template):
        """Save a ticket template"""
        if not hasattr(self, 'templates'):
            self.templates = []
        
        # Generate template ID if new
        if 'id' not in template:
            template['id'] = str(len(self.templates) + 1)
            self.templates.append(template)
        else:
            # Update existing template
            for i, t in enumerate(self.templates):
                if t['id'] == template['id']:
                    self.templates[i] = template
                    break
        
        # Save templates to file
        self._save_templates()

    def get_templates(self):
        """Get all saved templates"""
        if not hasattr(self, 'templates'):
            self._load_templates()
        return self.templates

    def _save_templates(self):
        """Save templates to JSON file"""
        templates_file = os.path.join(os.path.dirname(self.TICKETS_FILE), 'templates.json')
        with open(templates_file, 'w') as f:
            json.dump(self.templates, f, indent=2)

    def _load_templates(self):
        """Load templates from JSON file"""
        self.templates = []
        templates_file = os.path.join(os.path.dirname(self.TICKETS_FILE), 'templates.json')
        if os.path.exists(templates_file):
            with open(templates_file, 'r') as f:
                self.templates = json.load(f) 

    def delete_template(self, template_id):
        """Delete a template by ID"""
        if not hasattr(self, 'templates'):
            self._load_templates()
        
        self.templates = [t for t in self.templates if t['id'] != template_id]
        self._save_templates() 

    def get_asset_tickets(self, asset_id):
        """Get all tickets related to a specific asset"""
        try:
            # Convert asset_id to string for comparison
            asset_id = str(asset_id)
            
            # Filter tickets where asset_id matches
            asset_tickets = [
                ticket for ticket in self.tickets.values()
                if str(ticket.asset_id) == asset_id
            ]
            
            print(f"Found {len(asset_tickets)} tickets for asset {asset_id}")  # Debug print
            return asset_tickets
            
        except Exception as e:
            print(f"Error getting asset tickets: {str(e)}")
            return [] 