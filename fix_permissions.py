"""
Fix Permission Management Page - Database Cleanup Script

This script:
1. Finds and removes duplicate SUPER_ADMIN entries in the permissions table
2. Adds a unique constraint to the user_type column

Run this script with:
python fix_permissions.py
"""

from database import db_manager, Base, engine
from models.permission import Permission, UserType
from sqlalchemy import text
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_duplicate_permissions():
    """Fix duplicate entries in the permissions table and add unique constraint"""
    session = db_manager.get_session()
    
    try:
        # Step 1: Find all SUPER_ADMIN permissions
        super_admin_permissions = session.query(Permission).filter(
            Permission.user_type == UserType.SUPER_ADMIN
        ).all()
        
        # Check if duplicates exist
        if len(super_admin_permissions) <= 1:
            logger.info("No duplicate SUPER_ADMIN permissions found.")
        else:
            logger.info(f"Found {len(super_admin_permissions)} SUPER_ADMIN permissions.")
            
            # Keep the first one, delete the rest
            keep_permission = super_admin_permissions[0]
            logger.info(f"Keeping permission with ID: {keep_permission.id}")
            
            for perm in super_admin_permissions[1:]:
                logger.info(f"Deleting duplicate permission with ID: {perm.id}")
                session.delete(perm)
                
            # Commit the deletions
            session.commit()
            logger.info("Successfully removed duplicate SUPER_ADMIN permissions.")

        # Step 2: Add unique constraint to user_type column
        # Check database type to use the correct syntax
        db_type = engine.name
        
        if db_type == 'sqlite':
            # For SQLite, we need a workaround since it doesn't support 
            # adding constraints to existing tables
            logger.info("SQLite detected - using alternate approach for unique constraint")
            
            # Create a new temporary table with the constraint
            session.execute(text("""
                CREATE TABLE IF NOT EXISTS new_permissions (
                    id INTEGER PRIMARY KEY,
                    user_type VARCHAR NOT NULL UNIQUE,
                    can_view_assets BOOLEAN,
                    can_edit_assets BOOLEAN,
                    can_delete_assets BOOLEAN,
                    can_create_assets BOOLEAN,
                    can_view_country_assets BOOLEAN,
                    can_edit_country_assets BOOLEAN,
                    can_delete_country_assets BOOLEAN,
                    can_create_country_assets BOOLEAN,
                    can_view_accessories BOOLEAN,
                    can_edit_accessories BOOLEAN,
                    can_delete_accessories BOOLEAN,
                    can_create_accessories BOOLEAN,
                    can_view_companies BOOLEAN,
                    can_edit_companies BOOLEAN,
                    can_delete_companies BOOLEAN,
                    can_create_companies BOOLEAN,
                    can_view_users BOOLEAN,
                    can_edit_users BOOLEAN,
                    can_delete_users BOOLEAN,
                    can_create_users BOOLEAN,
                    can_import_data BOOLEAN,
                    can_export_data BOOLEAN,
                    can_view_reports BOOLEAN,
                    can_generate_reports BOOLEAN
                )
            """))
            
            # Copy data to the new table
            session.execute(text("""
                INSERT INTO new_permissions 
                SELECT * FROM permissions
            """))
            
            # Drop the old table and rename the new one
            session.execute(text("DROP TABLE permissions"))
            session.execute(text("ALTER TABLE new_permissions RENAME TO permissions"))
            
            logger.info("Recreated permissions table with unique constraint")
            
        elif db_type in ('postgresql', 'mysql'):
            # For PostgreSQL and MySQL
            try:
                if db_type == 'postgresql':
                    session.execute(text(
                        "ALTER TABLE permissions ADD CONSTRAINT uq_permissions_user_type UNIQUE (user_type)"
                    ))
                else:  # MySQL
                    session.execute(text(
                        "ALTER TABLE permissions ADD UNIQUE INDEX uq_user_type (user_type)"
                    ))
                logger.info(f"Added unique constraint to {db_type} database")
            except Exception as e:
                # Constraint might already exist
                if "already exists" in str(e) or "Duplicate key" in str(e):
                    logger.info("Unique constraint already exists")
                else:
                    raise
        else:
            logger.warning(f"Database type {db_type} not explicitly supported. Skipping constraint addition.")
        
        # Final verification
        remaining_count = session.query(Permission).filter(
            Permission.user_type == UserType.SUPER_ADMIN
        ).count()
        logger.info(f"Final check: {remaining_count} SUPER_ADMIN permission(s) in database")
        
        logger.info("Database cleanup complete. Please restart your application.")
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error during fix: {str(e)}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    print("Starting permission database cleanup...")
    fix_duplicate_permissions()
    print("Done! If no errors occurred, your database has been fixed.")
    print("Please restart your application now.") 