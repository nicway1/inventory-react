"""
Ship24 Parcel Tracking Utility
Scrapes tracking information from ship24.com using Playwright when available,
falls back to providing tracking links when Playwright is not installed.

Supports PythonAnywhere deployment with pre-installed Chromium.
"""

import asyncio
import os
from typing import Dict, List, Optional
from datetime import datetime
import logging
import re

logger = logging.getLogger(__name__)

# Check if Playwright is available
PLAYWRIGHT_AVAILABLE = False
try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    logger.warning("Playwright not available - tracking will use fallback mode with tracking links")


def is_pythonanywhere() -> bool:
    """Check if running on PythonAnywhere"""
    # PythonAnywhere sets specific environment variables
    return os.path.exists('/usr/bin/chromium') and (
        'PYTHONANYWHERE_SITE' in os.environ or
        'pythonanywhere' in os.environ.get('HOME', '').lower() or
        os.path.exists('/home/.pythonanywhere')
    )


def get_proxy_config() -> Optional[Dict]:
    """Get proxy configuration from environment variable"""
    proxy_url = os.environ.get('TRACKING_PROXY_URL')
    if proxy_url:
        # Support format: http://user:pass@host:port or http://host:port
        return {'server': proxy_url}
    return None


def get_browser_launch_options() -> Dict:
    """Get browser launch options based on environment"""
    if is_pythonanywhere():
        # PythonAnywhere specific settings - use pre-installed Chromium
        return {
            'executable_path': '/usr/bin/chromium',
            'headless': True,
            'args': ['--disable-gpu', '--no-sandbox', '--headless']
        }
    else:
        # Local/other environment settings
        return {
            'headless': True,
            'args': ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
        }


