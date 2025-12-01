#!/usr/bin/env python3
"""
Script to fix existing PDF attachments by updating their file_type field.
This ensures that PDFs show the preview button in the UI.
"""

from utils.db_manager import DatabaseManager
from models.ticket_attachment import TicketAttachment

def fix_pdf_file_types():
    """Fix existing PDF attachments by setting correct file_type"""
    logger.info("🔧 Fixing PDF file types...")
    
    db_manager = DatabaseManager()
    db_session = db_manager.get_session()
    
    try:
        # Find all attachments
        all_attachments = db_session.query(TicketAttachment).all()
        
        logger.info("Found {len(all_attachments)} total attachments")
        
        pdf_fixed = 0
        other_fixed = 0
        
        for attachment in all_attachments:
            # Get file extension from filename
            if '.' in attachment.filename:
                file_extension = attachment.filename.lower().split('.')[-1]
            else:
                file_extension = ''
            
            # Check if we need to update the file_type
            if attachment.file_type != file_extension:
                old_file_type = attachment.file_type
                attachment.file_type = file_extension
                
                if file_extension == 'pdf':
                    pdf_fixed += 1
                    logger.info("✓ Fixed PDF: {attachment.filename} (was: {old_file_type}, now: {file_extension})")
                else:
                    other_fixed += 1
                    logger.info("✓ Fixed file: {attachment.filename} (was: {old_file_type}, now: {file_extension})")
        
        # Commit changes
        db_session.commit()
        
        logger.info("\n📊 Summary:")
        logger.info("✓ Fixed {pdf_fixed} PDF files")
        logger.info("✓ Fixed {other_fixed} other files")
        logger.info("✓ Total attachments processed: {len(all_attachments)}")
        
        if pdf_fixed > 0:
            logger.info("\n🎉 PDF files should now show preview buttons in the UI!")
        
    except Exception as e:
        db_session.rollback()
        logger.info("❌ Error fixing file types: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        db_session.close()

if __name__ == "__main__":
    fix_pdf_file_types() 







