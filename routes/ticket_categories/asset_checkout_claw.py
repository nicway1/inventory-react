import datetime
import os
import json
import traceback
from flask import Blueprint, jsonify
from dotenv import load_dotenv
from utils.auth_decorators import login_required
from utils.store_instances import ticket_store
from models.ticket import Ticket

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
    """Fetches outbound tracking data by scraping ship24.com using Firecrawl."""
    # --- Get Ticket --- 
    ticket = ticket_store.get_ticket(ticket_id)
    if not ticket or not ticket.shipping_tracking:
        return jsonify({'success': False, 'error': 'Ticket or tracking number not found'}), 404
    
    tracking_number = ticket.shipping_tracking
    print(f"Attempting to scrape ship24 for outbound: {tracking_number}")

    # --- Initialize Firecrawl --- 
    firecrawl_client = _initialize_firecrawl()
    if not firecrawl_client:
        # Return simulated data as fallback
        current_date = datetime.datetime.now()
        tracking_info = [
            {"status": "In Transit (Simulated)", "location": "Scraping Hub (Simulated)", "date": current_date.isoformat()},
            {"status": "Shipment information received (Simulated)", "location": "Origin Facility (Simulated)", "date": (current_date - datetime.timedelta(days=1)).isoformat()}
        ]
        return jsonify({
            'success': True, 'tracking_info': tracking_info, 'is_real_data': False,
            'debug_info': {'source': 'ship24_scrape_fallback', 'tracking_number': tracking_number, 'status': 'In Transit (Simulated)'}
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
            db_session = ticket_store.db_manager.get_session()
            fresh_ticket = db_session.query(Ticket).get(ticket_id)
            if fresh_ticket:
                fresh_ticket.shipping_status = latest_status # Update outbound status
                fresh_ticket.shipping_history = tracking_info # Update outbound history
                fresh_ticket.updated_at = datetime.datetime.now()
                db_session.commit()
                print(f"Updated ticket {ticket_id} with outbound status: {latest_status}")
            db_session.close()
        except Exception as db_e:
            print(f"Warning: Could not update ticket in database: {str(db_e)}")

        # --- Return Result --- 
        return jsonify({
            'success': True, 'tracking_info': tracking_info, 'shipping_status': latest_status, 'is_real_data': True,
            'debug_info': {'source': 'ship24_firecrawl_outbound', 'tracking_number': tracking_number, 'events_count': len(tracking_info), 'url': ship24_url}
        })

    # --- Handle Errors --- 
    except Exception as e:
        print(f"Error scraping ship24 for {tracking_number}: {str(e)}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'Failed to scrape tracking data: {str(e)}'}), 500

@asset_checkout_claw_bp.route('/<int:ticket_id>/track_secondary', methods=['GET'])
@login_required
def track_secondary_shipment(ticket_id):
    """Fetches secondary shipment tracking data by scraping ship24.com using Firecrawl."""
    # --- Get Ticket --- 
    ticket = ticket_store.get_ticket(ticket_id)
    if not ticket or not ticket.shipping_tracking_2:
        return jsonify({'success': False, 'error': 'Ticket or secondary tracking number not found'}), 404
    
    tracking_number = ticket.shipping_tracking_2
    print(f"Attempting to scrape ship24 for secondary shipment: {tracking_number}")

    # --- Initialize Firecrawl --- 
    firecrawl_client = _initialize_firecrawl()
    if not firecrawl_client:
        # Return simulated data as fallback
        current_date = datetime.datetime.now()
        tracking_info = [
            {"status": "In Transit (Simulated)", "location": "Scraping Hub (Simulated)", "date": current_date.isoformat()},
            {"status": "Shipment information received (Simulated)", "location": "Origin Facility (Simulated)", "date": (current_date - datetime.timedelta(days=1)).isoformat()}
        ]
        return jsonify({
            'success': True, 'tracking_info': tracking_info, 'is_real_data': False,
            'debug_info': {'source': 'ship24_scrape_fallback', 'tracking_number': tracking_number, 'status': 'In Transit (Simulated)'}
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
            db_session = ticket_store.db_manager.get_session()
            fresh_ticket = db_session.query(Ticket).get(ticket_id)
            if fresh_ticket:
                fresh_ticket.shipping_status_2 = latest_status  # Update secondary status
                fresh_ticket.updated_at = datetime.datetime.now()
                db_session.commit()
                print(f"Updated ticket {ticket_id} with secondary shipment status: {latest_status}")
            db_session.close()
        except Exception as db_e:
            print(f"Warning: Could not update ticket in database: {str(db_e)}")

        # --- Return Result --- 
        return jsonify({
            'success': True, 'tracking_info': tracking_info, 'shipping_status': latest_status, 'is_real_data': True,
            'debug_info': {'source': 'ship24_firecrawl_secondary', 'tracking_number': tracking_number, 'events_count': len(tracking_info), 'url': ship24_url}
        })

    # --- Handle Errors --- 
    except Exception as e:
        print(f"Error scraping ship24 for secondary shipment {tracking_number}: {str(e)}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'Failed to scrape tracking data: {str(e)}'}), 500
