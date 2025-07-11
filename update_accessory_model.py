#!/usr/bin/env python
"""
Script to update the Accessory model file to include track_change method
"""
import os
import sys
import re
from datetime import datetime

def update_model():
    logger.info("Updating Accessory model file...")
    
    # Path to the model file - use current directory for local development
    model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'models', 'accessory.py')
    
    if not os.path.exists(model_path):
        logger.info("Error: Model file not found at {model_path}")
        return False
    
    # Read current file content
    with open(model_path, 'r') as f:
        content = f.read()
    
    # Check if the method already exists
    if 'def track_change' in content:
        logger.info("The track_change method already exists in the model file.")
        return True
    
    # Find position to add the method - after all properties but before any other methods
    # We'll look for the relationship definitions which should be at the end of the class properties
    relationship_pattern = r'(transactions = relationship\([^)]+\))'
    
    match = re.search(relationship_pattern, content)
    if not match:
        logger.info("Could not locate the right position in the file to add the method.")
        return False
    
    # Get the position after the last relationship
    insert_position = match.end()
    
    # Create the method code with triple quotes properly escaped
    track_change_method = '''
    
    def track_change(self, user_id, action, changes, notes=None):
        """Create a history entry for accessory changes
        
        Args:
            user_id: ID of the user who made the change
            action: Description of the action (e.g., "UPDATE", "STATUS_CHANGE")
            changes: Dictionary of changes in the format {field: {'old': old_value, 'new': new_value}}
            notes: Any additional notes about the change
            
        Returns:
            AccessoryHistory object (not yet added to session)
        """
        from models.accessory_history import AccessoryHistory
        
        return AccessoryHistory(
            accessory_id=self.id,
            user_id=user_id,
            action=action,
            changes=changes,
            notes=notes
        )
'''
    
    # Add the method to the content
    new_content = content[:insert_position] + track_change_method + content[insert_position:]
    
    # Create a backup of the original file
    backup_path = f"{model_path}.bak.{datetime.now().strftime('%Y%m%d%H%M%S')}"
    with open(backup_path, 'w') as f:
        f.write(content)
    logger.info("Created backup of original file at {backup_path}")
    
    # Write the updated content
    with open(model_path, 'w') as f:
        f.write(new_content)
    
    logger.info("Successfully added track_change method to {model_path}")
    logger.info("Please restart your application for changes to take effect.")
    return True

if __name__ == "__main__":
    update_model() 