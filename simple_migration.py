# Simple migration script using direct SQL
from models.base import Base
from models.ticket import Ticket
from models.asset import Asset
from utils.db_manager import DatabaseManager
from sqlalchemy import text
import traceback

db_manager = DatabaseManager()
db_session = db_manager.get_session()

try:
    print("Migrating ticket-asset relationships using direct SQL...")
    
    # Get all tickets with asset_id set
    tickets = db_session.query(Ticket).filter(Ticket.asset_id.isnot(None)).all()
    print(f"Found {len(tickets)} tickets with assets to migrate")
    
    # For each ticket, execute a direct SQL insert
    migration_count = 0
    for ticket in tickets:
        if ticket.asset_id:
            try:
                # Check if relationship already exists to avoid duplicates
                check_sql = text("SELECT COUNT(*) FROM ticket_assets WHERE ticket_id = :ticket_id AND asset_id = :asset_id")
                result = db_session.execute(check_sql, {"ticket_id": ticket.id, "asset_id": ticket.asset_id}).scalar()
                
                if result == 0:
                    # Insert directly using SQL rather than the ORM relationship
                    insert_sql = text("INSERT INTO ticket_assets (ticket_id, asset_id) VALUES (:ticket_id, :asset_id)")
                    db_session.execute(insert_sql, {"ticket_id": ticket.id, "asset_id": ticket.asset_id})
                    print(f"Created relationship for ticket {ticket.id} and asset {ticket.asset_id}")
                    migration_count += 1
                else:
                    print(f"Relationship already exists for ticket {ticket.id} and asset {ticket.asset_id}")
            except Exception as e:
                print(f"Error processing ticket {ticket.id}: {str(e)}")
    
    db_session.commit()
    print(f"Migration completed successfully. Migrated {migration_count} relationships.")
    
except Exception as e:
    db_session.rollback()
    print(f"Error migrating relationships: {str(e)}")
    traceback.print_exc()
finally:
    db_session.close() 