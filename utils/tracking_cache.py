import json
from datetime import datetime, timedelta
from models.tracking_history import TrackingHistory

class TrackingCache:
    """Utility class for managing tracking data caching"""
    
    @staticmethod
    def get_cached_tracking(db_session, tracking_number, ticket_id=None, tracking_type='primary', max_age_hours=24, force=False):
        """
        Get cached tracking data if available and not expired
        
        Args:
            db_session: SQLAlchemy database session
            tracking_number: The tracking number to look for
            ticket_id: Optional ticket ID to associate with the tracking
            tracking_type: Type of tracking (primary, secondary, return)
            max_age_hours: Maximum age of cached data in hours before considered stale
            force: If True, bypass cache completely and return None
            
        Returns:
            Dictionary with tracking data if available and fresh, None otherwise
        """
        # If force is True, bypass cache completely
        if force:
            print(f"Force refresh requested for {tracking_number}, bypassing cache")
            return None
            
        try:
            # Try to find existing tracking history for this tracking number
            if ticket_id:
                # First try to find by tracking number AND ticket ID
                tracking_history = db_session.query(TrackingHistory).filter(
                    TrackingHistory.tracking_number == tracking_number,
                    TrackingHistory.ticket_id == ticket_id,
                    TrackingHistory.tracking_type == tracking_type
                ).first()
            else:
                # Fall back to just tracking number (first match)
                tracking_history = db_session.query(TrackingHistory).filter(
                    TrackingHistory.tracking_number == tracking_number,
                    TrackingHistory.tracking_type == tracking_type
                ).first()
            
            # If tracking history exists and is not stale, return it
            if tracking_history and not tracking_history.is_stale(max_age_hours):
                print(f"Using cached tracking data for {tracking_number} (type: {tracking_type})")
                
                # If data is stored as JSON string, parse it
                if tracking_history.tracking_data:
                    try:
                        return {
                            'success': True, 
                            'tracking_info': json.loads(tracking_history.tracking_data),
                            'shipping_status': tracking_history.status,
                            'is_cached': True,
                            'last_updated': tracking_history.last_updated.isoformat(),
                            'is_real_data': True
                        }
                    except json.JSONDecodeError:
                        print(f"Error decoding cached tracking data for {tracking_number}")
            
            # If we got here, no valid cache was found
            return None
            
        except Exception as e:
            print(f"Error getting cached tracking for {tracking_number}: {str(e)}")
            return None
    
    @staticmethod
    def save_tracking_data(db_session, tracking_number, tracking_info, status, 
                           ticket_id=None, tracking_type='primary', carrier=None):
        """
        Save tracking data to cache
        
        Args:
            db_session: SQLAlchemy database session
            tracking_number: The tracking number
            tracking_info: List of tracking events
            status: Current tracking status
            ticket_id: Optional ticket ID to associate with the tracking
            tracking_type: Type of tracking (primary, secondary, return)
            carrier: Optional carrier code
            
        Returns:
            True if successful, False otherwise
        """
        try:
            print(f"Saving tracking data for {tracking_number} (type: {tracking_type})")
            print(f"- Ticket ID: {ticket_id}")
            print(f"- Status: {status}")
            print(f"- Events count: {len(tracking_info) if tracking_info else 0}")
            
            # Try to find existing tracking history for this tracking number
            if ticket_id:
                # First try to find by tracking number AND ticket ID
                tracking_history = db_session.query(TrackingHistory).filter(
                    TrackingHistory.tracking_number == tracking_number,
                    TrackingHistory.ticket_id == ticket_id,
                    TrackingHistory.tracking_type == tracking_type
                ).first()
                print(f"- Lookup by tracking number and ticket ID: {'Found' if tracking_history else 'Not found'}")
            else:
                # Fall back to just tracking number (first match)
                tracking_history = db_session.query(TrackingHistory).filter(
                    TrackingHistory.tracking_number == tracking_number,
                    TrackingHistory.tracking_type == tracking_type
                ).first()
                print(f"- Lookup by tracking number only: {'Found' if tracking_history else 'Not found'}")
            
            # If tracking history exists, update it
            if tracking_history:
                tracking_history.update(tracking_info, status, carrier)
                print(f"Updated tracking cache for {tracking_number} (type: {tracking_type})")
            else:
                # Create a new tracking history
                tracking_history = TrackingHistory(
                    tracking_number=tracking_number,
                    tracking_data=tracking_info,
                    status=status,
                    carrier=carrier,
                    ticket_id=ticket_id,
                    tracking_type=tracking_type
                )
                db_session.add(tracking_history)
                print(f"Created new tracking cache for {tracking_number} (type: {tracking_type})")
            
            # Make sure changes are flushed before commit
            db_session.flush()
            
            # Commit the changes
            db_session.commit()
            print(f"Successfully committed tracking data for {tracking_number}")
            return True
            
        except Exception as e:
            db_session.rollback()
            print(f"Error saving tracking cache for {tracking_number}: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
            
    @staticmethod
    def clear_cache(db_session, tracking_number=None, ticket_id=None, tracking_type=None):
        """
        Clear tracking cache entries
        
        Args:
            db_session: SQLAlchemy database session
            tracking_number: Optional tracking number to clear (if None, will use other filters)
            ticket_id: Optional ticket ID to clear (if None, will use other filters)
            tracking_type: Optional tracking type to clear (if None, will clear all types)
            
        Returns:
            Number of entries cleared
        """
        try:
            # Build query
            query = db_session.query(TrackingHistory)
            
            # Apply filters if provided
            if tracking_number:
                query = query.filter(TrackingHistory.tracking_number == tracking_number)
            if ticket_id:
                query = query.filter(TrackingHistory.ticket_id == ticket_id)
            if tracking_type:
                query = query.filter(TrackingHistory.tracking_type == tracking_type)
                
            # If no filters provided, don't delete anything (safety measure)
            if not tracking_number and not ticket_id and not tracking_type:
                print("Warning: No filters provided for clear_cache. For safety, refusing to clear all cache entries.")
                return 0
                
            # Delete matching entries
            count = query.delete()
            db_session.commit()
            print(f"Cleared {count} tracking cache entries")
            return count
            
        except Exception as e:
            db_session.rollback()
            print(f"Error clearing tracking cache: {str(e)}")
            return 0 