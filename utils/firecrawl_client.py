import requests
import os
from config import FIRECRAWL_API_KEY
from dotenv import load_dotenv

class FirecrawlClient:
    def __init__(self, api_key=None):
        # Force reload environment variables
        load_dotenv(override=True)
        
        # Use provided API key or get from freshly loaded environment
        self.api_key = api_key or os.environ.get('FIRECRAWL_API_KEY') or FIRECRAWL_API_KEY
        
        if not self.api_key:
            raise ValueError("Firecrawl API key not configured")
        
        print(f"FirecrawlClient initialized with API key: {self.api_key[:5]}...")
        self.base_url = "https://api.firecrawl.com/v1"
        
    def scrape_ship24(self, tracking_number):
        """
        Scrape tracking information from Ship24 using Firecrawl API
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        endpoint = f"{self.base_url}/scrape/ship24"
        payload = {
            "tracking_number": tracking_number
        }
        
        try:
            response = requests.post(endpoint, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error scraping Ship24: {str(e)}")
            return None 