"""
Script to update Ticket and Asset models with the missing relationship definitions.
This will directly modify the model files on PythonAnywhere to add the required relationships.
"""
import os
import shutil
import re

# File paths
TICKET_MODEL = 'models/ticket.py'
ASSET_MODEL = 'models/asset.py'

# Backup files first
def backup_file(file_path):
    if os.path.exists(file_path):
        backup_path = f"{file_path}.backup"
        logger.info("Creating backup of {file_path} to {backup_path}")
        shutil.copy2(file_path, backup_path)
        return True
    return False

# Update Asset model to add ticket_assets table and tickets relationship
def update_asset_model():
    logger.info("Updating Asset model in {ASSET_MODEL}")
    if not os.path.exists(ASSET_MODEL):
        logger.info("Error: {ASSET_MODEL} not found!")
        return False
    
    with open(ASSET_MODEL, 'r') as f:
        asset_content = f.read()
    
    # Check if ticket_assets table is already defined
    if "ticket_assets = Table(" in asset_content:
        logger.info("ticket_assets table is already defined in Asset model")
    else:
        # Add ticket_assets table after imports
        ticket_assets_def = """
# Association table for many-to-many relationship between tickets and assets
ticket_assets = Table(
    'ticket_assets',
    Base.metadata,
    Column('ticket_id', Integer, ForeignKey('tickets.id'), primary_key=True),
    Column('asset_id', Integer, ForeignKey('assets.id'), primary_key=True)
)
"""
        # Insert after imports
        import_pattern = r'(from models\.base import Base.*?$)'
        asset_content = re.sub(import_pattern, r'\1\n' + ticket_assets_def, asset_content, flags=re.DOTALL)
    
    # Check if tickets relationship is already defined
    if "tickets = relationship" in asset_content:
        logger.info("tickets relationship is already defined in Asset model")
    else:
        # Add tickets relationship to relationships section
        relationship_pattern = r'(# Relationships.*?)(^$)'
        tickets_relationship = "    tickets = relationship(\"Ticket\", secondary=ticket_assets, back_populates=\"assets\")\n    "
        
        if re.search(relationship_pattern, asset_content, re.DOTALL | re.MULTILINE):
            asset_content = re.sub(relationship_pattern, r'\1' + tickets_relationship + r'\2', 
                                   asset_content, flags=re.DOTALL | re.MULTILINE)
        else:
            logger.info("Relationship section not found, trying to add at end of class")
            class_end_pattern = r'(^class Asset.*?)(^\S)'
            asset_content = re.sub(class_end_pattern, 
                                  r'\1    # Relationships\n' + tickets_relationship + r'\n\2', 
                                  asset_content, flags=re.DOTALL | re.MULTILINE)
    
    # Write updated content
    with open(ASSET_MODEL, 'w') as f:
        f.write(asset_content)
    
    logger.info("Updated {ASSET_MODEL}")
    return True

# Update Ticket model to add assets relationship
def update_ticket_model():
    logger.info("Updating Ticket model in {TICKET_MODEL}")
    if not os.path.exists(TICKET_MODEL):
        logger.info("Error: {TICKET_MODEL} not found!")
        return False
    
    with open(TICKET_MODEL, 'r') as f:
        ticket_content = f.read()
    
    # Check if assets relationship is already defined
    if "assets = relationship" in ticket_content:
        logger.info("assets relationship is already defined in Ticket model")
        return True
    
    # Look for relationship section
    relationship_pattern = r'(# Relationships.*?asset = relationship.*?)(\n    \w)'
    if re.search(relationship_pattern, ticket_content, re.DOTALL):
        # Add assets relationship after asset relationship
        assets_relationship = "\n    assets = relationship('Asset', secondary='ticket_assets', back_populates='tickets')"
        ticket_content = re.sub(relationship_pattern, r'\1' + assets_relationship + r'\2', 
                               ticket_content, flags=re.DOTALL)
    else:
        logger.info("Could not find proper insertion point for assets relationship")
        return False
    
    # Write updated content
    with open(TICKET_MODEL, 'w') as f:
        f.write(ticket_content)
    
    logger.info("Updated {TICKET_MODEL}")
    return True

# Main execution
try:
    logger.info("==== Starting model update ====")
    
    # Backup files
    backup_file(ASSET_MODEL)
    backup_file(TICKET_MODEL)
    
    # Update models
    asset_updated = update_asset_model()
    ticket_updated = update_ticket_model()
    
    if asset_updated and ticket_updated:
        logger.info("Successfully updated both models. Please restart your web application.")
        logger.info("If the changes don't take effect, check the backup files and manually merge the changes.")
        logger.info("\nRemember to restart your web application:")
        logger.info("1. Go to the Web tab in PythonAnywhere")
        logger.info("2. Click on 'Reload <username>.pythonanywhere.com'")
    else:
        logger.info("WARNING: Not all models were updated successfully!")
        
except Exception as e:
    import traceback
    logger.info("Error updating models: {str(e)}")
    traceback.print_exc()
    logger.info("\nPlease try manually updating the files using the backup files as reference.") 