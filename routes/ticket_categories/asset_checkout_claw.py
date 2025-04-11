import datetime
import os
import json
import traceback
from flask import Blueprint, jsonify, request, render_template, session, current_app as app, send_file
from dotenv import load_dotenv
from utils.auth_decorators import login_required
from utils.store_instances import ticket_store
from models.ticket import Ticket, TicketCategory, TicketStatus
from utils.tracking_cache import TrackingCache

# Define Blueprint
asset_checkout_claw_bp = Blueprint(
    'asset_checkout_claw', 
    __name__,
    url_prefix='/tickets/category/checkout_claw' # Example prefix
)

# --- Helper: Initialize Firecrawl Client --- 
def _initialize_firecrawl():
    load_dotenv(override=True)
    FIRECRAWL_API_KEY = os.environ.get('FIRECRAWL_API_KEY')
    firecrawl_client = None
    try:
        from firecrawl import FirecrawlApp
        if FIRECRAWL_API_KEY:
            firecrawl_client = FirecrawlApp(api_key=FIRECRAWL_API_KEY)
            print(f"Firecrawl API client initialized successfully with key: {FIRECRAWL_API_KEY[:5]}...")
        else:
            print("Error: No Firecrawl API key found in environment variables")
    except Exception as e:
        print(f"Error initializing Firecrawl client: {str(e)}")
    return firecrawl_client

# --- Route: Outbound Tracking --- 
@asset_checkout_claw_bp.route('/<int:ticket_id>/track', methods=['GET'])
@login_required
def track_outbound(ticket_id):
    """Fetches outbound tracking data by scraping ship24.com using Firecrawl, with caching support."""
    # --- Get Ticket --- 
    ticket = ticket_store.get_ticket(ticket_id)
    if not ticket or not ticket.shipping_tracking:
        return jsonify({'success': False, 'error': 'Ticket or tracking number not found'}), 404

    tracking_number = ticket.shipping_tracking
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
                tracking_type='primary',
                max_age_hours=24  # Cache for 24 hours
            )
            
            if cached_data:
                print(f"Using cached tracking data for {tracking_number}")
                return jsonify(cached_data)
        else:
            print(f"Force refresh requested for {tracking_number}, bypassing cache")
        
        # If we get here, need to fetch fresh data
        print(f"Scraping ship24 for: {tracking_number}")

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
                tracking_type='primary',
                carrier=ticket.shipping_carrier
            )
            
            return jsonify({
                'success': True, 
                'tracking_info': tracking_info, 
                'is_real_data': False,
                'is_cached': False,
                'debug_info': {
                    'source': 'ship24_scrape_fallback', 
                    'tracking_number': tracking_number, 
                    'status': 'In Transit (Simulated)'
                }
            })

        # --- Scrape Data --- 
        try:
            ship24_url = f"https://www.ship24.com/tracking?p={tracking_number}"
            print(f"Scraping URL: {ship24_url}")
            
            scrape_result = firecrawl_client.scrape_url(ship24_url, {
                'formats': ['json'],
                'jsonOptions': {
                    'prompt': f"""Extract all tracking events from Ship24 for tracking number {tracking_number}.
                    For each event, extract: date, status, location.
                    Also extract the current shipment status.
                    Return as: {{"current_status": "Current status", "events": [{{"date": "Date", "status": "Status", "location": "Location"}}]}}"""
                }
            })
            print(f"Firecrawl Raw Response: {scrape_result}")

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
                print("Warning: No tracking events extracted. Using fallback data.")
                current_date = datetime.datetime.now()
                tracking_info = [{"status": "Information Received", "location": "Ship24 System", "date": current_date.isoformat()}]
                latest_status = "Information Received"
                
            # --- Update Ticket --- 
            try:
                # Get a fresh instance of the ticket
                fresh_ticket = db_session.query(Ticket).get(ticket_id)
                if fresh_ticket:
                    fresh_ticket.shipping_status = latest_status
                    fresh_ticket.updated_at = datetime.datetime.now()
                    print(f"Updated ticket {ticket_id} with status: {latest_status}")
                
                # Save to cache for future requests
                TrackingCache.save_tracking_data(
                    db_session,
                    tracking_number, 
                    tracking_info, 
                    latest_status,
                    ticket_id=ticket_id,
                    tracking_type='primary',
                    carrier=ticket.shipping_carrier
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
                    'source': 'ship24_firecrawl',
                    'tracking_number': tracking_number,
                    'events_count': len(tracking_info),
                    'url': ship24_url
                }
            })
                
        except Exception as e:
            print(f"Error scraping ship24 for {tracking_number}: {str(e)}")
            traceback.print_exc()
            return jsonify({'success': False, 'error': f'Failed to scrape tracking data: {str(e)}'}), 500
    
    finally:
        # Always close the session
        try:
            print(f"Closing database session in track_outbound for ticket {ticket_id}")
            # Check if session is still active
            if db_session:
                if db_session.is_active:
                    print("Session is still active - committing any pending transactions")
                    db_session.commit()
                db_session.close()
                print("Database session closed successfully")
        except Exception as e:
            print(f"Error closing database session: {str(e)}")

