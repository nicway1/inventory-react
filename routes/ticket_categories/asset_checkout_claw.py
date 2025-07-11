import datetime
import os
import json
import traceback
from flask import Blueprint, jsonify, request, render_template, session, current_app as app, send_file
from dotenv import load_dotenv
from utils.auth_decorators import login_required
from utils.store_instances import ticket_store, firecrawl_client
from models.ticket import Ticket, TicketCategory, TicketStatus
from utils.tracking_cache import TrackingCache
import logging

# Set up logging for this module
logger = logging.getLogger(__name__)


# Define Blueprint
asset_checkout_claw_bp = Bluelogger.info(
    'asset_checkout_claw', 
    __name__,
    url_prefix='/tickets/category/checkout_claw' # Example prefix
)

# --- Helper: Initialize Firecrawl Client --- 
def _initialize_firecrawl():
    # Use the centralized FirecrawlClient that automatically gets the active key from database
    
    if firecrawl_client:
        logger.info("Using centralized Firecrawl client with active database key")
        return firecrawl_client
    else:
        logger.info("Error: Centralized Firecrawl client not available")
        return None

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
                logger.info("Using cached tracking data for {tracking_number}")
                return jsonify(cached_data)
        else:
            logger.info("Force refresh requested for {tracking_number}, bypassing cache")
        
        # If we get here, need to fetch fresh data
        logger.info("Scraping ship24 for: {tracking_number}")

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
            logger.info("Scraping URL: {ship24_url}")
            
            scrape_result = firecrawl_client.scrape_url(ship24_url, {
                'formats': ['json', 'markdown'],
                'jsonOptions': {
                    'prompt': f"""You are extracting tracking information from Ship24.com for tracking number {tracking_number}.

Look for tracking events and status information on the page. Each tracking event typically shows:
- A date/time (like "2025-01-15 10:30" or "Jan 15, 2025")
- A status message (like "Package delivered", "In transit", "Out for delivery")
- A location (like "Singapore Delivery Centre", "Regional Hub")

Extract ALL tracking events found on the page, starting with the most recent.

Also look for the current/latest status of the shipment.

If no tracking events are found, check if there's an error message or if the tracking number is invalid.

Return the data in this exact JSON format:
{{
    "current_status": "the most recent status (e.g., 'Out for delivery', 'Package delivered', 'In transit')",
    "events": [
        {{
            "date": "actual date from the page (e.g., '2025-01-15 10:30')",
            "status": "actual status text from the page (e.g., 'Package delivered')",
            "location": "actual location from the page (e.g., 'Singapore Delivery Centre')"
        }},
        {{
            "date": "next event date",
            "status": "next event status", 
            "location": "next event location"
        }}
    ]
}}

IMPORTANT: Only extract real data from the page. If no tracking information is found, return:
{{
    "current_status": "No tracking information found",
    "events": []
}}"""
                },
                'waitFor': 3000,  # Wait 3 seconds for dynamic content to load
                'timeout': 15000  # 15 second timeout
            })
            logger.info("Firecrawl Raw Response: {scrape_result}")

            # --- Process Result --- 
            tracking_info = []
            latest_status = "Unknown"
            
            # Check for the correct Firecrawl response structure
            if 'data' in scrape_result and 'json' in scrape_result['data'] and scrape_result['data']['json']:
                data = scrape_result['data']['json']
                latest_status = data.get('current_status', 'Unknown')
                events = data.get('events', [])
                logger.info("[DEBUG] Found {len(events)} tracking events")
                if events:
                    for event in events:
                        tracking_info.append({
                            'date': event.get('date', ''),
                            'status': event.get('status', ''),
                            'location': event.get('location', '')
                        })
                if not tracking_info and latest_status != "Unknown":
                    tracking_info.append({'date': datetime.datetime.now().isoformat(), 'status': latest_status, 'location': 'Ship24 System'})
                    
                logger.info("[DEBUG] Successfully extracted status: {latest_status}, events: {len(tracking_info)}")
            
            # Fallback: try old structure for backwards compatibility
            elif 'json' in scrape_result and scrape_result['json']:
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
                logger.info("Warning: No tracking events extracted. Using fallback data.")
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
                    logger.info("Updated ticket {ticket_id} with status: {latest_status}")
                
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
                logger.info("Warning: Could not update ticket or cache in database: {str(e)}")
            
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
            logger.info("Error scraping ship24 for {tracking_number}: {str(e)}")
            traceback.print_exc()
            return jsonify({'success': False, 'error': f'Failed to scrape tracking data: {str(e)}'}), 500
    
    finally:
        # Always close the session
        try:
            logger.info("Closing database session in track_outbound for ticket {ticket_id}")
            # Check if session is still active
            if db_session:
                if db_session.is_active:
                    logger.info("Session is still active - committing any pending transactions")
                    db_session.commit()
                db_session.close()
                logger.info("Database session closed successfully")
        except Exception as e:
            logger.info("Error closing database session: {str(e)}")

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
                logger.info("Using cached secondary tracking data for {tracking_number}")
                return jsonify(cached_data)
        else:
            logger.info("Force refresh requested for secondary tracking {tracking_number}, bypassing cache")
        
        # If we get here, need to fetch fresh data
        logger.info("Scraping ship24 for secondary tracking: {tracking_number}")

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
            logger.info("Scraping URL for secondary tracking: {ship24_url}")
            
            scrape_result = firecrawl_client.scrape_url(ship24_url, {
                'formats': ['json', 'markdown'],
                'jsonOptions': {
                    'prompt': f"""You are extracting tracking information from Ship24.com for tracking number {tracking_number}.

Look for tracking events and status information on the page. Each tracking event typically shows:
- A date/time (like "2025-01-15 10:30" or "Jan 15, 2025")
- A status message (like "Package delivered", "In transit", "Out for delivery")
- A location (like "Singapore Delivery Centre", "Regional Hub")

Extract ALL tracking events found on the page, starting with the most recent.

Also look for the current/latest status of the shipment.

If no tracking events are found, check if there's an error message or if the tracking number is invalid.

Return the data in this exact JSON format:
{{
    "current_status": "the most recent status (e.g., 'Out for delivery', 'Package delivered', 'In transit')",
    "events": [
        {{
            "date": "actual date from the page (e.g., '2025-01-15 10:30')",
            "status": "actual status text from the page (e.g., 'Package delivered')",
            "location": "actual location from the page (e.g., 'Singapore Delivery Centre')"
        }},
        {{
            "date": "next event date",
            "status": "next event status", 
            "location": "next event location"
        }}
    ]
}}

IMPORTANT: Only extract real data from the page. If no tracking information is found, return:
{{
    "current_status": "No tracking information found",
    "events": []
}}"""
                },
                'waitFor': 3000,  # Wait 3 seconds for dynamic content to load
                'timeout': 15000  # 15 second timeout
            })
            logger.info("Firecrawl Raw Response for secondary tracking: {scrape_result}")

            # --- Process Result --- 
            tracking_info = []
            latest_status = "Unknown"
            
            # Check for the correct Firecrawl response structure
            if 'data' in scrape_result and 'json' in scrape_result['data'] and scrape_result['data']['json']:
                data = scrape_result['data']['json']
                latest_status = data.get('current_status', 'Unknown')
                events = data.get('events', [])
                logger.info("[DEBUG] Found {len(events)} tracking events")
                if events:
                    for event in events:
                        tracking_info.append({
                            'date': event.get('date', ''),
                            'status': event.get('status', ''),
                            'location': event.get('location', '')
                        })
                if not tracking_info and latest_status != "Unknown":
                    tracking_info.append({'date': datetime.datetime.now().isoformat(), 'status': latest_status, 'location': 'Ship24 System'})
                    
                logger.info("[DEBUG] Successfully extracted status: {latest_status}, events: {len(tracking_info)}")
            
            # Fallback: try old structure for backwards compatibility
            elif 'json' in scrape_result and scrape_result['json']:
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
                logger.info("Warning: No tracking events extracted. Using fallback data.")
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
                    logger.info("Updated ticket {ticket_id} with secondary status: {latest_status}")
                
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
                logger.info("Warning: Could not update ticket or cache in database: {str(e)}")
            
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
            logger.info("Error scraping ship24 for secondary tracking {tracking_number}: {str(e)}")
            traceback.print_exc()
            return jsonify({'success': False, 'error': f'Failed to scrape secondary tracking data: {str(e)}'}), 500
    
    finally:
        # Always close the session
        try:
            logger.info("Closing database session in track_secondary_shipment for ticket {ticket_id}")
            # Check if session is still active
            if db_session:
                if db_session.is_active:
                    logger.info("Session is still active - committing any pending transactions")
                    db_session.commit()
                db_session.close()
                logger.info("Database session closed successfully")
        except Exception as e:
            logger.info("Error closing database session: {str(e)}")
