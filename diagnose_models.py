"""
Diagnostic script to check model relationships and imports.
Run this on PythonAnywhere to diagnose why the 'assets' relationship is not found.
"""
import inspect
import sys

# Import models and check their attributes
try:
    logger.info("========== CHECKING TICKET MODEL ==========")
    from models.ticket import Ticket
    ticket_attributes = dir(Ticket)
    logger.info("Ticket class attributes: {[attr for attr in ticket_attributes if not attr.startswith('_')]}")
    
    # Check if 'assets' is in the attributes
    if 'assets' in ticket_attributes:
        logger.info("✅ 'assets' attribute IS defined in Ticket model")
    else:
        logger.info("❌ 'assets' attribute is NOT defined in Ticket model")
    
    # Check for relationship attributes
    logger.info("\nRelationship attributes:")
    for attr_name in ticket_attributes:
        if not attr_name.startswith('_'):
            attr = getattr(Ticket, attr_name)
            if str(type(attr)).find('relationship') > -1:
                logger.info("  - {attr_name}: {attr}")
    
    # Check ticket module source code
    logger.info("\nTicket module source code:")
    import models.ticket
    ticket_source = inspect.getsource(models.ticket)
    # Look for 'assets' in the source
    if "assets = relationship" in ticket_source:
        logger.info("✅ 'assets = relationship' found in Ticket source code")
        # Find the full assets relationship line
        for line in ticket_source.split('\n'):
            if "assets = relationship" in line:
                logger.info("  Line: {line.strip()}")
    else:
        logger.info("❌ 'assets = relationship' NOT found in Ticket source code")
    
    logger.info("\n========== CHECKING ASSET MODEL ==========")
    from models.asset import Asset, ticket_assets
    asset_attributes = dir(Asset)
    logger.info("Asset class attributes: {[attr for attr in asset_attributes if not attr.startswith('_')]}")
    
    # Check if 'tickets' is in the attributes
    if 'tickets' in asset_attributes:
        logger.info("✅ 'tickets' attribute IS defined in Asset model")
    else:
        logger.info("❌ 'tickets' attribute is NOT defined in Asset model")
    
    # Examine the ticket_assets table
    logger.info("\nticket_assets table definition:")
    logger.info(ticket_assets)
    
    # Check for relationship attributes
    logger.info("\nRelationship attributes:")
    for attr_name in asset_attributes:
        if not attr_name.startswith('_'):
            attr = getattr(Asset, attr_name)
            if str(type(attr)).find('relationship') > -1:
                logger.info("  - {attr_name}: {attr}")
                
    # Check asset module source code
    logger.info("\nAsset module source code (relationship parts):")
    import models.asset
    asset_source = inspect.getsource(models.asset)
    # Look for ticket_assets and tickets relationship in the source
    ticket_assets_lines = []
    tickets_relationship_lines = []
    for line in asset_source.split('\n'):
        if "ticket_assets" in line:
            ticket_assets_lines.append(line.strip())
        if "tickets = relationship" in line:
            tickets_relationship_lines.append(line.strip())
    
    if ticket_assets_lines:
        logger.info("✅ 'ticket_assets' definition found in Asset source code:")
        for line in ticket_assets_lines:
            logger.info("  {line}")
    else:
        logger.info("❌ 'ticket_assets' definition NOT found in Asset source code")
        
    if tickets_relationship_lines:
        logger.info("✅ 'tickets = relationship' found in Asset source code:")
        for line in tickets_relationship_lines:
            logger.info("  {line}")
    else:
        logger.info("❌ 'tickets = relationship' NOT found in Asset source code")
    
except Exception as e:
    logger.info("Error during diagnosis: {str(e)}")
    import traceback
    traceback.print_exc()

logger.info("\n========== PYTHON VERSION AND PATH ==========")
logger.info("Python version: {sys.version}")
logger.info("Python executable: {sys.executable}")
logger.info("\nPython path:")
for path in sys.path:
    logger.info("  {path}")

logger.info("\n========== INSTRUCTIONS ==========")
logger.info("""
1. Check if relationships are correctly defined in model source code.
2. Verify that your running application is using the latest code.
3. Make sure the models are imported correctly in your application.
4. Try a full application restart (not just touching the wsgi file).

To completely restart the PythonAnywhere app:
1. Go to the Web tab in PythonAnywhere
2. Click on "Reload <username>.pythonanywhere.com"
3. Wait for the restart to complete
""") 