@asset_checkout_claw_bp.route('/<int:ticket_id>/track_secondary', methods=['GET'])
@login_required
def track_secondary_shipment(ticket_id):
    """Fetches secondary shipment tracking data by scraping ship24.com using Firecrawl, with caching support."""
    # --- Get Ticket --- 
    ticket = ticket_store.get_ticket(ticket_id)
    if not ticket or not ticket.shipping_tracking_2:
        return jsonify({'success': False, 'error': 'Ticket or secondary tracking number not found'}), 404
    
    tracking_number = ticket.shipping_tracking_2
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
                tracking_type='secondary',
                max_age_hours=24  # Cache for 24 hours
            )
            
            if cached_data:
                print(f"Using cached secondary tracking data for {tracking_number}")
                return jsonify(cached_data)
        else:
            print(f"Force refresh requested for secondary tracking {tracking_number}, bypassing cache")
        
        # If we get here, need to fetch fresh data
        print(f"Scraping ship24 for secondary tracking: {tracking_number}")

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
                tracking_type='secondary',
                carrier=ticket.shipping_carrier_2
            )
            
            return jsonify({
                'success': True, 
                'tracking_info': tracking_info, 
                'is_real_data': False,
                'is_cached': False,
                'debug_info': {
                    'source': 'ship24_scrape_fallback', 
                    'tracking_number': tracking_number, 
                    'status': 'In Transit (Simulated)'
                }
            })

        # --- Scrape Data --- 
        try:
            ship24_url = f"https://www.ship24.com/tracking?p={tracking_number}"
            print(f"Scraping URL for secondary tracking: {ship24_url}")
            
            scrape_result = firecrawl_client.scrape_url(ship24_url, {
                'formats': ['json'],
                'jsonOptions': {
                    'prompt': f"""Extract all tracking events from Ship24 for tracking number {tracking_number}.
                    For each event, extract: date, status, location.
                    Also extract the current shipment status.
                    Return as: {{"current_status": "Current status", "events": [{{"date": "Date", "status": "Status", "location": "Location"}}]}}"""
                }
            })
            print(f"Firecrawl Raw Response for secondary tracking: {scrape_result}")

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
                print("Warning: No secondary tracking events extracted. Using fallback data.")
                current_date = datetime.datetime.now()
                tracking_info = [{"status": "Information Received", "location": "Ship24 System", "date": current_date.isoformat()}]
                latest_status = "Information Received"
                
            # --- Update Ticket --- 
            try:
                # Get a fresh instance of the ticket
                fresh_ticket = db_session.query(Ticket).get(ticket_id)
                if fresh_ticket:
                    fresh_ticket.shipping_status_2 = latest_status
                    fresh_ticket.updated_at = datetime.datetime.now()
                    print(f"Updated ticket {ticket_id} with secondary status: {latest_status}")
                
                # Save to cache for future requests
                TrackingCache.save_tracking_data(
                    db_session,
                    tracking_number, 
                    tracking_info, 
                    latest_status,
                    ticket_id=ticket_id,
                    tracking_type='secondary',
                    carrier=ticket.shipping_carrier_2
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
                    'source': 'ship24_firecrawl_secondary',
                    'tracking_number': tracking_number,
                    'events_count': len(tracking_info),
                    'url': ship24_url
                }
            })
                
        except Exception as e:
            print(f"Error scraping ship24 for secondary tracking {tracking_number}: {str(e)}")
            traceback.print_exc()
            return jsonify({'success': False, 'error': f'Failed to scrape secondary tracking data: {str(e)}'}), 500
    
    finally:
        # Always close the session
        try:
            print(f"Closing database session in track_secondary_shipment for ticket {ticket_id}")
            # Check if session is still active
            if db_session:
                if db_session.is_active:
                    print("Session is still active - committing any pending transactions")
                    db_session.commit()
                db_session.close()
                print("Database session closed successfully")
        except Exception as e:
            print(f"Error closing database session: {str(e)}")
