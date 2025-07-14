from utils.db_manager import DatabaseManager
from models.ticket import Ticket, TicketCategory, TicketStatus
from models.queue import Queue
import pandas as pd
from datetime import datetime
import os
import logging

# Set up logging for this module
logger = logging.getLogger(__name__)


class TicketImportStore:
    def __init__(self):
        self.db_manager = DatabaseManager()

    def preview_tickets_from_csv(self, file_path):
        """Preview tickets from CSV file before importing"""
        try:
            # Read CSV file
            df = pd.read_csv(file_path)
            
            # Debug: Print column names
            logger.info(f"CSV columns: {df.columns.tolist()}")
            
            tickets_preview = []
            
            # Convert DataFrame to ticket preview data
            for index, row in df.iterrows():
                # Extract ticket data from CSV row
                ticket_data = {
                    'row_number': index + 1,
                    'subject': str(row.get('subject', row.get('Subject', f'Ticket {index + 1}'))),
                    'description': str(row.get('description', row.get('Description', 'Imported from CSV'))),
                    'category': str(row.get('category', row.get('Category', 'GENERAL'))),
                    'priority': str(row.get('priority', row.get('Priority', 'MEDIUM'))),
                    'requester_email': str(row.get('requester_email', row.get('Requester Email', ''))),
                    'country': str(row.get('country', row.get('Country', ''))),
                    'company': str(row.get('company', row.get('Company', ''))),
                    'status': TicketStatus.NEW.value,
                    'queue_name': 'FirstBase New Orders'
                }
                
                tickets_preview.append(ticket_data)
            
            return {
                'success': True,
                'total_tickets': len(tickets_preview),
                'tickets': tickets_preview,
                'columns': df.columns.tolist()
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
            # Read CSV file
            df = pd.read_csv(file_path)
            
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
                
                # Convert DataFrame to tickets
                for index, row in df.iterrows():
                    # Extract ticket data from CSV row
                    subject = str(row.get('subject', row.get('Subject', f'Ticket {index + 1}')))
                    description = str(row.get('description', row.get('Description', 'Imported from CSV')))
                    category_str = str(row.get('category', row.get('Category', 'GENERAL')))
                    priority_str = str(row.get('priority', row.get('Priority', 'MEDIUM')))
                    requester_email = str(row.get('requester_email', row.get('Requester Email', '')))
                    country = str(row.get('country', row.get('Country', '')))
                    company = str(row.get('company', row.get('Company', '')))
                    
                    # Convert category string to enum
                    try:
                        category = TicketCategory[category_str.upper()]
                    except (KeyError, AttributeError):
                        category = TicketCategory.GENERAL
                    
                    # Create new Ticket
                    ticket = Ticket(
                        subject=subject,
                        description=description,
                        category=category,
                        status=TicketStatus.NEW,
                        priority=priority_str.upper() if priority_str.upper() in ['LOW', 'MEDIUM', 'HIGH', 'URGENT'] else 'MEDIUM',
                        requester_id=user_id,  # Set the importing user as requester
                        queue_id=firstbase_queue.id,
                        country=country if country else None,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                    
                    # Add additional fields from CSV if they exist
                    if hasattr(ticket, 'company') and company:
                        ticket.company = company
                    if hasattr(ticket, 'requester_email') and requester_email:
                        ticket.requester_email = requester_email
                    
                    db_session.add(ticket)
                    imported_tickets.append({
                        'subject': subject,
                        'description': description,
                        'category': category.value,
                        'priority': priority_str
                    })
                
                db_session.commit()
                
                return {
                    'success': True,
                    'imported_count': len(imported_tickets),
                    'queue_name': firstbase_queue.name,
                    'tickets': imported_tickets
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
            'subject',
            'description', 
            'category',
            'priority',
            'requester_email',
            'country',
            'company'
        ]

# Create singleton instance
ticket_import_store = TicketImportStore()