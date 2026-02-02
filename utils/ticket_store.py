import json
import os
from datetime import datetime
from models.ticket import Ticket, TicketPriority
from models.shipment import Shipment
from models.user import UserType
from utils.db_manager import DatabaseManager
import logging
import time

# Set up logging for this module
logger = logging.getLogger(__name__)

# Simple in-memory cache for ticket queries
_ticket_cache = {}
_cache_ttl = 30  # Cache TTL in seconds


def _get_cache_key(user_id, user_type):
    """Generate cache key for ticket queries"""
    return f"tickets_{user_id}_{user_type.value if hasattr(user_type, 'value') else user_type}"


def _is_cache_valid(cache_entry):
    """Check if cache entry is still valid"""
    if not cache_entry:
        return False
    return (time.time() - cache_entry['timestamp']) < _cache_ttl


def clear_ticket_cache(user_id=None):
    """Clear ticket cache. If user_id provided, clear only that user's cache."""
    global _ticket_cache
    if user_id:
        keys_to_delete = [k for k in _ticket_cache if k.startswith(f"tickets_{user_id}_")]
        for key in keys_to_delete:
            del _ticket_cache[key]
        logger.debug(f"Cleared ticket cache for user {user_id}")
    else:
        _ticket_cache = {}
        logger.debug("Cleared all ticket cache")


