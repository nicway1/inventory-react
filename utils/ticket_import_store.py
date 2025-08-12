from utils.db_manager import DatabaseManager
from models.ticket import Ticket, TicketCategory, TicketStatus
from models.queue import Queue
from models.customer_user import CustomerUser
from models.company import Company
from models.enums import Country
import pandas as pd
import csv
import io
from datetime import datetime
import os
import logging
import uuid

# Set up logging for this module
logger = logging.getLogger(__name__)


class TicketImportStore:
    def __init__(self):
        self.db_manager = DatabaseManager()
    
    def map_country_code(self, country_code):
        """Map country code to Country enum value"""
        if not country_code:
            return Country.USA  # Default to USA if no country provided
        
        country_code = country_code.strip().upper()
        
        # Direct mapping for country codes
        country_mapping = {
            'US': Country.USA,
            'USA': Country.USA,
            'JP': Country.JAPAN,
            'JAPAN': Country.JAPAN,
            'PH': Country.PHILIPPINES,
            'PHILIPPINES': Country.PHILIPPINES,
            'AU': Country.AUSTRALIA,
            'AUSTRALIA': Country.AUSTRALIA,
            'IL': Country.ISRAEL,
            'ISRAEL': Country.ISRAEL,
            'IN': Country.INDIA,
            'INDIA': Country.INDIA,
            'TW': Country.TAIWAN,
            'TAIWAN': Country.TAIWAN,
            'CN': Country.CHINA,
            'CHINA': Country.CHINA,
            'HK': Country.HONG_KONG,
            'HONG_KONG': Country.HONG_KONG,
            'MY': Country.MALAYSIA,
            'MALAYSIA': Country.MALAYSIA,
            'TH': Country.THAILAND,
            'THAILAND': Country.THAILAND,
            'VN': Country.VIETNAM,
            'VIETNAM': Country.VIETNAM,
            'KR': Country.SOUTH_KOREA,
            'SOUTH_KOREA': Country.SOUTH_KOREA,
            'ID': Country.INDONESIA,
            'INDONESIA': Country.INDONESIA,
            'CA': Country.CANADA,
            'CANADA': Country.CANADA,
            'SG': Country.SINGAPORE,
            'SINGAPORE': Country.SINGAPORE
        }
        
        return country_mapping.get(country_code, Country.USA)  # Default to USA if not found

    def clean_csv_row(self, row):
        """Clean and validate a CSV row - copied from admin.py"""
        try:
            # Required fields for validation
            required_fields = ['product_title', 'org_name']
            
            # Clean whitespace and handle quoted empty values
            cleaned = {}
            for key, value in row.items():
                if value is None:
                    cleaned[key] = ''
                else:
                    # Strip whitespace and handle quoted spaces like " "
                    cleaned_value = str(value).strip()
                    if cleaned_value in ['" "', "'  '", '""', "''"]:
                        cleaned_value = ''
                    cleaned[key] = cleaned_value
            
            # Check if required fields are present and non-empty
            for field in required_fields:
                if not cleaned.get(field):
                    logger.info(f"Skipping row due to missing required field '{field}'. Row data: {cleaned}")
                    return None
            
            logger.info(f"Row passed validation with required fields: {[field + '=' + str(cleaned.get(field)) for field in required_fields]}")
            
            # Set default values for missing fields
            defaults = {
                'person_name': cleaned.get('person_name') or 'Unknown Customer',
                'primary_email': cleaned.get('primary_email') or '',
                'phone_number': cleaned.get('phone_number') or '',
                'category_code': cleaned.get('category_code') or 'GENERAL',
                'brand': cleaned.get('brand') or '',
                'serial_number': cleaned.get('serial_number') or '',
                'preferred_condition': cleaned.get('preferred_condition') or 'Good',
                'priority': cleaned.get('priority') or '1',
                'order_id': cleaned.get('order_id') or '',
                'order_item_id': cleaned.get('order_item_id') or '',
                'organization_id': cleaned.get('organization_id') or '',
                'status': cleaned.get('status') or 'Pending',
                'start_date': cleaned.get('start_date') or '',
                'shipped_date': cleaned.get('shipped_date') or '',
                'delivery_date': cleaned.get('delivery_date') or '',
                'office_name': cleaned.get('office_name') or '',
                'address_line1': cleaned.get('address_line1') or '',
                'address_line2': cleaned.get('address_line2') or '',
                'city': cleaned.get('city') or '',
                'state': cleaned.get('state') or '',
                'postal_code': cleaned.get('postal_code') or '',
                'country_code': cleaned.get('country_code') or '',
                'carrier': cleaned.get('carrier') or '',
                'tracking_link': cleaned.get('tracking_link') or ''
            }
            
            # Update cleaned row with defaults
            for key, default_value in defaults.items():
                if not cleaned.get(key):
                    cleaned[key] = default_value
            
            return cleaned
            
        except Exception as e:
            logger.info(f"Error cleaning row: {e}")
            return None

    def group_orders_by_id(self, data):
        """Group CSV rows by order_id - copied from admin.py"""
        try:
            order_groups = {}
            individual_items = []
            
            # Group by order_id
            for row in data:
                order_id = row.get('order_id', '').strip()
                if order_id:
                    if order_id not in order_groups:
                        order_groups[order_id] = []
                    order_groups[order_id].append(row)
                else:
                    # No order_id, treat as individual
                    individual_items.append(row)
            
            grouped_orders = []
            
            # Process groups
            for order_id, items in order_groups.items():
                if len(items) > 1:
                    # Multiple items - create grouped order
                    primary_item = items[0]  # Use first item as primary
                    
                    # Create item summary
                    product_titles = [item['product_title'] for item in items]
                    if len(product_titles) <= 3:
                        title_summary = ', '.join(product_titles)
                    else:
                        title_summary = f"{', '.join(product_titles[:2])} and {len(product_titles) - 2} more..."
                    
                    grouped_order = {
                        'is_grouped': True,
                        'order_id': order_id,
                        'item_count': len(items),
                        'title_summary': title_summary,
                        'all_items': items,
                        # Include primary item data for compatibility
                        **primary_item
                    }
                    grouped_orders.append(grouped_order)
                else:
                    # Single item, add to individual
                    item = items[0]
                    item['is_grouped'] = False
                    individual_items.append(item)
            
            # Mark individual items
            for item in individual_items:
                if 'is_grouped' not in item:
                    item['is_grouped'] = False
            
            return grouped_orders, individual_items
            
        except Exception as e:
            logger.info(f"Error grouping orders: {e}")
            return [], data

    def preview_tickets_from_csv(self, file_path):
        """Preview tickets from CSV file before importing"""
        try:
            # Read CSV file using same method as admin.py
            with open(file_path, 'r', encoding='utf-8') as csvfile:
                csv_content = csvfile.read()
            
            csv_reader = csv.DictReader(io.StringIO(csv_content))
            
            # Convert to list and validate
            raw_data = []
            for row_index, row in enumerate(csv_reader):
                logger.info(f"Processing CSV row {row_index + 1}: {dict(row)}")
                # Clean and validate the row
                cleaned_row = self.clean_csv_row(row)
                if cleaned_row:  # Only add valid rows
                    logger.info(f"Row {row_index + 1} valid, adding to raw_data")
                    raw_data.append(cleaned_row)
                else:
                    logger.info(f"Row {row_index + 1} invalid, skipping")
            
            logger.info(f"Total valid rows after cleaning: {len(raw_data)}")
            
            if not raw_data:
                return {
                    'success': False,
                    'error': 'No valid data found in CSV',
                    'tickets': [],
                    'total_tickets': 0
                }
            
            # Group orders by order_id
            grouped_data, individual_data = self.group_orders_by_id(raw_data)
            
            # Combine grouped and individual data
            all_data = grouped_data + individual_data
            
            logger.info(f"Processing {len(grouped_data)} grouped orders and {len(individual_data)} individual items")
            
            # Check for duplicates before creating preview (only against existing DB tickets)
            db_session = self.db_manager.get_session()
            tickets_preview = []
            
            # Get all existing order IDs from database to avoid repeated queries
            existing_order_ids = set()
            try:
                existing_tickets = db_session.query(Ticket.firstbaseorderid).filter(
                    Ticket.firstbaseorderid.isnot(None)
                ).all()
                existing_order_ids = {ticket.firstbaseorderid for ticket in existing_tickets}
            except:
                existing_order_ids = set()
            
            try:
                for index, row in enumerate(all_data):
                    # Check for duplicate order_id only against existing database tickets
                    is_duplicate = False
                    order_id = row.get('order_id', '').strip()
                    if order_id and order_id in existing_order_ids:
                        is_duplicate = True
                        logger.info(f"Row {index + 1} marked as duplicate (order_id: {order_id})")
                    else:
                        logger.info(f"Row {index + 1} not duplicate (order_id: {order_id})")
                
                    if row.get('is_grouped', False):
                        # Grouped order
                        all_items = row.get('all_items', [])
                        
                        # Build description with all products
                        product_items = []
                        for item in all_items:
                            product_title = item.get('product_title', '')
                            brand = item.get('brand', '')
                            serial_number = item.get('serial_number', '')
                            
                            item_desc = f"- {product_title}"
                            if brand and brand != 'nan':
                                item_desc += f" ({brand})"
                            if serial_number and serial_number != 'nan':
                                item_desc += f" [Serial: {serial_number}]"
                            
                            product_items.append(item_desc)
                        
                        description = f"Order ID: {row['order_id']}\n\nItems:\n" + "\n".join(product_items)
                        
                        # Create customer address
                        customer_address = f"{row.get('address_line1', '')}\n{row.get('address_line2', '')}\n{row.get('city', '')}, {row.get('state', '')} {row.get('postal_code', '')}\n{row.get('country_code', '')}".strip()
                        if not customer_address or customer_address.replace('\n', '').replace(',', '').strip() == '':
                            customer_address = "Address not provided"
                        
                        # Check if ticket status is PROCESSING
                        ticket_status = row.get('status', 'Unknown')
                        is_processing = ticket_status.upper() == 'PROCESSING'
                        
                        ticket_data = {
                            'row_number': f"Order {row['order_id']}",
                            'subject': f"Order {row['order_id']} - {row.get('title_summary', 'Multiple Items')}",
                            'description': description,
                            'category': TicketCategory.ASSET_CHECKOUT_CLAW.name,
                            'priority': 'MEDIUM',
                            'requester_email': row.get('primary_email', ''),
                            'country': row.get('country_code', ''),
                            'company': row.get('org_name', ''),
                            'customer_name': row.get('person_name', ''),
                            'customer_address': customer_address,
                            'status': ticket_status,
                            'queue_name': 'FirstBase New Orders',
                            'order_id': row['order_id'],
                            'item_count': row.get('item_count', len(all_items)),
                            'is_processing': is_processing,
                            'is_duplicate': is_duplicate,
                            'cannot_import': is_processing or is_duplicate
                        }
                    else:
                        # Individual item
                        description = ""
                        # Add order ID if available
                        if row.get('order_id'):
                            description += f"Order ID: {row['order_id']}\n\n"
                        
                        description += f"Product: {row.get('product_title', '')}"
                        if row.get('brand') and row.get('brand') != 'nan':
                            description += f"\nBrand: {row['brand']}"
                        if row.get('serial_number') and row.get('serial_number') != 'nan':
                            description += f"\nSerial Number: {row['serial_number']}"
                        
                        # Create customer address
                        customer_address = f"{row.get('address_line1', '')}\n{row.get('address_line2', '')}\n{row.get('city', '')}, {row.get('state', '')} {row.get('postal_code', '')}\n{row.get('country_code', '')}".strip()
                        if not customer_address or customer_address.replace('\n', '').replace(',', '').strip() == '':
                            customer_address = "Address not provided"
                        
                        # Check if ticket status is PROCESSING
                        ticket_status = row.get('status', 'Unknown')
                        is_processing = ticket_status.upper() == 'PROCESSING'
                        
                        ticket_data = {
                            'row_number': index + 1,
                            'subject': f"Asset Request - {row.get('product_title', 'Unknown Product')}",
                            'description': description,
                            'category': TicketCategory.ASSET_CHECKOUT_CLAW.name,
                            'priority': 'MEDIUM',
                            'requester_email': row.get('primary_email', ''),
                            'country': row.get('country_code', ''),
                            'company': row.get('org_name', ''),
                            'customer_name': row.get('person_name', ''),
                            'customer_address': customer_address,
                            'status': ticket_status,
                            'queue_name': 'FirstBase New Orders',
                            'order_id': row.get('order_id', ''),
                            'item_count': 1,
                            'is_processing': is_processing,
                            'is_duplicate': is_duplicate,
                            'cannot_import': is_processing or is_duplicate
                        }
                    
                    tickets_preview.append(ticket_data)
                    logger.info(f"Added ticket to preview: {ticket_data['subject']}")
            
            finally:
                db_session.close()
            
            logger.info(f"Total tickets in preview: {len(tickets_preview)}")
            
            # Count processing and duplicate tickets
            processing_count = sum(1 for ticket in tickets_preview if ticket.get('is_processing', False))
            duplicate_count = sum(1 for ticket in tickets_preview if ticket.get('is_duplicate', False))
            importable_count = len(tickets_preview) - processing_count - duplicate_count
            
            return {
                'success': True,
                'total_tickets': len(tickets_preview),
                'importable_tickets': importable_count,
                'processing_tickets': processing_count,
                'duplicate_tickets': duplicate_count,
                'tickets': tickets_preview,
                'columns': list(csv_reader.fieldnames) if csv_reader.fieldnames else [],
                'grouped_by_order': len(grouped_data) > 0
            }
            
        except Exception as e:
            logger.error(f"Error previewing CSV file: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e),
                'tickets': [],
                'total_tickets': 0
            }

    def import_tickets_from_csv(self, file_path, user_id):
        """Import tickets from CSV file to FirstBase New Orders queue"""
        try:
            # Read CSV file using same method as preview
            with open(file_path, 'r', encoding='utf-8') as csvfile:
                csv_content = csvfile.read()
            
            csv_reader = csv.DictReader(io.StringIO(csv_content))
            
            # Convert to list and validate
            raw_data = []
            for row in csv_reader:
                # Clean and validate the row
                cleaned_row = self.clean_csv_row(row)
                if cleaned_row:  # Only add valid rows
                    raw_data.append(cleaned_row)
            
            if not raw_data:
                return {
                    'success': False,
                    'error': 'No valid data found in CSV',
                    'imported_count': 0
                }
            
            # Group orders by order_id
            grouped_data, individual_data = self.group_orders_by_id(raw_data)
            
            # Combine grouped and individual data
            all_data = grouped_data + individual_data
            
            db_session = self.db_manager.get_session()
            try:
                # Get the FirstBase New Orders queue
                firstbase_queue = db_session.query(Queue).filter(
                    Queue.name == 'FirstBase New Orders'
                ).first()
                
                if not firstbase_queue:
                    # Create the queue if it doesn't exist
                    firstbase_queue = Queue(
                        name='FirstBase New Orders',
                        description='Queue for new order tickets imported from CSV'
                    )
                    db_session.add(firstbase_queue)
                    db_session.commit()
                    db_session.refresh(firstbase_queue)
                
                imported_tickets = []
                skipped_processing = []
                skipped_duplicates = []
                
                # Get all existing order IDs from database to avoid repeated queries  
                existing_order_ids = set()
                try:
                    existing_tickets = db_session.query(Ticket.firstbaseorderid).filter(
                        Ticket.firstbaseorderid.isnot(None)
                    ).all()
                    existing_order_ids = {ticket.firstbaseorderid for ticket in existing_tickets}
                except:
                    existing_order_ids = set()
                
                for row in all_data:
                    # Skip tickets with PROCESSING status
                    if row.get('status', '').upper() == 'PROCESSING':
                        skipped_processing.append({
                            'order_id': row.get('order_id', ''),
                            'reason': 'Status is PROCESSING'
                        })
                        continue
                    
                    # Check for duplicate order_id only against existing database tickets
                    order_id = row.get('order_id', '').strip()
                    if order_id and order_id in existing_order_ids:
                        skipped_duplicates.append({
                            'order_id': order_id,
                            'reason': 'Order ID already exists in database'
                        })
                        continue
                    # Create or get customer - only if email is provided
                    customer = None
                    customer_created = False
                    
                    if row.get('primary_email') and row['primary_email'].strip():
                        customer = db_session.query(CustomerUser).filter(
                            CustomerUser.email == row['primary_email']
                        ).first()
                    
                    if not customer and row.get('primary_email') and row['primary_email'].strip():
                        logger.info(f"Creating customer with email: {row['primary_email']}")
                        # Get or create company
                        company = db_session.query(Company).filter(
                            Company.name == row['org_name']
                        ).first()
                        
                        if not company:
                            company = Company(
                                name=row['org_name'],
                                description=f"Auto-created from CSV import",
                                contact_email=row['primary_email']
                            )
                            db_session.add(company)
                            db_session.flush()
                        
                        # Create customer address
                        customer_address = f"{row.get('address_line1', '')}\n{row.get('address_line2', '')}\n{row.get('city', '')}, {row.get('state', '')} {row.get('postal_code', '')}\n{row.get('country_code', '')}".strip()
                        if not customer_address or customer_address.replace('\n', '').replace(',', '').strip() == '':
                            customer_address = "Address not provided"
                        
                        customer = CustomerUser(
                            name=row['person_name'] or 'Unknown Customer',
                            email=row['primary_email'],
                            contact_number=row.get('phone_number', '') or 'No phone provided',
                            address=customer_address,
                            company_id=company.id,
                            country=self.map_country_code(row.get('country_code', ''))
                        )
                        db_session.add(customer)
                        db_session.flush()
                        customer_created = True
                    elif not row.get('primary_email') or not row['primary_email'].strip():
                        # No email provided - create customer with a generated email
                        # Get or create company
                        company = db_session.query(Company).filter(
                            Company.name == row['org_name']
                        ).first()
                        
                        if not company:
                            company = Company(
                                name=row['org_name'],
                                description=f"Auto-created from CSV import",
                                contact_email=""
                            )
                            db_session.add(company)
                            db_session.flush()
                        
                        # Create customer address
                        customer_address = f"{row.get('address_line1', '')}\n{row.get('address_line2', '')}\n{row.get('city', '')}, {row.get('state', '')} {row.get('postal_code', '')}\n{row.get('country_code', '')}".strip()
                        if not customer_address or customer_address.replace('\n', '').replace(',', '').strip() == '':
                            customer_address = "Address not provided"
                        
                        # Generate a unique email for customer without email
                        generated_email = f"noemail_{uuid.uuid4().hex[:8]}@{row['org_name'].lower().replace(' ', '')}.generated"
                        
                        customer = CustomerUser(
                            name=row['person_name'] or 'Unknown Customer',
                            email=generated_email,
                            contact_number=row.get('phone_number', '') or 'No phone provided',
                            address=customer_address,
                            company_id=company.id,
                            country=self.map_country_code(row.get('country_code', ''))
                        )
                        db_session.add(customer)
                        db_session.flush()
                        customer_created = True
                    
                    # Create ticket based on whether it's grouped or individual
                    if row.get('is_grouped', False):
                        # Grouped order
                        all_items = row.get('all_items', [])
                        
                        # Build description with all products
                        product_items = []
                        for item in all_items:
                            product_title = item.get('product_title', '')
                            brand = item.get('brand', '')
                            serial_number = item.get('serial_number', '')
                            
                            item_desc = f"- {product_title}"
                            if brand and brand != 'nan':
                                item_desc += f" ({brand})"
                            if serial_number and serial_number != 'nan':
                                item_desc += f" [Serial: {serial_number}]"
                            
                            product_items.append(item_desc)
                        
                        description = f"Order ID: {row['order_id']}\n\nItems:\n" + "\n".join(product_items)
                        subject = f"Order {row['order_id']} - {row.get('title_summary', 'Multiple Items')}"
                        
                    else:
                        # Individual item
                        description = ""
                        # Add order ID if available
                        if row.get('order_id'):
                            description += f"Order ID: {row['order_id']}\n\n"
                        
                        description += f"Product: {row.get('product_title', '')}"
                        if row.get('brand') and row.get('brand') != 'nan':
                            description += f"\nBrand: {row['brand']}"
                        if row.get('serial_number') and row.get('serial_number') != 'nan':
                            description += f"\nSerial Number: {row['serial_number']}"
                        
                        subject = f"Asset Request - {row.get('product_title', 'Unknown Product')}"
                    
                    # Create new Ticket
                    ticket = Ticket(
                        subject=subject,
                        description=description,
                        category=TicketCategory.ASSET_CHECKOUT_CLAW,
                        status=TicketStatus.NEW,
                        priority='MEDIUM',
                        requester_id=user_id,  # Set the importing user as requester
                        customer_id=customer.id if customer else None,  # Link to customer
                        queue_id=firstbase_queue.id,
                        country=row.get('country_code', None),
                        firstbaseorderid=row.get('order_id', None),  # Store order ID for duplicate prevention
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                    
                    db_session.add(ticket)
                    db_session.flush()  # Ensure ticket gets an ID
                    
                    # Send queue notifications for the imported ticket
                    try:
                        from utils.queue_notification_sender import send_queue_notifications
                        send_queue_notifications(ticket, action_type="created")
                    except Exception as e:
                        logger.error(f"Error sending queue notifications for imported ticket: {str(e)}")
                    
                    imported_tickets.append({
                        'subject': subject,
                        'description': description[:100] + '...' if len(description) > 100 else description,
                        'category': TicketCategory.ASSET_CHECKOUT_CLAW.name,
                        'priority': 'MEDIUM',
                        'order_id': row.get('order_id', ''),
                        'item_count': row.get('item_count', 1),
                        'customer_created': customer_created
                    })
                
                db_session.commit()
                
                return {
                    'success': True,
                    'imported_count': len(imported_tickets),
                    'skipped_processing_count': len(skipped_processing),
                    'skipped_duplicates_count': len(skipped_duplicates),
                    'queue_name': firstbase_queue.name,
                    'tickets': imported_tickets,
                    'skipped_processing': skipped_processing,
                    'skipped_duplicates': skipped_duplicates
                }
                
            except Exception as e:
                db_session.rollback()
                raise e
            finally:
                db_session.close()
                
        except Exception as e:
            logger.error(f"Error importing tickets from CSV: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e),
                'imported_count': 0
            }

    def get_supported_csv_columns(self):
        """Get list of supported CSV columns for ticket import"""
        return [
            'order_id',          # For grouping multiple items into one ticket
            'order_item_id',     # Individual item ID
            'product_title',     # Product name/title (REQUIRED)
            'brand',             # Product brand
            'serial_number',     # Serial number
            'category_code',     # Category code
            'person_name',       # Customer name
            'primary_email',     # Customer email
            'phone_number',      # Customer phone
            'org_name',          # Organization name (REQUIRED)
            'address_line1',     # Address line 1
            'address_line2',     # Address line 2
            'city',              # City
            'state',             # State
            'postal_code',       # Postal code
            'country_code',      # Country code
            'office_name',       # Office name
            'preferred_condition', # Preferred condition
            'priority',          # Priority
            'status',            # Status
            'start_date',        # Start date
            'shipped_date',      # Shipped date
            'delivery_date',     # Delivery date
            'carrier',           # Carrier
            'tracking_link'      # Tracking link
        ]

# Create singleton instance
ticket_import_store = TicketImportStore()