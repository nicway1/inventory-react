#!/usr/bin/env python
"""
Direct fix for unterminated string in Asset model transactions relationship
"""
import os
import sys
import shutil
from datetime import datetime

def direct_fix():
    """Direct fix for line 78 in asset.py"""
    logger.info("Starting direct fix for Asset model relationship...")
    
    # Determine if we're running locally or on PythonAnywhere
    if os.path.exists('/home/nicway2/inventory'):
        model_file_path = '/home/nicway2/inventory/models/asset.py'
        logger.info("Running on PythonAnywhere environment")
    else:
        model_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'models', 'asset.py')
        logger.info("Running on local environment, path: {model_file_path}")
    
    if not os.path.exists(model_file_path):
        logger.info("Error: Asset model file not found at {model_file_path}")
        return False
    
    # Create a backup of the original file
    backup_path = f"{model_file_path}.bak.{datetime.now().strftime('%Y%m%d%H%M%S')}"
    try:
        shutil.copy2(model_file_path, backup_path)
        logger.info("Backup created at {backup_path}")
    except Exception as e:
        logger.info("Warning: Could not create backup: {str(e)}")
    
    # Read the file content
    try:
        with open(model_file_path, 'r') as f:
            content = f.readlines()
    except Exception as e:
        logger.info("Error reading the file: {str(e)}")
        return False
    
    # Try to fix by just replacing the entire problematic line
    # The correct line should be:
    correct_line = '    transactions = relationship("AssetTransaction", back_populates="asset", order_by="desc(AssetTransaction.transaction_date)")\n'
    
    # Look for a line with 'transactions = relationship' and replace it
    found = False
    for i, line in enumerate(content):
        if 'transactions =' in line and 'relationship(' in line and 'AssetTransaction' in line:
            logger.info("Found transactions relationship at line {i+1}: {line.strip()}")
            content[i] = correct_line
            logger.info("Replaced with: {correct_line.strip()}")
            found = True
            break
    
    if not found:
        logger.info("Could not find the transactions relationship line.")
        logger.info("Will try to look at line 78 specifically...")
        
        # Try to fix line 78 directly (Python uses 0-based indexing)
        if len(content) >= 78:
            logger.info("Line 78 content: {content[77].strip()}")
            content[77] = correct_line
            logger.info("Replaced with: {correct_line.strip()}")
            found = True
        else:
            logger.info("File has fewer than 78 lines (only {len(content)} lines)")
            return False
    
    # Write the fixed content back
    try:
        with open(model_file_path, 'w') as f:
            f.writelines(content)
        logger.info("Successfully wrote fixed content to {model_file_path}")
        return True
    except Exception as e:
        logger.info("Error writing to file: {str(e)}")
        return False

if __name__ == "__main__":
    success = direct_fix()
    if success:
        logger.info("Asset model relationship successfully fixed.")
        logger.info("Now run update_asset_model.py to add the track_change method")
        logger.info("Then restart your application with:")
        logger.info("touch /var/www/nicway2_pythonanywhere_com_wsgi.py")
    else:
        logger.info("Failed to fix Asset model relationship.")
        logger.info("You may need to manually edit the file.")
        sys.exit(1) 