class Ship24Tracker:
    """Track parcels using Ship24.com, 17track, and SingPost API via Playwright web scraping"""

    # SingPost UAT API Credentials
    SINGPOST_ACCOUNT_NO = "0056759L"
    SINGPOST_API_KEY_DEFAULT = "a59a2f41051b4b0a8a709eb4fd0330f9"
    SINGPOST_API_URL_UAT = "https://api.qa.singpost.com/sp/tracking"
    SINGPOST_API_URL_PROD = "https://api.singpost.com/sp/tracking"

    def __init__(self, singpost_api_key: Optional[str] = None, use_singpost_uat: bool = True):
        self.base_url = "https://www.ship24.com"
        self.track17_url = "https://t.17track.net"
        # SingPost API credentials
        self.singpost_api_key = singpost_api_key or self._get_singpost_api_key()
        # Use UAT by default for testing, set use_singpost_uat=False for production
        self.singpost_api_url = self.SINGPOST_API_URL_UAT if use_singpost_uat else self.SINGPOST_API_URL_PROD

    def _get_singpost_api_key(self) -> Optional[str]:
        """Get SingPost API key from environment or use default UAT key"""
        import os
        return os.environ.get('SINGPOST_API_KEY', self.SINGPOST_API_KEY_DEFAULT)

    async def track_with_singpost_api(self, tracking_number: str) -> Optional[Dict]:
        """
        Track a parcel using official SingPost API
        UAT credentials: Account 0056759L
        """
        if not self.singpost_api_key:
            return None

        try:
            import aiohttp

            headers = {
                'Authorization': self.singpost_api_key,
                'X-Account-No': self.SINGPOST_ACCOUNT_NO,
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }

            async with aiohttp.ClientSession() as session:
                # SingPost API - try with tracking number in path
                url = f"{self.singpost_api_url}/{tracking_number}"
                logger.info(f"Calling SingPost API for {tracking_number} at {url}")

                async with session.get(url, headers=headers, timeout=30) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"SingPost API response: {data}")

                        # Parse the API response
                        tracking_info = data.get('trackingInfo', {})
                        events = []

                        # Extract tracking events
                        for event in tracking_info.get('trackingEvents', []):
                            events.append({
                                'description': event.get('eventDescription', ''),
                                'timestamp': event.get('eventDateTime', ''),
                                'location': event.get('eventLocation', '')
                            })

                        status = tracking_info.get('currentStatus', 'Unknown')
                        if 'delivered' in status.lower():
                            status = 'Delivered'
                        elif 'transit' in status.lower():
                            status = 'In Transit'

                        return {
                            'success': True,
                            'tracking_number': tracking_number,
                            'carrier': 'Singapore Post',
                            'status': status,
                            'events': events,
                            'current_location': tracking_info.get('currentLocation', 'Unknown'),
                            'estimated_delivery': tracking_info.get('estimatedDelivery'),
                            'last_updated': datetime.utcnow().isoformat(),
                            'tracking_url': f'https://www.singpost.com/track-items',
                            'source': 'SingPost API'
                        }
                    elif response.status == 401:
                        logger.error("SingPost API: Invalid API key")
                    elif response.status == 404:
                        logger.info(f"SingPost API: Tracking number {tracking_number} not found")
                    else:
                        logger.error(f"SingPost API error: {response.status}")

        except ImportError:
            logger.warning("aiohttp not installed, SingPost API not available")
        except Exception as e:
            logger.error(f"SingPost API error: {str(e)}")

        return None

    async def track_parcel(self, tracking_number: str, carrier: Optional[str] = None) -> Dict:
        """
        Track a parcel using multiple sources with fallbacks

        Args:
            tracking_number: The tracking number to search for
            carrier: Optional carrier name

        Returns:
            Dictionary containing tracking information
        """
        tracking_url = f"{self.base_url}/tracking?p={tracking_number}"
        ship24_result = None

        # For HFD Israel tracking, try HFD scraper first
        if self._is_hfd_tracking(tracking_number):
            logger.info(f"Trying HFD scraper for {tracking_number}")
            result = await self.track_with_hfd(tracking_number)
            if result and result.get('status') not in ['Unknown', None, 'Check Links Below']:
                result['tracking_links'] = self._get_all_tracking_links(tracking_number)
                return result

        # For SingPost tracking numbers, try official API first if configured
        if self._is_singpost_tracking(tracking_number) and self.singpost_api_key:
            logger.info(f"Trying SingPost API for {tracking_number}")
            result = await self.track_with_singpost_api(tracking_number)
            if result:
                result['tracking_links'] = self._get_all_tracking_links(tracking_number)
                return result

        # If Playwright is not available OR running on PythonAnywhere without proxy, skip directly to fallback
        # PythonAnywhere's datacenter IPs are blocked by CloudFront/tracking sites
        proxy_config = get_proxy_config()
        if not PLAYWRIGHT_AVAILABLE or (is_pythonanywhere() and not proxy_config):
            reason = "PythonAnywhere without proxy (sites block datacenter IPs)" if is_pythonanywhere() else "Playwright not available"
            logger.info(f"Skipping scraping ({reason}), returning tracking links for {tracking_number}")
            detected_carrier = carrier or self._detect_carrier(tracking_number) or 'Unknown'
            return {
                'success': True,
                'tracking_number': tracking_number,
                'carrier': detected_carrier,
                'status': 'Check Links Below',
                'events': [],
                'current_location': detected_carrier if detected_carrier != 'Unknown' else 'Unknown',
                'estimated_delivery': None,
                'last_updated': datetime.utcnow().isoformat(),
                'tracking_url': tracking_url,
                'tracking_links': self._get_all_tracking_links(tracking_number),
                'message': 'Click tracking links below to check status on carrier website.',
                'source': 'fallback'
            }

        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                # Get browser launch options (PythonAnywhere compatible)
                launch_options = get_browser_launch_options()
                browser = await p.chromium.launch(**launch_options)

                # Build context options with optional proxy
                context_options = {
                    'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'viewport': {'width': 1920, 'height': 1080}
                }
                if proxy_config:
                    context_options['proxy'] = proxy_config
                    logger.info(f"Using proxy for Ship24: {proxy_config['server']}")

                context = await browser.new_context(**context_options)
                page = await context.new_page()

                logger.info(f"Navigating to Ship24: {tracking_url}")

                # Navigate to tracking page
                await page.goto(tracking_url, wait_until='domcontentloaded', timeout=30000)

                # Wait for page to fully load (Ship24 uses React and loads data dynamically)
                await page.wait_for_timeout(5000)

                # Try to wait for tracking content to appear
                try:
                    # Wait for any tracking-related content
                    await page.wait_for_selector('main, [class*="tracking"], [class*="result"], [class*="shipment"]', timeout=10000)
                except:
                    pass

                # Give more time for dynamic content
                await page.wait_for_timeout(3000)

                # Extract tracking information
                tracking_info = await self._extract_ship24_data(page, tracking_number)

                await browser.close()

                ship24_result = {
                    'success': True,
                    'tracking_number': tracking_number,
                    'carrier': tracking_info.get('carrier', carrier or 'Unknown'),
                    'status': tracking_info.get('status', 'Unknown'),
                    'events': tracking_info.get('events', []),
                    'current_location': tracking_info.get('location', 'Unknown'),
                    'estimated_delivery': tracking_info.get('estimated_delivery'),
                    'last_updated': datetime.utcnow().isoformat(),
                    'tracking_url': tracking_url,
                    'source': 'Ship24'
                }

                # If Ship24 returned good results, use them
                if ship24_result['status'] not in ['Unknown', 'No tracking information found']:
                    return ship24_result

        except Exception as e:
            logger.error(f"Error tracking parcel with Ship24 {tracking_number}: {str(e)}")

        # Try 17track as fallback
        logger.info(f"Trying 17track fallback for {tracking_number}")
        try:
            result_17track = await self.track_with_17track(tracking_number, carrier)
            if result_17track and result_17track.get('status') not in ['Unknown', None]:
                # Add tracking links to result
                result_17track['tracking_links'] = self._get_all_tracking_links(tracking_number)
                return result_17track
        except Exception as e:
            logger.error(f"17track fallback failed: {str(e)}")

        # Try TrackingMore as another fallback (especially good for SingPost)
        logger.info(f"Trying TrackingMore fallback for {tracking_number}")
        try:
            result_trackingmore = await self.track_with_trackingmore(tracking_number, carrier)
            if result_trackingmore and result_trackingmore.get('status') not in ['Unknown', None]:
                result_trackingmore['tracking_links'] = self._get_all_tracking_links(tracking_number)
                return result_trackingmore
        except Exception as e:
            logger.error(f"TrackingMore fallback failed: {str(e)}")

        # If all failed, return Ship24 result or fallback
        if ship24_result:
            ship24_result['tracking_links'] = self._get_all_tracking_links(tracking_number)
            return ship24_result

        # Final fallback - with carrier-specific messaging
        detected_carrier = carrier or self._detect_carrier(tracking_number) or 'Unknown'

        # Custom message for SingPost
        if self._is_singpost_tracking(tracking_number):
            message = 'SingPost tracking requires manual lookup. Use Tracking.my or SingPost app for best results.'
        else:
            message = 'Unable to fetch tracking data. Use tracking links to check manually.'

        return {
            'success': True,  # Return success with fallback
            'tracking_number': tracking_number,
            'carrier': detected_carrier,
            'status': 'Check Links Below',
            'events': [],
            'current_location': detected_carrier if detected_carrier != 'Unknown' else 'Unknown',
            'estimated_delivery': None,
            'last_updated': datetime.utcnow().isoformat(),
            'tracking_url': tracking_url,
            'tracking_links': self._get_all_tracking_links(tracking_number),
            'message': message,
            'source': 'fallback'
        }

    async def _extract_ship24_data(self, page, tracking_number: str) -> Dict:
        """Extract tracking data from Ship24 results page using text analysis"""
        tracking_data = {
            'carrier': 'Unknown',
            'status': 'Unknown',
            'location': 'Unknown',
            'events': [],
            'estimated_delivery': None
        }

        try:
            # Get full page text content
            page_text = await page.evaluate('() => document.body.innerText')
            lower_text = page_text.lower()

            logger.info(f"Ship24 page text length: {len(page_text)}")
            # Debug: Log first 500 chars to see what content we're getting
            logger.info(f"Ship24 page content preview: {page_text[:500] if page_text else 'EMPTY'}")

            # Check for "no tracking found" messages
            no_result_patterns = [
                'no tracking information',
                'no results found',
                'tracking number not found',
                'invalid tracking',
                'we couldn\'t find',
                'enter a tracking number'
            ]
            for pattern in no_result_patterns:
                if pattern in lower_text:
                    tracking_data['status'] = 'No tracking information found'
                    return tracking_data

            # Extract carrier name - Ship24 usually shows carrier prominently
            carriers_to_check = [
                'DHL Express', 'DHL', 'FedEx', 'UPS', 'USPS', 'TNT', 'Aramex',
                'Singapore Post', 'SingPost', 'China Post', 'EMS', 'Royal Mail',
                'Australia Post', 'Canada Post', 'Japan Post', 'Korea Post',
                'Yanwen', 'Cainiao', '4PX', 'YunExpress', 'SF Express',
                'Pos Malaysia', 'Thai Post', 'Vietnam Post', 'PostNL', 'Deutsche Post',
                'La Poste', 'Correos', 'CTT', 'Poste Italiane', 'Swiss Post'
            ]

            # Try to find carrier in page text
            for carrier in carriers_to_check:
                if carrier.lower() in lower_text:
                    tracking_data['carrier'] = carrier
                    break

            # Try to extract carrier from specific elements
            try:
                # Look for carrier logo alt text
                carrier_imgs = await page.query_selector_all('img[alt]')
                for img in carrier_imgs:
                    alt = await img.get_attribute('alt')
                    if alt:
                        for carrier in carriers_to_check:
                            if carrier.lower() in alt.lower():
                                tracking_data['carrier'] = carrier
                                break
            except:
                pass

            # Extract status - look for common status keywords
            status_mapping = {
                'delivered': 'Delivered',
                'in transit': 'In Transit',
                'out for delivery': 'Out for Delivery',
                'at customs': 'At Customs',
                'customs clearance': 'Customs Clearance',
                'arrived at': 'Arrived',
                'departed from': 'Departed',
                'picked up': 'Picked Up',
                'shipment information received': 'Info Received',
                'pending': 'Pending',
                'exception': 'Exception',
                'return': 'Return',
                'available for pickup': 'Ready for Pickup'
            }

            # Look for status in text
            for keyword, status in status_mapping.items():
                if keyword in lower_text:
                    tracking_data['status'] = status
                    break

            # If status still unknown, try to find it in structured elements
            if tracking_data['status'] == 'Unknown':
                try:
                    # Try various selectors for status
                    status_selectors = [
                        'h1', 'h2', 'h3',
                        '[class*="status"]',
                        '[class*="state"]',
                        '[class*="milestone"]'
                    ]
                    for selector in status_selectors:
                        elements = await page.query_selector_all(selector)
                        for elem in elements:
                            text = (await elem.inner_text()).lower()
                            for keyword, status in status_mapping.items():
                                if keyword in text:
                                    tracking_data['status'] = status
                                    break
                        if tracking_data['status'] != 'Unknown':
                            break
                except:
                    pass

            # Extract events from the page
            events = []

            # Since Ship24 is a React SPA that's hard to scrape reliably,
            # we'll focus on extracting just the key status info rather than
            # trying to get all tracking events (which often picks up UI elements)

            # For detailed tracking history, we'll direct users to the Ship24 link
            # This approach gives accurate status without garbage events

            # Only try to extract events if we can find proper date+location patterns
            date_location_pattern = re.compile(
                r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\w{3}\s+\d{1,2},?\s+\d{4})'  # Date
                r'.*?'  # Something in between
                r'(\d{1,2}:\d{2}(?:\s*[AP]M)?)?'  # Optional time
                r'.*?'  # Something in between
                r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?(?:,\s*[A-Z]{2,})?)',  # Location
                re.IGNORECASE | re.DOTALL
            )

            # Strict blocklist for UI elements - exact matches or very short phrases
            ui_element_phrases = [
                'remove selected', 'detailed view', 'select all', 'deselect all',
                'sort by', 'show more', 'load more', 'view all', 'see details',
                'click here', 'learn more', 'read more', 'see more',
                'track another', 'add tracking', 'new tracking',
                'out for delivery today', 'delivered today', 'arriving today',
                'filter by', 'group by', 'expand all', 'collapse all',
                'integration', 'seamless sync', 'cookie', 'privacy',
                'sign in', 'sign up', 'login', 'register', 'subscribe',
                'newsletter', 'help center', 'documentation', 'api',
                'pricing', 'features', 'solutions', 'enterprise',
                'about us', 'contact us', 'careers', 'terms', 'copyright'
            ]

            # Try to find actual tracking events with dates
            lines = page_text.split('\n')
            for line in lines:
                line = line.strip()

                # Skip very short or very long lines
                if len(line) < 25 or len(line) > 300:
                    continue

                lower_line = line.lower()

                # Skip if it's a UI element phrase
                if any(ui_phrase in lower_line for ui_phrase in ui_element_phrases):
                    continue

                # Skip lines that are just labels (no date/time info)
                if lower_line in ['delivered', 'in transit', 'out for delivery', 'pending', 'exception']:
                    continue

                # MUST have a date pattern to be considered an event
                has_date = bool(re.search(
                    r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|'  # MM/DD/YYYY or similar
                    r'\w{3}\s+\d{1,2},?\s+\d{4}|'  # Jan 15, 2024
                    r'\d{1,2}\s+\w{3}\s+\d{4}',  # 15 Jan 2024
                    line
                ))

                if not has_date:
                    continue

                # Should also have time or location indicator
                has_time = bool(re.search(r'\d{1,2}:\d{2}', line))
                has_location = bool(re.search(r'[A-Z][a-z]+,?\s+[A-Z]{2}|facility|center|hub|warehouse', line, re.IGNORECASE))
                has_action = bool(re.search(r'arrived|departed|delivered|transit|processed|cleared|received|dispatched|picked|scan', lower_line))

                if has_time or has_location or has_action:
                    clean_text = ' '.join(line.split())

                    # Check for duplicates
                    if clean_text not in [e['description'] for e in events]:
                        # Extract timestamp
                        timestamp = None
                        date_match = re.search(
                            r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}(?:\s*\d{1,2}:\d{2})?|'
                            r'\w{3}\s+\d{1,2},?\s+\d{4}(?:\s*\d{1,2}:\d{2})?)',
                            line
                        )
                        if date_match:
                            timestamp = date_match.group(1)

                        events.append({
                            'description': clean_text,
                            'timestamp': timestamp
                        })

                        # Limit events to avoid noise
                        if len(events) >= 10:
                            break

            tracking_data['events'] = events[:10]  # Limit to 10 events

            # Set location based on status if we couldn't find a specific location
            # If delivered, the "location" is essentially "Delivered"
            if tracking_data['status'] == 'Delivered':
                tracking_data['location'] = 'Delivered'
            elif tracking_data['status'] == 'In Transit':
                tracking_data['location'] = 'In Transit'
            elif tracking_data['status'] == 'Out for Delivery':
                tracking_data['location'] = 'Out for Delivery'
            elif tracking_data['status'] == 'At Customs':
                tracking_data['location'] = 'Customs'

            # Try to extract a more specific location from page content
            # Look for common location patterns
            location_patterns = [
                r'(?:delivered to|arrived at|in)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?(?:,\s*[A-Z]{2,})?)',
                r'([A-Z][a-z]+,\s*[A-Z]{2})',  # City, STATE format
                r'(?:destination|location)[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
            ]
            for pattern in location_patterns:
                match = re.search(pattern, page_text)
                if match:
                    found_location = match.group(1).strip()
                    # Make sure it's not a generic word
                    if found_location.lower() not in ['the', 'to', 'from', 'in', 'at', 'on', 'delivered', 'transit']:
                        tracking_data['location'] = found_location
                        break

            # Extract estimated delivery if available
            delivery_patterns = [
                r'deliver(?:y|ed)?\s*(?:by|on|date)?[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
                r'eta[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
                r'expected[:\s]+(\w+\s+\d{1,2},?\s+\d{4})'
            ]
            for pattern in delivery_patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    tracking_data['estimated_delivery'] = match.group(1)
                    break

        except Exception as e:
            logger.error(f"Error extracting Ship24 data: {str(e)}")

        return tracking_data

    async def track_with_17track(self, tracking_number: str, carrier: Optional[str] = None) -> Dict:
        """
        Track a parcel using 17track.net as fallback
        """
        tracking_url = f"{self.track17_url}/en#nums={tracking_number}"

        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                # Get browser launch options (PythonAnywhere compatible)
                launch_options = get_browser_launch_options()
                browser = await p.chromium.launch(**launch_options)

                # Build context options with optional proxy
                proxy_config = get_proxy_config()
                context_options = {
                    'user_agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1',
                    'viewport': {'width': 390, 'height': 844}
                }
                if proxy_config:
                    context_options['proxy'] = proxy_config
                    logger.info(f"Using proxy for 17track: {proxy_config['server']}")

                context = await browser.new_context(**context_options)
                page = await context.new_page()

                logger.info(f"Navigating to 17track: {tracking_url}")

                # Navigate to tracking page
                await page.goto(tracking_url, wait_until='domcontentloaded', timeout=30000)

                # Wait for page to load
                await page.wait_for_timeout(5000)

                # Try to click track button if present
                try:
                    track_btn = await page.query_selector('button[class*="track"], .submit-btn, #submit')
                    if track_btn:
                        await track_btn.click()
                        await page.wait_for_timeout(5000)
                except:
                    pass

                # Wait for results
                await page.wait_for_timeout(3000)

                # Extract tracking info
                tracking_data = await self._extract_17track_data(page, tracking_number)

                await browser.close()

                if tracking_data.get('status') != 'Unknown':
                    return {
                        'success': True,
                        'tracking_number': tracking_number,
                        'carrier': tracking_data.get('carrier', carrier or self._detect_carrier(tracking_number) or 'Unknown'),
                        'status': tracking_data.get('status', 'Unknown'),
                        'events': tracking_data.get('events', []),
                        'current_location': tracking_data.get('location', 'Unknown'),
                        'estimated_delivery': tracking_data.get('estimated_delivery'),
                        'last_updated': datetime.utcnow().isoformat(),
                        'tracking_url': tracking_url,
                        'source': '17track'
                    }
                else:
                    return None  # Indicate fallback needed

        except Exception as e:
            logger.error(f"Error tracking with 17track {tracking_number}: {str(e)}")
            return None

    async def _extract_17track_data(self, page, tracking_number: str) -> Dict:
        """Extract tracking data from 17track results page"""
        tracking_data = {
            'carrier': 'Unknown',
            'status': 'Unknown',
            'location': 'Unknown',
            'events': [],
            'estimated_delivery': None
        }

        try:
            page_text = await page.evaluate('() => document.body.innerText')
            lower_text = page_text.lower()

            logger.info(f"17track page text length: {len(page_text)}")
            # Debug: Log first 500 chars to see what content we're getting
            logger.info(f"17track page content preview: {page_text[:500] if page_text else 'EMPTY'}")

            # Check for no results
            if 'not found' in lower_text or 'no result' in lower_text:
                tracking_data['status'] = 'No tracking information found'
                return tracking_data

            # Extract carrier
            carriers = [
                'Singapore Post', 'SingPost', 'DHL', 'FedEx', 'UPS', 'USPS',
                'China Post', 'EMS', 'Royal Mail', 'Pos Malaysia', 'Thai Post',
                'Japan Post', 'Korea Post', 'Australia Post', 'Aramex', 'TNT'
            ]
            for c in carriers:
                if c.lower() in lower_text:
                    tracking_data['carrier'] = c
                    break

            # Extract status
            status_mapping = {
                'delivered': 'Delivered',
                'in transit': 'In Transit',
                'out for delivery': 'Out for Delivery',
                'customs': 'At Customs',
                'picked up': 'Picked Up',
                'info received': 'Info Received',
                'exception': 'Exception',
                'expired': 'Expired'
            }
            for keyword, status in status_mapping.items():
                if keyword in lower_text:
                    tracking_data['status'] = status
                    break

            # Set location based on status
            if tracking_data['status'] == 'Delivered':
                tracking_data['location'] = 'Delivered'
            elif tracking_data['status'] in ['In Transit', 'Out for Delivery']:
                tracking_data['location'] = tracking_data['status']

            # Try to extract events with dates
            events = []
            lines = page_text.split('\n')
            for line in lines:
                line = line.strip()
                if len(line) < 20 or len(line) > 300:
                    continue

                # Must have date pattern
                has_date = bool(re.search(
                    r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\w{3}\s+\d{1,2},?\s+\d{4}|\d{4}-\d{2}-\d{2}',
                    line
                ))
                if has_date:
                    has_time = bool(re.search(r'\d{1,2}:\d{2}', line))
                    if has_time:
                        clean_text = ' '.join(line.split())
                        if clean_text not in [e['description'] for e in events]:
                            events.append({
                                'description': clean_text,
                                'timestamp': None
                            })
                            if len(events) >= 10:
                                break

            tracking_data['events'] = events

        except Exception as e:
            logger.error(f"Error extracting 17track data: {str(e)}")

        return tracking_data

    async def track_with_trackingmore(self, tracking_number: str, carrier: Optional[str] = None) -> Dict:
        """
        Track a parcel using TrackingMore as fallback (good for SingPost)
        """
        tracking_url = f"https://www.trackingmore.com/track/en/{tracking_number}"

        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                # Get browser launch options (PythonAnywhere compatible)
                launch_options = get_browser_launch_options()
                browser = await p.chromium.launch(**launch_options)

                # Build context options with optional proxy
                proxy_config = get_proxy_config()
                context_options = {
                    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                    'viewport': {'width': 1366, 'height': 768},
                    'locale': 'en-US',
                    'timezone_id': 'America/New_York'
                }
                if proxy_config:
                    context_options['proxy'] = proxy_config
                    logger.info(f"Using proxy for TrackingMore: {proxy_config['server']}")

                context = await browser.new_context(**context_options)
                page = await context.new_page()

                # Add stealth scripts to avoid detection
                await page.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                    Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
                    Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                """)

                logger.info(f"Navigating to TrackingMore: {tracking_url}")

                await page.goto(tracking_url, wait_until='domcontentloaded', timeout=30000)
                await page.wait_for_timeout(5000)

                # Extract tracking info
                tracking_data = await self._extract_trackingmore_data(page, tracking_number)

                await browser.close()

                if tracking_data.get('status') != 'Unknown':
                    return {
                        'success': True,
                        'tracking_number': tracking_number,
                        'carrier': tracking_data.get('carrier', carrier or self._detect_carrier(tracking_number) or 'Unknown'),
                        'status': tracking_data.get('status', 'Unknown'),
                        'events': tracking_data.get('events', []),
                        'current_location': tracking_data.get('location', 'Unknown'),
                        'estimated_delivery': tracking_data.get('estimated_delivery'),
                        'last_updated': datetime.utcnow().isoformat(),
                        'tracking_url': tracking_url,
                        'source': 'TrackingMore'
                    }
                else:
                    return None

        except Exception as e:
            logger.error(f"Error tracking with TrackingMore {tracking_number}: {str(e)}")
            return None

    async def _extract_trackingmore_data(self, page, tracking_number: str) -> Dict:
        """Extract tracking data from TrackingMore results page"""
        tracking_data = {
            'carrier': 'Unknown',
            'status': 'Unknown',
            'location': 'Unknown',
            'events': [],
            'estimated_delivery': None
        }

        try:
            page_text = await page.evaluate('() => document.body.innerText')
            lower_text = page_text.lower()

            logger.info(f"TrackingMore page text length: {len(page_text)}")

            # Check for no results
            if 'not found' in lower_text or 'no tracking' in lower_text or 'invalid' in lower_text:
                tracking_data['status'] = 'No tracking information found'
                return tracking_data

            # Extract carrier
            carriers = [
                'Singapore Post', 'SingPost', 'DHL', 'FedEx', 'UPS', 'USPS',
                'China Post', 'EMS', 'Royal Mail', 'Pos Malaysia', 'Thai Post',
                'Japan Post', 'Korea Post', 'Australia Post', 'Aramex', 'TNT'
            ]
            for c in carriers:
                if c.lower() in lower_text:
                    tracking_data['carrier'] = c
                    break

            # Extract status
            status_mapping = {
                'delivered': 'Delivered',
                'in transit': 'In Transit',
                'out for delivery': 'Out for Delivery',
                'customs': 'At Customs',
                'picked up': 'Picked Up',
                'info received': 'Info Received',
                'exception': 'Exception',
                'expired': 'Expired',
                'arrived': 'Arrived'
            }
            for keyword, status in status_mapping.items():
                if keyword in lower_text:
                    tracking_data['status'] = status
                    break

            # Set location based on status
            if tracking_data['status'] == 'Delivered':
                tracking_data['location'] = 'Delivered'
            elif tracking_data['status'] in ['In Transit', 'Out for Delivery']:
                tracking_data['location'] = tracking_data['status']

            # Try to extract events with dates
            events = []
            lines = page_text.split('\n')
            for line in lines:
                line = line.strip()
                if len(line) < 15 or len(line) > 300:
                    continue

                # Must have date pattern
                has_date = bool(re.search(
                    r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\w{3}\s+\d{1,2},?\s+\d{4}|\d{4}-\d{2}-\d{2}',
                    line
                ))
                if has_date:
                    clean_text = ' '.join(line.split())
                    # Skip UI elements
                    if any(skip in clean_text.lower() for skip in ['cookie', 'privacy', 'subscribe', 'sign up', 'login']):
                        continue
                    if clean_text not in [e['description'] for e in events]:
                        events.append({
                            'description': clean_text,
                            'timestamp': None
                        })
                        if len(events) >= 10:
                            break

            tracking_data['events'] = events

        except Exception as e:
            logger.error(f"Error extracting TrackingMore data: {str(e)}")

        return tracking_data

    async def track_with_hfd(self, tracking_number: str) -> Optional[Dict]:
        """
        Track a parcel using HFD Israel website via Oxylabs Web Unblocker
        HFD pages are in Hebrew and rendered via JavaScript
        Uses ONLY Oxylabs proxy method - no fallback to Playwright
        """
        original_input = tracking_number.strip()
        tracking_url = self._get_hfd_tracking_url(tracking_number)
        logger.info(f"Tracking HFD parcel at: {tracking_url}")

        # Track original URL for debug
        original_url = tracking_url
        resolved_from_short = False

        # If it's a short URL, resolve it first to get the actual tracking URL
        if 'hfd.sh/' in tracking_url:
            logger.info(f"[HFD] Detected short URL, resolving: {tracking_url}")
            resolved_url = await self._resolve_hfd_short_url(tracking_url)
            if resolved_url:
                tracking_url = resolved_url
                resolved_from_short = True
                logger.info(f"[HFD] Resolved short URL to: {tracking_url}")
            else:
                logger.warning(f"[HFD] Could not resolve short URL, using original")

        # Debug info to return - comprehensive error tracking
        debug_info = {
            'method': 'oxylabs_web_unblocker',
            'tracking_number': tracking_number,
            'original_input': original_input,
            'original_url': original_url,
            'tracking_url': tracking_url,
            'resolved_from_short_url': resolved_from_short,
            'proxy_endpoint': 'unblock.oxylabs.io:60000',
            'timestamp': datetime.utcnow().isoformat(),
            'steps': []
        }

        # Step 1: Check environment and credentials
        oxylabs_username = os.environ.get('OXYLABS_USERNAME', 'truelog_4k6QP')
        oxylabs_password = os.environ.get('OXYLABS_PASSWORD', '8x5UDpDnhe0+m5z')

        debug_info['credentials'] = {
            'username': oxylabs_username,
            'password_set': bool(oxylabs_password),
            'password_length': len(oxylabs_password) if oxylabs_password else 0,
            'from_env': 'OXYLABS_USERNAME' in os.environ
        }
        debug_info['steps'].append({'step': 1, 'action': 'credentials_loaded', 'status': 'ok'})

        try:
            import requests
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            debug_info['steps'].append({'step': 2, 'action': 'imports_loaded', 'status': 'ok'})
        except ImportError as e:
            debug_info['steps'].append({'step': 2, 'action': 'imports_loaded', 'status': 'failed', 'error': str(e)})
            debug_info['error'] = f'Missing required library: {str(e)}'
            return self._hfd_error_response(tracking_number, tracking_url, debug_info, 'Missing requests library')

        # Step 3: Build proxy configuration
        proxies = {
            'http': f'https://{oxylabs_username}:{oxylabs_password}@unblock.oxylabs.io:60000',
            'https': f'https://{oxylabs_username}:{oxylabs_password}@unblock.oxylabs.io:60000'
        }
        debug_info['steps'].append({'step': 3, 'action': 'proxy_configured', 'status': 'ok'})

        # Step 4: Make the request
        try:
            logger.info(f"[HFD] Step 4: Making request to {tracking_url}")
            debug_info['steps'].append({'step': 4, 'action': 'request_started', 'url': tracking_url})

            response = requests.get(
                tracking_url,
                proxies=proxies,
                verify=False,
                timeout=90,  # Increased timeout
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'he-IL,he;q=0.9,en-US;q=0.8,en;q=0.7',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                },
                allow_redirects=True
            )

            # Step 5: Process response
            debug_info['response'] = {
                'status_code': response.status_code,
                'content_length': len(response.text),
                'headers': dict(response.headers),
                'url_after_redirects': response.url,
                'encoding': response.encoding,
                'elapsed_seconds': response.elapsed.total_seconds()
            }
            debug_info['steps'].append({
                'step': 5,
                'action': 'response_received',
                'status_code': response.status_code,
                'content_length': len(response.text),
                'elapsed': response.elapsed.total_seconds()
            })

            logger.info(f"[HFD] Response: status={response.status_code}, length={len(response.text)}, elapsed={response.elapsed.total_seconds()}s")

            page_text = response.text

            # Add preview of response content
            debug_info['response']['content_preview'] = page_text[:1000] if page_text else 'EMPTY'
            debug_info['response']['content_tail'] = page_text[-500:] if len(page_text) > 500 else ''

            # Step 6: Validate response
            if response.status_code != 200:
                debug_info['steps'].append({
                    'step': 6,
                    'action': 'validate_status',
                    'status': 'failed',
                    'reason': f'HTTP {response.status_code}'
                })
                return self._hfd_error_response(
                    tracking_number, tracking_url, debug_info,
                    f'HTTP Error {response.status_code}: {response.reason}'
                )

            if len(page_text) < 500:
                debug_info['steps'].append({
                    'step': 6,
                    'action': 'validate_content',
                    'status': 'failed',
                    'reason': f'Response too short ({len(page_text)} bytes)'
                })
                return self._hfd_error_response(
                    tracking_number, tracking_url, debug_info,
                    f'Response too short ({len(page_text)} bytes) - possible empty page or error'
                )

            debug_info['steps'].append({'step': 6, 'action': 'validate_response', 'status': 'ok'})

            # Step 7: Check for blocks/captchas
            lower_text = page_text.lower()
            block_indicators = [
                ('you have been blocked', 'Cloudflare WAF block'),
                ('access denied', 'Access denied'),
                ('captcha', 'CAPTCHA challenge'),
                ('challenge-running', 'JavaScript challenge'),
                ('cf-browser-verification', 'Cloudflare browser check'),
                ('just a moment', 'Cloudflare waiting page'),
                ('checking your browser', 'Browser verification'),
                ('ray id', 'Cloudflare error page'),
            ]

            for indicator, block_type in block_indicators:
                if indicator in lower_text:
                    debug_info['steps'].append({
                        'step': 7,
                        'action': 'check_blocks',
                        'status': 'blocked',
                        'block_type': block_type,
                        'indicator': indicator
                    })
                    debug_info['blocked'] = True
                    debug_info['block_type'] = block_type
                    return self._hfd_error_response(
                        tracking_number, tracking_url, debug_info,
                        f'Blocked by {block_type}. The proxy may need adjustment.'
                    )

            debug_info['steps'].append({'step': 7, 'action': 'check_blocks', 'status': 'ok'})

            # Step 8: Parse HTML
            logger.info(f"[HFD] Step 8: Parsing HTML content")
            try:
                tracking_data = self._parse_hfd_html(page_text, tracking_number)
                debug_info['parsing'] = {
                    'status': tracking_data.get('status'),
                    'events_count': len(tracking_data.get('events', [])),
                    'location': tracking_data.get('location'),
                    'estimated_delivery': tracking_data.get('estimated_delivery')
                }
                debug_info['steps'].append({
                    'step': 8,
                    'action': 'parse_html',
                    'status': 'ok',
                    'parsed_status': tracking_data.get('status'),
                    'events_found': len(tracking_data.get('events', []))
                })
            except Exception as parse_error:
                import traceback
                debug_info['steps'].append({
                    'step': 8,
                    'action': 'parse_html',
                    'status': 'failed',
                    'error': str(parse_error),
                    'traceback': traceback.format_exc()
                })
                return self._hfd_error_response(
                    tracking_number, tracking_url, debug_info,
                    f'HTML parsing failed: {str(parse_error)}'
                )

            # Step 9: Validate parsed data
            if tracking_data.get('status') in ['Unknown', None]:
                debug_info['steps'].append({
                    'step': 9,
                    'action': 'validate_parsed',
                    'status': 'warning',
                    'reason': 'Could not extract status from page'
                })
                # Still return success but with warning
                return {
                    'success': True,
                    'tracking_number': tracking_number,
                    'carrier': 'HFD Israel',
                    'status': 'Unable to Parse',
                    'events': tracking_data.get('events', []),
                    'current_location': tracking_data.get('location', 'Israel'),
                    'estimated_delivery': tracking_data.get('estimated_delivery'),
                    'last_updated': datetime.utcnow().isoformat(),
                    'tracking_url': tracking_url,
                    'source': 'HFD (Oxylabs)',
                    'warning': 'Page loaded but status could not be extracted. Check the tracking link manually.',
                    'debug_info': debug_info
                }

            debug_info['steps'].append({'step': 9, 'action': 'validate_parsed', 'status': 'ok'})

            # Success!
            logger.info(f"[HFD] Successfully parsed: status={tracking_data.get('status')}, events={len(tracking_data.get('events', []))}")
            return {
                'success': True,
                'tracking_number': tracking_number,
                'carrier': 'HFD Israel',
                'status': tracking_data.get('status', 'Unknown'),
                'events': tracking_data.get('events', []),
                'current_location': tracking_data.get('location', 'Israel'),
                'estimated_delivery': tracking_data.get('estimated_delivery'),
                'last_updated': datetime.utcnow().isoformat(),
                'tracking_url': tracking_url,
                'source': 'HFD (Oxylabs)',
                'debug_info': debug_info
            }

        except requests.exceptions.Timeout as e:
            debug_info['steps'].append({
                'step': 4,
                'action': 'request',
                'status': 'timeout',
                'error': str(e)
            })
            return self._hfd_error_response(
                tracking_number, tracking_url, debug_info,
                f'Request timed out after 90 seconds. The proxy or HFD site may be slow.'
            )

        except requests.exceptions.ProxyError as e:
            debug_info['steps'].append({
                'step': 4,
                'action': 'request',
                'status': 'proxy_error',
                'error': str(e)
            })
            return self._hfd_error_response(
                tracking_number, tracking_url, debug_info,
                f'Proxy connection failed: {str(e)}. Check Oxylabs credentials and subscription.'
            )

        except requests.exceptions.SSLError as e:
            debug_info['steps'].append({
                'step': 4,
                'action': 'request',
                'status': 'ssl_error',
                'error': str(e)
            })
            return self._hfd_error_response(
                tracking_number, tracking_url, debug_info,
                f'SSL/TLS error: {str(e)}'
            )

        except requests.exceptions.ConnectionError as e:
            debug_info['steps'].append({
                'step': 4,
                'action': 'request',
                'status': 'connection_error',
                'error': str(e)
            })
            return self._hfd_error_response(
                tracking_number, tracking_url, debug_info,
                f'Connection failed: {str(e)}. Check network connectivity.'
            )

        except Exception as e:
            import traceback
            error_tb = traceback.format_exc()
            logger.error(f"[HFD] Unexpected error: {str(e)}")
            logger.error(f"[HFD] Traceback: {error_tb}")
            debug_info['steps'].append({
                'step': 4,
                'action': 'request',
                'status': 'exception',
                'error': str(e),
                'error_type': type(e).__name__,
                'traceback': error_tb
            })
            return self._hfd_error_response(
                tracking_number, tracking_url, debug_info,
                f'Unexpected error ({type(e).__name__}): {str(e)}'
            )

    def _hfd_error_response(self, tracking_number: str, tracking_url: str, debug_info: dict, error_message: str) -> dict:
        """Generate a detailed HFD error response"""
        debug_info['error_message'] = error_message
        debug_info['final_status'] = 'error'

        return {
            'success': False,
            'tracking_number': tracking_number,
            'carrier': 'HFD Israel',
            'status': 'Error',
            'error': error_message,
            'events': [{
                'description': f'Error: {error_message}',
                'timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M')
            }],
            'current_location': 'Israel',
            'last_updated': datetime.utcnow().isoformat(),
            'tracking_url': tracking_url,
            'source': 'HFD (Oxylabs)',
            'debug_info': debug_info,
            'message': 'Could not fetch tracking data. Use the tracking link to check manually.'
        }

    def _parse_hfd_html(self, html_content: str, tracking_number: str) -> Dict:
        """Parse HFD HTML response and extract tracking data"""
        from bs4 import BeautifulSoup

        tracking_data = {
            'status': 'Unknown',
            'location': 'Israel',
            'events': [],
            'estimated_delivery': None
        }

        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            page_text = soup.get_text(separator='\n')
            logger.info(f"HFD HTML parsed, text length: {len(page_text)}")

            # Use the same translation logic
            phrase_translations = self._get_hfd_translations()

            def translate_hebrew(text):
                result = text
                for hebrew, english in phrase_translations:
                    result = result.replace(hebrew, english)
                return result

            # Detect status
            if 'נמסר' in page_text:
                tracking_data['status'] = 'Delivered'
            elif 'בדרך ללקוח' in page_text or 'בדרך' in page_text:
                tracking_data['status'] = 'In Transit'
            elif 'יצא לחלוקה' in page_text or 'בחלוקה' in page_text:
                tracking_data['status'] = 'Out for Delivery'
            elif 'במחסן' in page_text or 'במחסני' in page_text:
                tracking_data['status'] = 'At Warehouse'
            elif 'התקבל' in page_text or 'נקלט' in page_text or 'הוקם במערכת' in page_text:
                tracking_data['status'] = 'Received'

            logger.info(f"HFD parsed status: {tracking_data['status']}")

            # Extract events from page text
            events = []
            lines = page_text.split('\n')
            lines = [l.strip() for l in lines if l.strip()]

            i = 0
            while i < len(lines) and len(events) < 15:
                line = lines[i]
                if len(line) < 5 or len(line) > 300:
                    i += 1
                    continue

                date_match = re.match(r'^(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})\s*(\d{1,2}:\d{2})?$', line)
                if date_match:
                    date_str = date_match.group(1)
                    time_str = date_match.group(2) or ''
                    timestamp = f"{date_str} {time_str}".strip()

                    if i > 0:
                        for j in range(i - 1, max(i - 3, -1), -1):
                            prev_line = lines[j]
                            if not re.match(r'^\d{1,2}[./-]\d{1,2}[./-]\d{2,4}', prev_line):
                                translated = translate_hebrew(prev_line)
                                skip_phrases = ['shipment status', 'shipment details', 'shipping address', 'status', 'details', 'estimated delivery']
                                if translated.lower() not in skip_phrases:
                                    if not any(e.get('description') == translated and e.get('timestamp') == timestamp for e in events):
                                        events.append({'description': translated, 'timestamp': timestamp})
                                break
                i += 1

            tracking_data['events'] = events
            logger.info(f"HFD parsed {len(events)} events")

        except Exception as e:
            logger.error(f"Error parsing HFD HTML: {str(e)}")

        return tracking_data

    def _get_hfd_translations(self):
        """Get HFD Hebrew to English translations"""
        return [
            ('המשלוח במחסני המיון שלנו ולאחר מיון יצא אל בית הלקוח', 'Shipment at sorting warehouse, will be sent to customer after sorting'),
            ('המשלוח בדרכו לישראל/למחסן המיון', 'Shipment on its way to Israel/sorting warehouse'),
            ('צפי מסירה משוער עד', 'Estimated delivery by'),
            ('צפי מסירה משוער', 'Estimated delivery'),
            ('המשלוח הוקם במערכת', 'Shipment created in system'),
            ('המשלוח במחסני HFD', 'Shipment at HFD warehouse'),
            ('המשלוח בדרך ללקוח', 'Shipment on its way to customer'),
            ('המשלוח נמסר', 'Shipment delivered'),
            ('המשלוח בדרך', 'Shipment in transit'),
            ('סטטוס משלוח', 'Shipment Status'),
            ('פרטי משלוח', 'Shipment Details'),
            ('פרטי נהג', 'Out for delivery'),
            ('נמסר', 'Delivered'),
            ('במשלוח', 'In shipment'),
            ('בדרך', 'On the way'),
            ('התקבל', 'Received'),
            ('במחסן', 'At warehouse'),
            ('במחסני', 'At warehouses'),
            ('נהג', 'Driver'),
            ('המשלוח', 'Shipment'),
            ('משלוח', 'shipment'),
        ]

    async def _track_hfd_playwright(self, tracking_number: str, tracking_url: str) -> Optional[Dict]:
        """Fallback: Track HFD using Playwright (no proxy)"""
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            launch_options = get_browser_launch_options()
            browser = await p.chromium.launch(**launch_options)

            context_options = {
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'viewport': {'width': 1366, 'height': 768},
                'locale': 'he-IL'
            }

            context = await browser.new_context(**context_options)
            page = await context.new_page()

            await page.goto(tracking_url, wait_until='domcontentloaded', timeout=30000)
            await page.wait_for_timeout(5000)

            tracking_data = await self._extract_hfd_data(page, tracking_number)
            await browser.close()

            if tracking_data.get('status') not in ['Unknown', None]:
                return {
                    'success': True,
                    'tracking_number': tracking_number,
                    'carrier': 'HFD Israel',
                    'status': tracking_data.get('status', 'Unknown'),
                    'events': tracking_data.get('events', []),
                    'current_location': tracking_data.get('location', 'Israel'),
                    'last_updated': datetime.utcnow().isoformat(),
                    'tracking_url': tracking_url,
                    'source': 'HFD'
                }

        return None

    async def _extract_hfd_data(self, page, tracking_number: str) -> Dict:
        """Extract tracking data from HFD Israel page (Hebrew content)"""
        tracking_data = {
            'status': 'Unknown',
            'location': 'Israel',
            'events': [],
            'estimated_delivery': None
        }

        try:
            page_text = await page.evaluate('() => document.body.innerText')
            logger.info(f"HFD page text length: {len(page_text)}")
            logger.info(f"HFD page preview: {page_text[:500] if page_text else 'EMPTY'}")

            # HFD-specific full phrase translations (MUST be sorted longest first)
            # These are actual phrases from HFD tracking pages
            phrase_translations = [
                # Full HFD status phrases (longest first to avoid partial matches)
                ('המשלוח במחסני המיון שלנו ולאחר מיון יצא אל בית הלקוח', 'Shipment at sorting warehouse, will be sent to customer after sorting'),
                ('המשלוח בדרכו לישראל/למחסן המיון', 'Shipment on its way to Israel/sorting warehouse'),
                ('צפי מסירה משוער עד', 'Estimated delivery by'),
                ('צפי מסירה משוער', 'Estimated delivery'),
                ('המשלוח הוקם במערכת', 'Shipment created in system'),
                ('המשלוח במחסני HFD', 'Shipment at HFD warehouse'),
                ('המשלוח בדרך ללקוח', 'Shipment on its way to customer'),
                ('המשלוח נמסר', 'Shipment delivered'),
                ('המשלוח בדרך', 'Shipment in transit'),
                ('סטטוס משלוח', 'Shipment Status'),
                ('פרטי משלוח', 'Shipment Details'),
                ('כתובת למשלוח', 'Shipping Address'),
                ('היסטוריית משלוח', 'Shipment History'),
                ('איפה המשלוח שלי', 'Where is my shipment'),
                ('מוכן לאיסוף', 'Ready for pickup'),
                ('יצא לחלוקה', 'Out for delivery'),
                ('הגיע ליעד', 'Arrived at destination'),
                ('בדרך ללקוח', 'On the way to customer'),
                ('פרטי נהג', 'Out for delivery'),
                # Status words
                ('נמסר', 'Delivered'),
                ('נמסרה', 'Delivered'),
                ('סופק', 'Supplied'),
                ('במשלוח', 'In shipment'),
                ('בדרך', 'On the way'),
                ('בחלוקה', 'In distribution'),
                ('התקבל', 'Received'),
                ('נקלט', 'Received'),
                ('ממתין', 'Pending'),
                ('בטיפול', 'Processing'),
                ('במחסן', 'At warehouse'),
                ('במחסני', 'At warehouses'),
                ('בסניף', 'At branch'),
                ('החזרה', 'Return'),
                ('הוחזר', 'Returned'),
                ('הועבר', 'Transferred'),
                ('עודכן', 'Updated'),
                ('נשלח', 'Sent'),
                ('הגיע', 'Arrived'),
                ('יצא', 'Left'),
                ('נאסף', 'Collected'),
                ('נהג', 'Driver'),
                # Common words
                ('המשלוח', 'Shipment'),
                ('משלוח', 'shipment'),
                ('החבילה', 'The package'),
                ('חבילה', 'package'),
                ('ללקוח', 'to customer'),
                ('לכתובת', 'to address'),
                ('סטטוס', 'Status'),
                ('תאריך', 'Date'),
                ('שעה', 'Time'),
                ('פרטי', 'Details'),
                ('כתובת', 'Address'),
                ('שלנו', 'our'),
                ('ולאחר', 'and after'),
                ('מיון', 'sorting'),
                ('אל', 'to'),
                ('בית', 'home'),
                ('הלקוח', 'the customer'),
                ('צפי', 'Estimated'),
                ('מסירה', 'delivery'),
                ('משוער', 'estimated'),
                ('עד', 'by'),
            ]

            def translate_hebrew(text):
                """Translate Hebrew text using phrase list (longest first)"""
                result = text
                for hebrew, english in phrase_translations:
                    result = result.replace(hebrew, english)
                return result

            # Search for status in page text (check for delivered first)
            if 'נמסר' in page_text:
                tracking_data['status'] = 'Delivered'
                logger.info("Found HFD status: Delivered")
            elif 'בדרך ללקוח' in page_text or 'בדרך' in page_text:
                tracking_data['status'] = 'In Transit'
                logger.info("Found HFD status: In Transit")
            elif 'יצא לחלוקה' in page_text or 'בחלוקה' in page_text:
                tracking_data['status'] = 'Out for Delivery'
                logger.info("Found HFD status: Out for Delivery")
            elif 'במחסן' in page_text or 'במחסני' in page_text:
                tracking_data['status'] = 'At Warehouse'
                logger.info("Found HFD status: At Warehouse")
            elif 'התקבל' in page_text or 'נקלט' in page_text or 'הוקם במערכת' in page_text:
                tracking_data['status'] = 'Received'
                logger.info("Found HFD status: Received")

            # Try to extract events from timeline elements
            events = []
            try:
                # Look for timeline or event elements
                event_elements = await page.query_selector_all('[class*="timeline"] li, [class*="event"], [class*="status-item"], tr')
                for elem in event_elements[:15]:  # Limit to 15 events
                    try:
                        text = await elem.inner_text()
                        text = text.strip()
                        if text and len(text) > 5 and len(text) < 500:
                            translated = translate_hebrew(text)
                            events.append({
                                'description': translated,
                                'timestamp': None,
                                'original': text
                            })
                    except:
                        pass
            except:
                pass

            # If no events found, try parsing from page text
            # HFD format: status line, then date/time line on next line
            if not events:
                lines = page_text.split('\n')
                lines = [l.strip() for l in lines if l.strip()]

                i = 0
                while i < len(lines) and len(events) < 15:
                    line = lines[i]

                    # Skip very short or very long lines
                    if len(line) < 5 or len(line) > 300:
                        i += 1
                        continue

                    # Check if this line is a date/time (e.g., "12.01.2026 09:40")
                    date_match = re.match(r'^(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})\s*(\d{1,2}:\d{2})?$', line)

                    if date_match:
                        # This is a date line - look back for the status
                        date_str = date_match.group(1)
                        time_str = date_match.group(2) or ''
                        timestamp = f"{date_str} {time_str}".strip()

                        # Find the previous non-date status line
                        if i > 0:
                            for j in range(i - 1, max(i - 3, -1), -1):
                                prev_line = lines[j]
                                # Check if previous line is NOT a date
                                if not re.match(r'^\d{1,2}[./-]\d{1,2}[./-]\d{2,4}', prev_line):
                                    # This is the status for this date
                                    translated = translate_hebrew(prev_line)

                                    # Skip UI elements and estimated delivery header
                                    skip_phrases = ['shipment status', 'shipment details', 'shipping address', 'status', 'details', 'estimated delivery by', 'estimated delivery']
                                    if translated.lower() not in skip_phrases:
                                        event = {
                                            'description': translated,
                                            'timestamp': timestamp
                                        }
                                        # Avoid duplicates
                                        if not any(e.get('description') == translated and e.get('timestamp') == timestamp for e in events):
                                            events.append(event)
                                    break
                    i += 1

                # If still no events with dates, fall back to just collecting status lines
                if not events:
                    for line in lines:
                        if len(line) > 10 and len(line) < 200:
                            has_hebrew = any(hebrew in line for hebrew, _ in phrase_translations[:20])
                            if has_hebrew:
                                translated = translate_hebrew(line)
                                if translated not in [e.get('description') for e in events]:
                                    events.append({
                                        'description': translated,
                                        'timestamp': None
                                    })
                                if len(events) >= 10:
                                    break

            tracking_data['events'] = events

        except Exception as e:
            logger.error(f"Error extracting HFD data: {str(e)}")

        return tracking_data

    def _detect_carrier(self, tracking_number: str) -> Optional[str]:
        """Detect carrier based on tracking number format"""
        tn = tracking_number.upper().strip()
        tn_lower = tracking_number.lower().strip()

        # HFD Israel (URLs, short codes, or 14-digit numbers starting with 5 or 7)
        if self._is_hfd_tracking(tracking_number):
            return 'HFD Israel'

        # DHL Express (10-digit numbers)
        if len(tn) == 10 and tn.isdigit():
            return 'DHL Express'

        # DHL eCommerce
        if tn.startswith('GM') or tn.startswith('LX') or tn.startswith('JD'):
            return 'DHL eCommerce'

        # FedEx (12, 15, 20, or 22 digits)
        if len(tn) in [12, 15, 20, 22] and tn.isdigit():
            return 'FedEx'

        # UPS (1Z followed by alphanumeric)
        if tn.startswith('1Z') and len(tn) == 18:
            return 'UPS'

        # USPS (20-22 digits or starts with 94/92)
        if (len(tn) in [20, 22] and tn.isdigit()) or tn.startswith('94') or tn.startswith('92'):
            return 'USPS'

        # Singapore Post
        if tn.startswith('R') and tn.endswith('SG') and len(tn) == 13:
            return 'Singapore Post'

        # SingPost XZD format
        if tn.startswith('XZD'):
            return 'Singapore Post'

        # China Post / EMS
        if (tn.startswith('E') or tn.startswith('C') or tn.startswith('R')) and tn.endswith('CN') and len(tn) == 13:
            return 'China Post'

        # International postal format (2 letters + 9 digits + 2 letters)
        if len(tn) == 13 and tn[:2].isalpha() and tn[2:11].isdigit() and tn[11:].isalpha():
            country_code = tn[11:]
            country_map = {
                'SG': 'Singapore Post',
                'CN': 'China Post',
                'US': 'USPS',
                'GB': 'Royal Mail',
                'AU': 'Australia Post',
                'JP': 'Japan Post',
                'KR': 'Korea Post',
                'MY': 'Pos Malaysia',
                'TH': 'Thai Post'
            }
            return country_map.get(country_code, 'International Post')

        return None

    def _is_singpost_tracking(self, tracking_number: str) -> bool:
        """Check if tracking number is a Singapore Post number"""
        tn = tracking_number.upper().strip()
        # SingPost format: 2 letters + 9 digits + SG
        if len(tn) == 13 and tn[:2].isalpha() and tn[2:11].isdigit() and tn.endswith('SG'):
            return True
        # XZD/XZB/XZ prefixes used by SingPost for certain shipments
        if tn.startswith('XZD') or tn.startswith('XZB') or tn.startswith('XZ'):
            return True
        # SPNDD and SPPSD are new SingPost tracking formats
        if tn.startswith('SPNDD') or tn.startswith('SPPSD'):
            return True
        # Also check for other SingPost formats
        if tn.startswith('SP') or tn.startswith('SG'):
            return True
        return False

    def _is_hfd_tracking(self, tracking_number: str) -> bool:
        """Check if tracking number is an HFD Israel tracking number"""
        tn = tracking_number.strip()

        # HFD short URL format: hfd.sh/xxx or full URL
        if 'hfd.sh/' in tn.lower() or 'hfd.co.il' in tn.lower():
            return True

        # HFD tracking numbers are typically 14-digit numbers
        # Example: 55983416173321, 73083700057955
        if len(tn) >= 12 and len(tn) <= 16 and tn.isdigit():
            # HFD numbers often start with 5 or 7
            if tn.startswith('5') or tn.startswith('7'):
                return True
        return False

    async def _resolve_hfd_short_url(self, short_url: str) -> Optional[str]:
        """Resolve HFD short URL (hfd.sh/xxx) to actual tracking URL without using proxy"""
        try:
            import requests
            logger.info(f"[HFD] Resolving short URL: {short_url}")

            # Use a simple HEAD request to follow redirects and get final URL
            # Don't use proxy for this - short URL service is usually not blocked
            response = requests.head(
                short_url,
                allow_redirects=True,
                timeout=15,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
            )

            final_url = response.url
            logger.info(f"[HFD] Short URL resolved to: {final_url}")

            # Check if it resolved to an HFD tracking page
            if 'hfd.co.il' in final_url or 'run.hfd' in final_url:
                return final_url

            # If HEAD didn't work, try GET
            response = requests.get(
                short_url,
                allow_redirects=True,
                timeout=15,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
            )

            final_url = response.url
            logger.info(f"[HFD] Short URL (GET) resolved to: {final_url}")

            if 'hfd.co.il' in final_url or 'run.hfd' in final_url:
                return final_url

            return None

        except Exception as e:
            logger.error(f"[HFD] Error resolving short URL: {str(e)}")
            return None

    def _get_hfd_tracking_url(self, tracking_number: str) -> str:
        """Get HFD tracking URL from tracking number or short URL"""
        tn = tracking_number.strip()

        # If it's already a full URL, return as-is
        if tn.startswith('http'):
            return tn

        # If it's a short code (like KlXJVk), construct short URL
        if len(tn) <= 10 and not tn.isdigit():
            return f'https://hfd.sh/{tn}'

        # Otherwise it's a tracking number, construct full URL
        return f'https://run.hfd.co.il/info/{tn}'

    def _get_all_tracking_links(self, tracking_number: str) -> Dict[str, str]:
        """Get all tracking links for manual checking"""
        links = {
            'Ship24': f'https://www.ship24.com/tracking?p={tracking_number}',
            '17track': f'https://t.17track.net/en#nums={tracking_number}',
            'TrackingMore': f'https://www.trackingmore.com/track/en/{tracking_number}',
            'ParcelsApp': f'https://parcelsapp.com/en/tracking/{tracking_number}',
        }

        # HFD Israel tracking
        if self._is_hfd_tracking(tracking_number):
            hfd_url = self._get_hfd_tracking_url(tracking_number)
            links = {
                'HFD Israel': hfd_url,
                **links
            }

        # Add carrier-specific links
        if self._is_singpost_tracking(tracking_number):
            # SingPost-specific tracking sites (these often work better for SG parcels)
            links = {
                'Tracking.my': f'https://www.tracking.my/singpost/{tracking_number}',
                'PostalNinja': f'https://postal.ninja/en/tracker/{tracking_number}',
                'Ship24': f'https://www.ship24.com/tracking?p={tracking_number}',
                '17track': f'https://t.17track.net/en#nums={tracking_number}',
                'TrackingMore': f'https://www.trackingmore.com/track/en/{tracking_number}',
                'SingPost': 'https://www.singpost.com/track-items',
            }

        tn = tracking_number.upper()
        if tn.startswith('1Z'):  # UPS
            links['UPS'] = f'https://www.ups.com/track?tracknum={tracking_number}'
        elif len(tn) == 10 and tn.isdigit():  # DHL
            links['DHL'] = f'https://www.dhl.com/en/express/tracking.html?AWB={tracking_number}'
        elif tn.startswith('94') or tn.startswith('92'):  # USPS
            links['USPS'] = f'https://tools.usps.com/go/TrackConfirmAction?tLabels={tracking_number}'

        return links

    def track_parcel_sync(self, tracking_number: str, carrier: Optional[str] = None) -> Dict:
        """Synchronous wrapper for track_parcel"""
        try:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop and loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(self._run_in_new_loop, tracking_number, carrier)
                    return future.result(timeout=120)
            else:
                return self._run_in_new_loop(tracking_number, carrier)

        except Exception as e:
            logger.error(f"Error in sync track_parcel: {str(e)}")
            tracking_url = f"https://www.ship24.com/tracking?p={tracking_number}"
            return {
                'success': True,
                'tracking_number': tracking_number,
                'carrier': self._detect_carrier(tracking_number) or 'Unknown',
                'status': 'Click link to view status',
                'events': [],
                'current_location': 'Unknown',
                'estimated_delivery': None,
                'last_updated': datetime.utcnow().isoformat(),
                'error': str(e),
                'tracking_url': tracking_url,
                'tracking_links': self._get_all_tracking_links(tracking_number),
                'message': f'Error: {str(e)}. Use tracking links to check manually.',
                'source': 'fallback'
            }

    def _run_in_new_loop(self, tracking_number: str, carrier: Optional[str] = None) -> Dict:
        """Run async tracking in a new event loop"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(self.track_parcel(tracking_number, carrier))
            return result
        finally:
            loop.close()

    async def track_multiple_parcels(self, tracking_numbers: List[str]) -> List[Dict]:
        """Track multiple parcels sequentially"""
        results = []
        for tn in tracking_numbers:
            result = await self.track_parcel(tn)
            results.append(result)
            # Small delay between requests to be nice to the server
            await asyncio.sleep(1)
        return results


# Singleton instance
_tracker_instance = None


def get_tracker() -> Ship24Tracker:
    """Get or create Ship24Tracker singleton instance"""
    global _tracker_instance
    if _tracker_instance is None:
        _tracker_instance = Ship24Tracker()
    return _tracker_instance
