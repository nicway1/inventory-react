#!/usr/bin/env python
"""
Script to clean up 'None → None' entries from asset history table
"""
import os
import sys
import json
from datetime import datetime

def clean_history_entries():
    print("Starting cleanup of None→None history entries...")
    
    # Add the project directory to Python path
    # Determine if we're running locally or on PythonAnywhere
    if os.path.exists('/home/nicway2/inventory'):
        sys.path.insert(0, '/home/nicway2/inventory')
        print("Running on PythonAnywhere environment")
    else:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        print("Running on local environment")
    
    try:
        # Import models and database
        from models.asset_history import AssetHistory
        from models.accessory_history import AccessoryHistory
        from utils.db_manager import DatabaseManager
        
        # Get DB session
        db_manager = DatabaseManager()
        db_session = db_manager.get_session()
        
        # Find asset history entries with None→None changes
        filtered_entries = []
        modified_entries = []
        total_entries = 0
        
        # Process asset history
        asset_history_entries = db_session.query(AssetHistory).all()
        print(f"Found {len(asset_history_entries)} asset history entries")
        total_entries += len(asset_history_entries)
        
        for entry in asset_history_entries:
            if not entry.changes:
                continue
                
            # Make a copy of the changes dictionary
            updated_changes = {}
            has_meaningful_changes = False
            
            # Go through each change and only keep non None→None changes
            for field, change in entry.changes.items():
                if isinstance(change, dict) and 'old' in change and 'new' in change:
                    if not (change['old'] is None and change['new'] is None):
                        updated_changes[field] = change
                        has_meaningful_changes = True
                else:
                    # Keep any non-standard change format
                    updated_changes[field] = change
                    has_meaningful_changes = True
            
            if not has_meaningful_changes:
                # If no meaningful changes, mark for filtering
                filtered_entries.append(entry.id)
            elif updated_changes != entry.changes:
                # If we removed some None→None pairs but kept others, update the entry
                entry.changes = updated_changes
                modified_entries.append(entry.id)
        
        # Process accessory history (similar logic)
        accessory_history_entries = db_session.query(AccessoryHistory).all()
        print(f"Found {len(accessory_history_entries)} accessory history entries")
        total_entries += len(accessory_history_entries)
        
        for entry in accessory_history_entries:
            if not entry.changes:
                continue
                
            updated_changes = {}
            has_meaningful_changes = False
            
            for field, change in entry.changes.items():
                if isinstance(change, dict) and 'old' in change and 'new' in change:
                    if not (change['old'] is None and change['new'] is None):
                        updated_changes[field] = change
                        has_meaningful_changes = True
                else:
                    updated_changes[field] = change
                    has_meaningful_changes = True
            
            if not has_meaningful_changes:
                filtered_entries.append(entry.id)
            elif updated_changes != entry.changes:
                entry.changes = updated_changes
                modified_entries.append(entry.id)
        
        # Apply changes
        if filtered_entries:
            print(f"Removing {len(filtered_entries)} entries with only None→None changes")
            for entry_id in filtered_entries:
                # Find entry in either table
                asset_entry = db_session.query(AssetHistory).filter(AssetHistory.id == entry_id).first()
                if asset_entry:
                    db_session.delete(asset_entry)
                else:
                    accessory_entry = db_session.query(AccessoryHistory).filter(AccessoryHistory.id == entry_id).first()
                    if accessory_entry:
                        db_session.delete(accessory_entry)
        
        if modified_entries:
            print(f"Updating {len(modified_entries)} entries to remove None→None changes")
        
        # Commit changes
        db_session.commit()
        print(f"Successfully processed {total_entries} history entries")
        print(f"  - Removed {len(filtered_entries)} entries with only None→None changes")
        print(f"  - Updated {len(modified_entries)} entries to remove None→None fields")
        
    except ImportError as e:
        print(f"Error importing required modules: {str(e)}")
        return False
    except Exception as e:
        print(f"Error during cleanup: {str(e)}")
        if 'db_session' in locals():
            db_session.rollback()
        return False
    finally:
        if 'db_session' in locals():
            db_session.close()
    
    return True

if __name__ == "__main__":
    clean_history_entries() 