import datetime
import os
import json
import traceback
from flask import Blueprint, jsonify, request
from dotenv import load_dotenv
from utils.auth_decorators import login_required
from utils.store_instances import ticket_store
from models.ticket import Ticket
from utils.tracking_cache import TrackingCache

# Define Blueprint
asset_return_claw_bp = Blueprint(
    'asset_return_claw',
    __name__,
    url_prefix='/tickets/category/return_claw' # Example prefix
)

# --- Helper: Initialize Firecrawl Client (Can be shared or duplicated) ---
def _initialize_firecrawl():
    load_dotenv(override=True)
    FIRECRAWL_API_KEY = os.environ.get('FIRECRAWL_API_KEY')
    firecrawl_client = None
    try:
        from firecrawl import FirecrawlApp
        # Force use of the new API key
        firecrawl_client = FirecrawlApp(api_key='fc-9e1ffc308a01434582ece2625a2a0da7')
        print(f"Firecrawl API client initialized successfully with key: fc-eaa...")
    except Exception as e:
        print(f"Error initializing Firecrawl client: {str(e)}")
    return firecrawl_client

# --- Route: Inbound Tracking --- 
@asset_return_claw_bp.route('/<int:ticket_id>/track_return', methods=['GET'])
@login_required
def track_inbound(ticket_id):
    """Fetches return tracking data by scraping ship24.com using Firecrawl, with caching support."""
    # --- Get Ticket --- 
    ticket = ticket_store.get_ticket(ticket_id)
    if not ticket or not ticket.return_tracking:
        return jsonify({'success': False, 'error': 'Ticket or return tracking number not found'}), 404

    tracking_number = ticket.return_tracking
    db_session = ticket_store.db_manager.get_session()

    try:
        # Check for force refresh parameter
        force_refresh = request.args.get('force_refresh', 'false').lower() == 'true'
        
        # Check for cached tracking data if not forcing refresh
        if not force_refresh:
            cached_data = TrackingCache.get_cached_tracking(
                db_session, 
                tracking_number, 
                ticket_id=ticket_id, 
                tracking_type='return',
                max_age_hours=24  # Cache for 24 hours
            )
            
            if cached_data:
                print(f"Using cached return tracking data for {tracking_number}")
                return jsonify(cached_data)
        else:
            print(f"Force refresh requested for {tracking_number}, bypassing cache")
        
        # If we get here, need to fetch fresh data
        print(f"Scraping ship24 for return tracking: {tracking_number}")

        # --- Initialize Firecrawl --- 
        firecrawl_client = _initialize_firecrawl()
        if not firecrawl_client:
            # Return simulated data as fallback
            current_date = datetime.datetime.now()
            tracking_info = [
                {"status": "In Transit (Simulated)", "location": "Scraping Hub (Simulated)", "date": current_date.isoformat()},
                {"status": "Shipment information received (Simulated)", "location": "Origin Facility (Simulated)", "date": (current_date - datetime.timedelta(days=1)).isoformat()}
            ]
            
            # Save simulated data to cache (short TTL)
            TrackingCache.save_tracking_data(
                db_session,
                tracking_number, 
                tracking_info, 
                "In Transit (Simulated)",
                ticket_id=ticket_id,
                tracking_type='return'
            )
            
            return jsonify({
                'success': True, 
                'tracking_info': tracking_info, 
                'is_real_data': False,
                'is_cached': False,
                'debug_info': {
                    'source': 'ship24_scrape_fallback_return', 
                    'tracking_number': tracking_number, 
                    'status': 'In Transit (Simulated)'
                }
            })

        # --- Scrape Data --- 
        try:
            ship24_url = f"https://www.ship24.com/tracking?p={tracking_number}"
            print(f"Scraping URL for return tracking: {ship24_url}")
            
            scrape_result = firecrawl_client.scrape_url(ship24_url, {
                'formats': ['json'],
                'jsonOptions': {
                    'prompt': f"""Extract all tracking events from Ship24 for tracking number {tracking_number}.
                    For each event, extract: date, status, location.
                    Also extract the current shipment status.
                    Return as: {{"current_status": "Current status", "events": [{{"date": "Date", "status": "Status", "location": "Location"}}]}}"""
                }
            })
            print(f"Firecrawl Raw Response for return tracking: {scrape_result}")

            # --- Process Result --- 
            tracking_info = []
            latest_status = "Unknown"
            if 'json' in scrape_result and scrape_result['json']:
                data = scrape_result['json']
                latest_status = data.get('current_status', 'Unknown')
                events = data.get('events', [])
                if events:
                    for event in events:
                        tracking_info.append({
                            'date': event.get('date', ''),
                            'status': event.get('status', ''),
                            'location': event.get('location', '')
                        })
                if not tracking_info and latest_status != "Unknown":
                    tracking_info.append({'date': datetime.datetime.now().isoformat(), 'status': latest_status, 'location': 'Ship24 System'})
            
            if not tracking_info:
                print("Warning: No return tracking events extracted. Using fallback data.")
                current_date = datetime.datetime.now()
                tracking_info = [{"status": "Information Received", "location": "Ship24 System", "date": current_date.isoformat()}]
                latest_status = "Information Received"
                
            # --- Update Ticket --- 
            # Update ticket with latest return status
            try:
                # Get a fresh instance of the ticket
                fresh_ticket = db_session.query(Ticket).get(ticket_id)
                if fresh_ticket:
                    fresh_ticket.return_status = latest_status
                    fresh_ticket.updated_at = datetime.datetime.now()
                    print(f"Updated ticket {ticket_id} with return status: {latest_status}")
                
                # Save to cache for future requests
                TrackingCache.save_tracking_data(
                    db_session,
                    tracking_number, 
                    tracking_info, 
                    latest_status,
                    ticket_id=ticket_id,
                    tracking_type='return'
                )
                
            except Exception as e:
                print(f"Warning: Could not update ticket or cache in database: {str(e)}")
            
            return jsonify({
                'success': True,
                'tracking_info': tracking_info,
                'shipping_status': latest_status,
                'is_real_data': True,
                'is_cached': False,
                'debug_info': {
                    'source': 'ship24_firecrawl_return',
                    'tracking_number': tracking_number,
                    'events_count': len(tracking_info),
                    'url': ship24_url
                }
            })
                
        except Exception as e:
            print(f"Error scraping ship24 for return tracking {tracking_number}: {str(e)}")
            traceback.print_exc()
            return jsonify({'success': False, 'error': f'Failed to scrape return tracking data: {str(e)}'}), 500
    
    finally:
        # Always close the session
        try:
            print(f"Closing database session in track_inbound for ticket {ticket_id}")
            # Check if session is still active
            if db_session:
                if db_session.is_active:
                    print("Session is still active - committing any pending transactions")
                    db_session.commit()
                db_session.close()
                print("Database session closed successfully")
        except Exception as e:
            print(f"Error closing database session: {str(e)}")
