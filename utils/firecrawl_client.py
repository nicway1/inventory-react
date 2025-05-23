import requests
import os
from config import FIRECRAWL_API_KEY
from dotenv import load_dotenv
from datetime import datetime

class FirecrawlClient:
    def __init__(self, api_key=None):
        # Force reload environment variables
        load_dotenv(override=True)
        
        # Use provided API key or get from environment
        self.api_key = api_key or os.environ.get('FIRECRAWL_API_KEY') or 'fc-9e1ffc308a01434582ece2625a2a0da7'
        
        if not self.api_key:
            raise ValueError("Firecrawl API key not configured")
        
        print(f"FirecrawlClient initialized with API key: {self.api_key[:5]}...")
        self.base_url = "https://api.firecrawl.dev/v1"
        
    def scrape_url(self, url, options=None):
        """
        Scrape a URL using the Firecrawl API
        
        Args:
            url (str): The URL to scrape
            options (dict): Optional parameters for scraping
            
        Returns:
            dict: The scraped data
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
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
                'formats': ['json'],
                'jsonOptions': {
                    'prompt': f"""Extract all tracking events from Ship24 for tracking number {tracking_number}.
                    For each event, extract: date, status, location.
                    Also extract the current shipment status.
                    Return as: {{"current_status": "Current status", "events": [{{"date": "Date", "status": "Status", "location": "Location"}}]}}"""
                }
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
        """Generate mock tracking data when API is unavailable"""
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