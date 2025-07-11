#!/usr/bin/env python
"""
Script to add missing track_change methods to models
"""
import os
import sys
import inspect
from datetime import datetime
import importlib

def add_track_change_to_models():
    logger.info("Adding missing track_change methods to models...")
    
    # Add the project directory to Python path
    sys.path.insert(0, '/home/nicway2/inventory')
    
    try:
        # Import models
        from models.asset import Asset
        from models.accessory import Accessory
        from models.asset_history import AssetHistory
        from models.accessory_history import AccessoryHistory
        
        # Check if Asset has track_change method
        if not hasattr(Asset, 'track_change') or not callable(getattr(Asset, 'track_change')):
            logger.info("Adding track_change method to Asset class...")
            
            def asset_track_change(self, user_id, action, changes, notes=None):
                """Create a history entry for asset changes
                
                Args:
                    user_id: ID of the user who made the change
                    action: Description of the action (e.g., "UPDATE", "STATUS_CHANGE")
                    changes: Dictionary of changes in the format {field: {'old': old_value, 'new': new_value}}
                    notes: Any additional notes about the change
                    
                Returns:
                    AssetHistory object (not yet added to session)
                """
                return AssetHistory(
                    asset_id=self.id,
                    user_id=user_id,
                    action=action,
                    changes=changes,
                    notes=notes
                )
            
            # Add the method to the class
            Asset.track_change = asset_track_change
            logger.info("✓ Successfully added track_change method to Asset class")
        else:
            logger.info("✓ Asset class already has track_change method")
        
        # Check if Accessory has track_change method
        if not hasattr(Accessory, 'track_change') or not callable(getattr(Accessory, 'track_change')):
            logger.info("Adding track_change method to Accessory class...")
            
            def accessory_track_change(self, user_id, action, changes, notes=None):
                """Create a history entry for accessory changes
                
                Args:
                    user_id: ID of the user who made the change
                    action: Description of the action (e.g., "UPDATE", "STATUS_CHANGE")
                    changes: Dictionary of changes in the format {field: {'old': old_value, 'new': new_value}}
                    notes: Any additional notes about the change
                    
                Returns:
                    AccessoryHistory object (not yet added to session)
                """
                return AccessoryHistory(
                    accessory_id=self.id,
                    user_id=user_id,
                    action=action,
                    changes=changes,
                    notes=notes
                )
            
            # Add the method to the class
            Accessory.track_change = accessory_track_change
            logger.info("✓ Successfully added track_change method to Accessory class")
        else:
            logger.info("✓ Accessory class already has track_change method")
            
        logger.info("\nMethods added successfully. Please restart your application for changes to take effect.")
        
    except ImportError as e:
        logger.info("Error importing models: {str(e)}")
    except Exception as e:
        logger.info("Error adding methods: {str(e)}")

if __name__ == "__main__":
    add_track_change_to_models() 