class TicketStore:
    def __init__(self):
        self.tickets = {}
        self.TICKETS_FILE = 'data/tickets.json'
        self.db_manager = DatabaseManager()
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
                    
                    # Load shipping information
                    ticket.shipping_tracking = ticket_data.get('shipping_tracking')
                    ticket.shipping_address = ticket_data.get('shipping_address')
                    ticket.shipping_status = ticket_data.get('shipping_status')
                    ticket.shipping_history = ticket_data.get('shipping_history', [])
                    ticket.shipping_carrier = ticket_data.get('shipping_carrier', 'singpost')
                    ticket.customer_id = ticket_data.get('customer_id')

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
                'replacement_tracking': ticket.replacement_tracking.to_dict() if ticket.replacement_tracking else None,
                'shipping_tracking': ticket.shipping_tracking,
                'shipping_address': ticket.shipping_address,
                'shipping_status': ticket.shipping_status,
                'shipping_history': getattr(ticket, 'shipping_history', []),
                'shipping_carrier': getattr(ticket, 'shipping_carrier', 'singpost'),
                'customer_id': ticket.customer_id
            }
            tickets_data.append(ticket_data)

        with open(self.TICKETS_FILE, 'w') as f:
            json.dump(tickets_data, f, indent=2)

    def create_ticket(self, subject, description, requester_id, category=None, priority='Medium', 
                     asset_id=None, country=None, damage_description=None, apple_diagnostics=None, 
                     image_path=None, repair_status=None, customer_id=None, shipping_address=None,
                     shipping_tracking=None, shipping_carrier='singpost', return_tracking=None, queue_id=None, notes=None, return_description=None, case_owner_id=None):
        """Create a new ticket"""
        db_session = self.db_manager.get_session()
        try:
            # Convert priority to enum if it's not already
            if isinstance(priority, str):
                # Handle empty string or None priority by setting default
                if not priority or priority.strip() == "":
                    priority = TicketPriority.MEDIUM  # Default to MEDIUM
                else:
                    try:
                        # First try to get enum by name (e.g., 'LOW')
                        priority = TicketPriority[priority]
                    except KeyError:
                        try:
                            # If that fails, try to get enum by value (e.g., 'Low')
                            priority = TicketPriority(priority)
                        except ValueError:
                            # If both fail, use default
                            logger.info("Warning: Invalid priority '{priority}', using default MEDIUM")
                            priority = TicketPriority.MEDIUM
                
            # Determine case owner - use case_owner_id if provided, otherwise default to requester
            assigned_to_id = case_owner_id if case_owner_id else requester_id
            
            ticket = Ticket(
                subject=subject,
                description=description,
                requester_id=requester_id,
                assigned_to_id=assigned_to_id,  # Use selected case owner or default to requester
                category=category,
                priority=priority,
                asset_id=asset_id,
                country=country,
                damage_description=damage_description,
                apple_diagnostics=apple_diagnostics,
                image_path=image_path,
                repair_status=repair_status,
                customer_id=customer_id,
                shipping_address=shipping_address,
                shipping_tracking=shipping_tracking,
                shipping_carrier=shipping_carrier,
                return_tracking=return_tracking,
                queue_id=queue_id,
                notes=notes,
                return_description=return_description
            )
            db_session.add(ticket)
            db_session.flush()  # Flush to get the ticket ID
            
            # Temporarily disable automatic asset assignment to prevent duplicates
            # Asset assignment will be handled manually in the route
            if asset_id:
                logger.info("Skipping automatic asset assignment for asset {asset_id} - will be handled manually")
            
            db_session.commit()

            # Clear ticket cache since a new ticket was created
            clear_ticket_cache()

            # Send queue notifications if ticket was created in a queue
            if queue_id:
                try:
                    from utils.queue_notification_sender import send_queue_notifications
                    send_queue_notifications(ticket, action_type="created")
                except Exception as e:
                    logger.error(f"Error sending queue notifications: {str(e)}")

            return ticket.id  # Return the ID instead of the ticket object
        finally:
            db_session.close()

    def get_ticket(self, ticket_id):
        """Get a specific ticket by ID"""
        db_session = self.db_manager.get_session()
        try:
            return db_session.query(Ticket).get(ticket_id)
        finally:
            db_session.close()

    def get_all_tickets(self):
        """Get all tickets from the database"""
        db_session = self.db_manager.get_session()
        try:
            return db_session.query(Ticket).order_by(Ticket.created_at.desc()).all()
        finally:
            db_session.close()

    def get_ticket_by_id(self, ticket_id):
        """Get a specific ticket by ID (alias for get_ticket)"""
        return self.get_ticket(ticket_id)

    def get_user_tickets(self, user_id, user_type, use_cache=True):
        """Get tickets based on user's role and ID

        Args:
            user_id: The user ID
            user_type: The user's type (UserType enum)
            use_cache: Whether to use cached results (default True)
        """
        global _ticket_cache

        # Check cache first
        cache_key = _get_cache_key(user_id, user_type)
        if use_cache and cache_key in _ticket_cache:
            cache_entry = _ticket_cache[cache_key]
            if _is_cache_valid(cache_entry):
                logger.debug(f"Cache HIT for {cache_key}")
                return cache_entry['data']
            else:
                # Cache expired, remove it
                del _ticket_cache[cache_key]

        logger.debug(f"Cache MISS for {cache_key}, querying database")
        start_time = time.time()

        db_session = self.db_manager.get_session()
        try:
            query = db_session.query(Ticket)\
                .options(self.db_manager.joinedload(Ticket.assigned_to))\
                .options(self.db_manager.joinedload(Ticket.requester))\
                .options(self.db_manager.joinedload(Ticket.queue))\
                .options(self.db_manager.joinedload(Ticket.customer))

            # Super admin and developer can see all tickets
            if user_type in [UserType.SUPER_ADMIN, UserType.DEVELOPER]:
                tickets = query.order_by(Ticket.created_at.desc()).all()
            # COUNTRY_ADMIN and SUPERVISOR can see all tickets
            # (queue permissions will filter which tickets they can actually access)
            elif user_type in [UserType.COUNTRY_ADMIN, UserType.SUPERVISOR]:
                tickets = query.order_by(Ticket.created_at.desc()).all()
            else:
                # CLIENT and regular users only see their own tickets
                tickets = query.filter(
                    (Ticket.requester_id == user_id) |
                    (Ticket.assigned_to_id == user_id)
                ).order_by(Ticket.created_at.desc()).all()

            # Eagerly access related data to ensure it's loaded before session closes
            for ticket in tickets:
                _ = ticket.assigned_to.username if ticket.assigned_to else None
                _ = ticket.requester.username if ticket.requester else None
                _ = ticket.queue.name if ticket.queue else None
                _ = ticket.customer.name if ticket.customer else None

            # Detach objects from session so they can be cached
            db_session.expunge_all()

            elapsed = time.time() - start_time
            logger.info(f"Ticket query took {elapsed:.2f}s, found {len(tickets)} tickets")

            # Store in cache
            if use_cache:
                _ticket_cache[cache_key] = {
                    'data': tickets,
                    'timestamp': time.time()
                }

            return tickets
        finally:
            db_session.close()

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
            # Clear ticket cache since a ticket was assigned
            clear_ticket_cache()
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
            
            logger.info("Found {len(asset_tickets)} tickets for asset {asset_id}")  # Debug print
            return asset_tickets
            
        except Exception as e:
            logger.info("Error getting asset tickets: {str(e)}")
            return [] 

    def update_ticket(self, ticket_id, **kwargs):
        """Update ticket details"""
        db_session = self.db_manager.get_session()
        try:
            ticket = db_session.query(Ticket).get(ticket_id)
            if ticket:
                for key, value in kwargs.items():
                    setattr(ticket, key, value)
                db_session.commit()
                # Clear ticket cache since a ticket was updated
                clear_ticket_cache()
            return ticket
        finally:
            db_session.close()

    def delete_ticket(self, ticket_id):
        """Delete a ticket"""
        db_session = self.db_manager.get_session()
        try:
            ticket = db_session.query(Ticket).get(ticket_id)
            if ticket:
                db_session.delete(ticket)
                db_session.commit()
                # Clear ticket cache since a ticket was deleted
                clear_ticket_cache()
                return True
            return False
        finally:
            db_session.close()

    def get_tickets_by_queue(self, queue_id):
        """Get all tickets in a specific queue"""
        db_session = self.db_manager.get_session()
        try:
            tickets = db_session.query(Ticket).filter(Ticket.queue_id == queue_id).order_by(Ticket.created_at.desc()).all()
            return tickets
        finally:
            db_session.close()

    def clear_all_tickets(self):
        """Clear all tickets from both database and JSON storage"""
        # Clear from database
        db_session = self.db_manager.get_session()
        try:
            db_session.query(Ticket).delete()
            db_session.commit()
        finally:
            db_session.close()

        # Clear from JSON storage
        self.tickets = {}
        if os.path.exists(self.TICKETS_FILE):
            os.remove(self.TICKETS_FILE)
        else:
            # Ensure the directory exists and create an empty tickets file
            os.makedirs(os.path.dirname(self.TICKETS_FILE), exist_ok=True)
            with open(self.TICKETS_FILE, 'w') as f:
                json.dump([], f) 

    def _safely_assign_asset_to_ticket(self, ticket, asset, db_session):
        """
        Safely assign an asset to a ticket, checking for existing relationships first
        
        Args:
            ticket: Ticket object
            asset: Asset object
            db_session: Database session
            
        Returns:
            bool: True if assignment was successful or already exists, False otherwise
        """
        try:
            # Check if asset is already assigned to this ticket
            if asset in ticket.assets:
                logger.info("Asset {asset.id} ({asset.asset_tag}) already assigned to ticket {ticket.id}")
                return True
            
            # Check if the relationship already exists in the database
            from sqlalchemy import text
            stmt = text("""
                SELECT COUNT(*) FROM ticket_assets 
                WHERE ticket_id = :ticket_id AND asset_id = :asset_id
            """)
            result = db_session.execute(stmt, {"ticket_id": ticket.id, "asset_id": asset.id})
            count = result.scalar()
            
            if count > 0:
                logger.info("Asset {asset.id} already linked to ticket {ticket.id} in database")
                return True
            
            # Safe to assign - add the asset to the ticket
            ticket.assets.append(asset)
            logger.info("Successfully assigned asset {asset.id} ({asset.asset_tag}) to ticket {ticket.id}")
            return True
            
        except Exception as e:
            logger.info("Error assigning asset to ticket: {str(e)}")
            return False 