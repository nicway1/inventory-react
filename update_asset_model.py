#!/usr/bin/env python
"""
Script to update the Asset model with track_change method
"""
import os
import sys
import shutil
from datetime import datetime

def update_asset_model():
    """Add track_change method to Asset model"""
    print("Starting update of Asset model...")
    
    # Determine if we're running locally or on PythonAnywhere
    if os.path.exists('/home/nicway2/inventory'):
        model_file_path = '/home/nicway2/inventory/models/asset.py'
        print("Running on PythonAnywhere environment")
    else:
        model_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'models', 'asset.py')
        print(f"Running on local environment, path: {model_file_path}")
    
    if not os.path.exists(model_file_path):
        print(f"Error: Asset model file not found at {model_file_path}")
        return False
    
    # Create a backup of the original file
    backup_path = f"{model_file_path}.bak.{datetime.now().strftime('%Y%m%d%H%M%S')}"
    try:
        shutil.copy2(model_file_path, backup_path)
        print(f"Backup created at {backup_path}")
    except Exception as e:
        print(f"Warning: Could not create backup: {str(e)}")
    
    # Read the current model file
    with open(model_file_path, 'r') as f:
        content = f.read()
    
    # Check if track_change method already exists
    if 'def track_change' in content:
        print("track_change method already exists in the model. No changes needed.")
        return True
    
    # Find the position to insert the track_change method - after the class attributes and relationships
    # We'll look for the last relationship line
    relationship_patterns = [
        "relationship(\"AssetHistory\"",
        "relationship(\"AssetTransaction\""
    ]
    
    # Get the position of the last relationship definition
    pos = -1
    for pattern in relationship_patterns:
        pattern_pos = content.find(pattern)
        if pattern_pos != -1:
            pattern_end = content.find(")", pattern_pos)
            if pattern_end != -1 and pattern_end > pos:
                pos = pattern_end + 1
    
    if pos == -1:
        print("Could not find a suitable position to insert the track_change method.")
        return False
    
    # Find the next line after the position
    next_line_pos = content.find("\n", pos)
    if next_line_pos != -1:
        pos = next_line_pos + 1
    
    # Insert the track_change method - using triple quotes in the correct format
    track_change_method = '''
    def track_change(self, user_id, action, changes, notes=None):
        """Create a history entry for asset changes
        
        Args:
            user_id: ID of the user who made the change
            action: Description of the action (e.g., "UPDATE", "STATUS_CHANGE")
            changes: Dictionary of changes in the format {field: {'old': old_value, 'new': new_value}}
            notes: Any additional notes about the change
            
        Returns:
            AssetHistory object (not yet added to session)
        """
        from models.asset_history import AssetHistory
        
        return AssetHistory(
            asset_id=self.id,
            user_id=user_id,
            action=action,
            changes=changes,
            notes=notes
        )
'''
    
    new_content = content[:pos] + track_change_method + content[pos:]
    
    # Write back to the file
    try:
        with open(model_file_path, 'w') as f:
            f.write(new_content)
        print(f"Successfully added track_change method to Asset model at {model_file_path}")
        return True
    except Exception as e:
        print(f"Error writing to file: {str(e)}")
        return False

if __name__ == "__main__":
    success = update_asset_model()
    if success:
        print("Asset model successfully updated.")
    else:
        print("Failed to update Asset model.")
        sys.exit(1) 