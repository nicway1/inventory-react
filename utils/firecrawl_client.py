import requests
import os
from config import FIRECRAWL_API_KEY
from dotenv import load_dotenv
from datetime import datetime

class FirecrawlClient:
    def __init__(self, api_key=None):
        # Force reload environment variables
        load_dotenv(override=True)
        
        # Try to get the active key from database first, then environment
        self.api_key = api_key or self._get_active_api_key() or os.environ.get('FIRECRAWL_API_KEY') or 'fc-9e1ffc308a01434582ece2625a2a0da7'
        
        if not self.api_key:
            raise ValueError("Firecrawl API key not configured")
        
        print(f"FirecrawlClient initialized with API key: {self.api_key[:5]}...")
        self.base_url = "https://api.firecrawl.dev/v1"
        
    def _get_active_api_key(self):
        """Get the active API key from the database"""
        try:
            from database import SessionLocal
            from models.firecrawl_key import FirecrawlKey
            
            session = SessionLocal()
            try:
                # Get the primary active key
                active_key = session.query(FirecrawlKey).filter_by(is_primary=True, is_active=True).first()
                if active_key:
                    print(f"Using active database API key: {active_key.name}")
                    return active_key.api_key
                
                # If no primary, get any active key
                active_key = session.query(FirecrawlKey).filter_by(is_active=True).first()
                if active_key:
                    print(f"Using fallback database API key: {active_key.name}")
                    return active_key.api_key
                    
            finally:
                session.close()
        except Exception as e:
            print(f"Error getting active API key from database: {str(e)}")
        
        return None
    
    def get_current_api_key(self):
        """Get the current API key (may refresh from database)"""
        # Refresh key from database if needed
        db_key = self._get_active_api_key()
        if db_key and db_key != self.api_key:
            print(f"API key updated from database: {db_key[:5]}...")
            self.api_key = db_key
        return self.api_key
    
    def scrape_url(self, url, options=None):
        """
        Scrape a URL using the Firecrawl API
        
        Args:
            url (str): The URL to scrape
            options (dict): Optional parameters for scraping
            
        Returns:
            dict: The scraped data
        """
        # Refresh API key from database before making request
        current_key = self.get_current_api_key()
        
        headers = {
            "Authorization": f"Bearer {current_key}",
            "Content-Type": "application/json"
        }
        
        endpoint = f"{self.base_url}/scrape"
        payload = {
            "url": url
        }
        
        # Add options if provided
        if options:
            payload.update(options)
        
        try:
            print(f"Making Firecrawl API request to: {endpoint}")
            print(f"Payload: {payload}")
            print(f"Using API key: {current_key[:10]}...")
            
            response = requests.post(endpoint, headers=headers, json=payload)
            response.raise_for_status()
            
            result = response.json()
            print(f"Firecrawl API response status: {response.status_code}")
            return result
            
        except requests.exceptions.RequestException as e:
            print(f"Error calling Firecrawl API: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response status: {e.response.status_code}")
                print(f"Response text: {e.response.text}")
            raise
    
    def scrape_ship24(self, tracking_number):
        """
        Scrape tracking information from Ship24 using Firecrawl API
        
        Args:
            tracking_number (str): The tracking number to search for
            
        Returns:
            dict: Tracking information with events and current status
        """
        try:
            # Construct Ship24 URL
            ship24_url = f"https://www.ship24.com/tracking?p={tracking_number}"
            
            # Use scrape_url with JSON extraction
            options = {
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
            }
            
            result = self.scrape_url(ship24_url, options)
            print(f"[DEBUG] Raw Firecrawl result: {result}")
            
            # Process the result to match expected format
            if result and 'data' in result and result['data']:
                data = result['data']
                
                # Check if we have JSON extraction
                if 'json' in data and data['json']:
                    json_data = data['json']
                    print(f"[DEBUG] Extracted JSON data: {json_data}")
                    
                    return {
                        "success": True,
                        "is_real_data": True,
                        "current_status": json_data.get('current_status', 'Unknown'),
                        "events": json_data.get('events', [])
                    }
                
                # Fallback to parsing markdown if no JSON
                elif 'markdown' in data and data['markdown']:
                    markdown = data['markdown']
                    print(f"[DEBUG] Received markdown content: {markdown[:500]}...")
                    
                    # Try to extract tracking info from markdown
                    tracking_events = self._parse_ship24_markdown(markdown, tracking_number)
                    if tracking_events:
                        return {
                            "success": True,
                            "is_real_data": True,
                            "current_status": tracking_events[0].get('status', 'Unknown'),
                            "events": tracking_events
                        }
            
            # If we get here, extraction failed
            print(f"[DEBUG] No valid tracking data extracted from Firecrawl result")
            return self._generate_mock_tracking_data(tracking_number)
                
        except Exception as e:
            print(f"Error scraping Ship24 for {tracking_number}: {str(e)}")
            # Return mock data as fallback
            return self._generate_mock_tracking_data(tracking_number)
    
    def _parse_ship24_markdown(self, markdown, tracking_number):
        """
        Parse Ship24 markdown content to extract tracking events
        """
        import re
        from datetime import datetime
        
        events = []
        
        # Look for tracking status patterns in markdown
        status_patterns = [
            r'Status[:\s]+([^\n]+)',
            r'Current status[:\s]+([^\n]+)',
            r'Shipment status[:\s]+([^\n]+)',
        ]
        
        for pattern in status_patterns:
            match = re.search(pattern, markdown, re.IGNORECASE)
            if match:
                status = match.group(1).strip()
                events.append({
                    "status": status,
                    "location": "Ship24",
                    "date": datetime.now().isoformat(),
                    "timestamp": datetime.now().isoformat()
                })
                break
        
        # If no specific status found, look for general tracking info
        if not events:
            # Look for tracking number in content
            if tracking_number.lower() in markdown.lower():
                # If tracking number is found, assume it's at least being tracked
                events.append({
                    "status": "Tracking information available",
                    "location": "Ship24 System",
                    "date": datetime.now().isoformat(),
                    "timestamp": datetime.now().isoformat()
                })
            else:
                # If tracking number not found, might be invalid
                events.append({
                    "status": "Tracking number not found",
                    "location": "Ship24 System",
                    "date": datetime.now().isoformat(),
                    "timestamp": datetime.now().isoformat()
                })
        
        return events
    
    def _generate_mock_tracking_data(self, tracking_number):
        """DISABLED: Mock data generation is disabled"""
        print(f"[ERROR] Mock data generation disabled for {tracking_number}")
        return {
            'success': False,
            'error': 'Mock data generation is disabled',
            'tracking_info': [],
            'debug_info': {'reason': 'Mock data generation disabled by user request'}
        }
        current_time = datetime.now().isoformat()
        mock_response = {
            "success": True,
            "is_real_data": False,
            "events": [
                {
                    "timestamp": current_time,
                    "date": current_time,
                    "status": "Mock Data - API Unreachable",
                    "location": "System"
                }
            ],
            "current_status": "API Unreachable - Using Mock Data"
        }
        print(f"API unavailable, returning mock data for {tracking_number}")
        return mock_response 