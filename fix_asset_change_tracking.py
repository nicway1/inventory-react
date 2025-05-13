#!/usr/bin/env python
"""
Script to fix asset change tracking logic to avoid recording non-changes
"""
import os
import sys
import re
from datetime import datetime

def fix_asset_edit_route():
    print("Fixing asset change tracking logic...")
    
    # Path to the routes file - use current directory for local development
    routes_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'routes', 'inventory.py')
    
    if not os.path.exists(routes_path):
        print(f"Error: Routes file not found at {routes_path}")
        return False
    
    # Read current file content
    with open(routes_path, 'r') as f:
        content = f.read()
    
    # Look for the specific pattern where the edit_asset route builds the changes dictionary
    pattern = re.compile(r'(# Track changes\s+changes = \{\}\s+for field in old_values[^\n]+\s+new_value = getattr\(asset, field\).*?db_session\.add\(history_entry\))', re.DOTALL)
    
    match = pattern.search(content)
    if not match:
        print("Could not locate the change tracking code in the edit_asset route.")
        return False
    
    # Extract the matched section
    old_code = match.group(1)
    
    # Create improved code that properly handles None values and empty changes
    new_code = """# Track changes
                changes = {}
                for field in old_values:
                    new_value = getattr(asset, field)
                    if isinstance(new_value, AssetStatus):
                        new_value = new_value.value
                    
                    # Only record changes where values are actually different
                    # and avoid tracking None → None changes
                    if old_values[field] != new_value and not (old_values[field] is None and new_value is None):
                        changes[field] = {
                            'old': old_values[field],
                            'new': new_value
                        }
                
                print(f"Changes detected: {changes}")  # Debug log
                
                if changes:
                    history_entry = asset.track_change(
                        user_id=current_user.id,
                        action='update',
                        changes=changes,
                        notes=f"Asset updated by {current_user.username}"
                    )
                    db_session.add(history_entry)"""
    
    # Replace the old code with the new code
    new_content = content.replace(old_code, new_code)
    
    # Create a backup of the original file
    backup_path = f"{routes_path}.bak.{datetime.now().strftime('%Y%m%d%H%M%S')}"
    with open(backup_path, 'w') as f:
        f.write(content)
    print(f"Created backup of original routes file at {backup_path}")
    
    # Write the updated content
    with open(routes_path, 'w') as f:
        f.write(new_content)
    
    print("Successfully fixed asset change tracking logic.")
    print("Please restart your application for changes to take effect.")
    return True

if __name__ == "__main__":
    fix_asset_edit_route() 