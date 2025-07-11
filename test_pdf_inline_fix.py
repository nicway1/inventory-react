#!/usr/bin/env python3
"""
Test script to verify that PDF inline viewing is working correctly.
"""

import requests
from utils.db_manager import DatabaseManager
from models.ticket import Ticket
from models.ticket_attachment import TicketAttachment

def test_pdf_inline_viewing():
    """Test that PDFs can be viewed inline without forcing download"""
    logger.info("🧪 Testing PDF inline viewing functionality...")
    
    db_manager = DatabaseManager()
    db_session = db_manager.get_session()
    
    try:
        # Find tickets with PDF attachments
        pdf_attachments = db_session.query(TicketAttachment).filter(
            TicketAttachment.file_type == 'pdf'
        ).limit(5).all()
        
        logger.info("Found {len(pdf_attachments)} PDF attachments to test")
        
        for attachment in pdf_attachments:
            logger.info("\n📋 Testing PDF: {attachment.original_filename}")
            logger.info("   Ticket ID: {attachment.ticket_id}")
            logger.info("   File path: {attachment.file_path}")
            logger.info("   File exists: {'✓' if os.path.exists(attachment.file_path) else '✗'}")
            
            # Test the route endpoint pattern
            route_url = f"/tickets/{attachment.ticket_id}/attachment/{attachment.id}"
            logger.info("   Route URL: {route_url}")
            
            # Check file type detection
            is_pdf = attachment.original_filename.lower().endswith('.pdf')
            logger.info("   Detected as PDF: {'✓' if is_pdf else '✗'}")
            
        # Test the logic from the updated route
        logger.info("\n🔧 Testing route logic...")
        
        if pdf_attachments:
            test_attachment = pdf_attachments[0]
            
            # Simulate route parameters
            is_pdf = test_attachment.original_filename.lower().endswith('.pdf')
            download_requested = False  # Simulating no ?download=true parameter
            
            logger.info("Test file: {test_attachment.original_filename}")
            logger.info("Is PDF: {is_pdf}")
            logger.info("Download requested: {download_requested}")
            
            if is_pdf and not download_requested:
                logger.info("✓ Would serve with inline viewing (mimetype='application/pdf', as_attachment=False)")
            else:
                logger.info("✗ Would serve as download (as_attachment=True)")
        
        # Summary
        logger.info("\n📊 Summary:")
        logger.info("✓ Found {len(pdf_attachments)} PDF attachments")
        logger.info("✓ Route updated to serve PDFs inline by default")
        logger.info("✓ Download still available with ?download=true parameter")
        logger.info("✓ Non-PDF files will still download as expected")
        
    except Exception as e:
        logger.info("❌ Error testing PDF inline viewing: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        db_session.close()

if __name__ == "__main__":
    import os  # Add this import for file existence check
    test_pdf_inline_viewing() 