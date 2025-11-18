"""
Ship24 Parcel Tracking Utility using Playwright
Scrapes tracking information from ship24.com
"""

import asyncio
from typing import Dict, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class Ship24Tracker:
    """Track parcels using Ship24.com via Playwright web scraping"""

    def __init__(self):
        self.base_url = "https://www.ship24.com/track"

    async def track_parcel(self, tracking_number: str, carrier: Optional[str] = None) -> Dict:
        """
        Track a parcel using Ship24.com

        Args:
            tracking_number: The tracking number to search for
            carrier: Optional carrier name (e.g., 'dhl', 'fedex', 'ups')

        Returns:
            Dictionary containing tracking information
        """
        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                # Launch browser in headless mode
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
                )
                page = await context.new_page()

                # Navigate to Ship24 tracking page
                await page.goto(self.base_url, wait_until='networkidle')

                # Find and fill the tracking input field
                tracking_input = await page.wait_for_selector('input[placeholder*="tracking"]', timeout=10000)
                await tracking_input.fill(tracking_number)

                # Click the track button
                track_button = await page.wait_for_selector('button:has-text("Track")', timeout=5000)
                await track_button.click()

                # Wait for results to load
                await page.wait_for_timeout(5000)  # Wait for dynamic content

                # Extract tracking information
                tracking_info = await self._extract_tracking_data(page)

                await browser.close()

                return {
                    'success': True,
                    'tracking_number': tracking_number,
                    'carrier': tracking_info.get('carrier', carrier or 'Unknown'),
                    'status': tracking_info.get('status', 'Unknown'),
                    'events': tracking_info.get('events', []),
                    'current_location': tracking_info.get('location', 'Unknown'),
                    'estimated_delivery': tracking_info.get('estimated_delivery'),
                    'last_updated': datetime.utcnow().isoformat()
                }

        except Exception as e:
            logger.error(f"Error tracking parcel {tracking_number}: {str(e)}")
            return {
                'success': False,
                'tracking_number': tracking_number,
                'error': str(e),
                'message': 'Failed to retrieve tracking information'
            }

    async def _extract_tracking_data(self, page) -> Dict:
        """
        Extract tracking data from the Ship24 results page

        Args:
            page: Playwright page object

        Returns:
            Dictionary with extracted tracking data
        """
        tracking_data = {
            'carrier': 'Unknown',
            'status': 'Unknown',
            'location': 'Unknown',
            'events': [],
            'estimated_delivery': None
        }

        try:
            # Extract carrier name
            try:
                carrier_element = await page.query_selector('[class*="carrier"]')
                if carrier_element:
                    tracking_data['carrier'] = await carrier_element.inner_text()
            except:
                pass

            # Extract current status
            try:
                status_element = await page.query_selector('[class*="status"]')
                if status_element:
                    tracking_data['status'] = await status_element.inner_text()
            except:
                pass

            # Extract tracking events/checkpoints
            try:
                event_elements = await page.query_selector_all('[class*="event"], [class*="checkpoint"]')
                events = []
                for event_elem in event_elements[:10]:  # Limit to 10 most recent events
                    event_text = await event_elem.inner_text()
                    if event_text:
                        events.append({
                            'description': event_text,
                            'timestamp': None  # Could parse timestamp if available
                        })
                tracking_data['events'] = events
            except:
                pass

            # Extract current location
            try:
                location_element = await page.query_selector('[class*="location"]')
                if location_element:
                    tracking_data['location'] = await location_element.inner_text()
            except:
                pass

            # Extract estimated delivery date
            try:
                delivery_element = await page.query_selector('[class*="delivery"], [class*="eta"]')
                if delivery_element:
                    tracking_data['estimated_delivery'] = await delivery_element.inner_text()
            except:
                pass

        except Exception as e:
            logger.error(f"Error extracting tracking data: {str(e)}")

        return tracking_data

    def track_parcel_sync(self, tracking_number: str, carrier: Optional[str] = None) -> Dict:
        """
        Synchronous wrapper for track_parcel

        Args:
            tracking_number: The tracking number to search for
            carrier: Optional carrier name

        Returns:
            Dictionary containing tracking information
        """
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self.track_parcel(tracking_number, carrier))
            loop.close()
            return result
        except Exception as e:
            logger.error(f"Error in sync track_parcel: {str(e)}")
            return {
                'success': False,
                'tracking_number': tracking_number,
                'error': str(e),
                'message': 'Failed to retrieve tracking information'
            }

    async def track_multiple_parcels(self, tracking_numbers: List[str]) -> List[Dict]:
        """
        Track multiple parcels concurrently

        Args:
            tracking_numbers: List of tracking numbers

        Returns:
            List of tracking information dictionaries
        """
        tasks = [self.track_parcel(tn) for tn in tracking_numbers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to error dictionaries
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    'success': False,
                    'tracking_number': tracking_numbers[i],
                    'error': str(result),
                    'message': 'Failed to retrieve tracking information'
                })
            else:
                processed_results.append(result)

        return processed_results


# Create a singleton instance
_tracker_instance = None

def get_tracker() -> Ship24Tracker:
    """Get or create Ship24Tracker singleton instance"""
    global _tracker_instance
    if _tracker_instance is None:
        _tracker_instance = Ship24Tracker()
    return _tracker_instance
