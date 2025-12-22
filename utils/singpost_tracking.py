"""
SingPost Tracking API Client
REST API for tracking shipments via SingPost.

API Documentation: SingPost Tracking API v1.0
- Uses XML request/response
- Authentication via API key in Authorization header
"""

import os
import logging
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


@dataclass
class TrackingEvent:
    """Represents a single tracking event"""
    status_description: str
    date: str
    time: str
    status_code: str
    reason_code: Optional[str] = None


@dataclass
class TrackingResult:
    """Represents tracking result for a shipment"""
    tracking_number: str
    found: bool
    origin_country: Optional[str] = None
    destination_country: Optional[str] = None
    posting_date: Optional[str] = None
    events: List[TrackingEvent] = None
    error: Optional[str] = None
    was_pushed: bool = False  # True if shipment was physically received by SingPost

    def __post_init__(self):
        if self.events is None:
            self.events = []

    def check_was_pushed(self) -> bool:
        """
        Check if shipment was physically received/pushed by SingPost.

        Status codes indicating NOT pushed (information only):
        - IR: Information Received - SingPost has order info but not the item yet

        Any other status code (AC, HQ, AL, DF, RS, etc.) indicates the item
        was physically received by SingPost.
        """
        if not self.events:
            return False

        # Check if any event has a status code other than 'IR' (Information Received)
        for event in self.events:
            if event.status_code and event.status_code.upper() != 'IR':
                return True

        return False


class SingPostTrackingClient:
    """
    Client for SingPost Tracking REST API.

    Authentication uses API key in Authorization header.
    Request/Response format is XML.
    """

    # API Endpoints
    SANDBOX_URL = "https://api.qa.singpost.com/sp/tracking"
    PRODUCTION_URL = "https://apim.singpost.com/sp/tracking"

    def __init__(
        self,
        api_key: Optional[str] = None,
        use_production: Optional[bool] = None
    ):
        """
        Initialize the SingPost Tracking client.

        Credentials can be passed directly or loaded from environment variables:
        - SINGPOST_TRACKING_API_KEY
        - SINGPOST_TRACKING_USE_PRODUCTION (true/false)
        """
        self.api_key = api_key or os.environ.get('SINGPOST_TRACKING_API_KEY', '')

        # Determine which environment to use
        if use_production is None:
            use_production = os.environ.get('SINGPOST_TRACKING_USE_PRODUCTION', 'true').lower() == 'true'

        if use_production:
            self.base_url = self.PRODUCTION_URL
        else:
            self.base_url = self.SANDBOX_URL

    def is_configured(self) -> bool:
        """Check if the client has API key configured"""
        return bool(self.api_key)

    def get_credentials_status(self) -> Dict:
        """Check credentials configuration status"""
        return {
            'api_key': bool(self.api_key),
            'is_configured': self.is_configured(),
            'base_url': self.base_url
        }

    def _build_request_xml(self, tracking_numbers: List[str]) -> str:
        """Build XML request payload"""
        tracking_items = '\n'.join([
            f'        <TrackingNumber>{tn}</TrackingNumber>'
            for tn in tracking_numbers
        ])

        return f'''<?xml version="1.0" encoding="UTF-8"?>
<ItemTrackingDetailsRequest xmlns="http://singpost.com/paw/ns">
    <SystemID>-</SystemID>
    <ItemTrackingNumbers>
{tracking_items}
    </ItemTrackingNumbers>
</ItemTrackingDetailsRequest>'''

    def _parse_response_xml(self, xml_text: str) -> List[TrackingResult]:
        """Parse XML response into TrackingResult objects"""
        results = []

        try:
            # Define namespace
            ns = {'sp': 'http://singpost.com/paw/ns'}

            root = ET.fromstring(xml_text)

            # Check for error status
            status = root.find('.//sp:Status', ns)
            if status is not None:
                error_code = status.find('sp:ErrorCode', ns)
                error_desc = status.find('sp:ErrorDesc', ns)
                if error_code is not None and error_code.text != '0':
                    logger.error(f"API Error: {error_desc.text if error_desc is not None else 'Unknown'}")
                    return []

            # Parse tracking details
            items_list = root.find('.//sp:ItemsTrackingDetailList', ns)
            if items_list is None:
                return []

            for item in items_list.findall('sp:ItemTrackingDetail', ns):
                tracking_number = self._get_text(item, 'sp:TrackingNumber', ns)
                found_text = self._get_text(item, 'sp:TrackingNumberFound', ns)
                found = found_text.lower() == 'true' if found_text else False

                result = TrackingResult(
                    tracking_number=tracking_number or '',
                    found=found,
                    origin_country=self._get_text(item, 'sp:OriginCountry', ns) or self._get_text(item, 'sp:OriginalCountry', ns),
                    destination_country=self._get_text(item, 'sp:DestinationCountry', ns),
                    posting_date=self._get_text(item, 'sp:PostingDate', ns),
                    events=[]
                )

                # Parse delivery status details
                status_details = item.find('.//sp:DeliveryStatusDetails', ns)
                if status_details is not None:
                    for detail in status_details.findall('sp:DeliveryStatusDetail', ns):
                        date_str = self._get_text(detail, 'sp:Date', ns) or ''
                        # Parse date and time from ISO format (e.g., "2024-05-21T10:56:00")
                        event_date = ''
                        event_time = ''
                        if date_str and 'T' in date_str:
                            parts = date_str.split('T')
                            event_date = parts[0]
                            event_time = parts[1] if len(parts) > 1 else ''
                        else:
                            event_date = date_str

                        event = TrackingEvent(
                            status_description=self._get_text(detail, 'sp:StatusDescription', ns) or '',
                            date=event_date,
                            time=event_time,
                            status_code=self._get_text(detail, 'sp:StatusCode', ns) or '',
                            reason_code=self._get_text(detail, 'sp:ReasonCode', ns)
                        )
                        result.events.append(event)

                # Check if shipment was pushed (physically received by SingPost)
                result.was_pushed = result.check_was_pushed()

                results.append(result)

            return results

        except ET.ParseError as e:
            logger.error(f"XML Parse Error: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Error parsing response: {str(e)}")
            return []

    def _get_text(self, element, path: str, ns: dict) -> Optional[str]:
        """Helper to get text from XML element"""
        found = element.find(path, ns)
        if found is not None and found.text:
            text = found.text.strip()
            return text if text and text != '-' else None
        return None

    def track(self, tracking_numbers: List[str]) -> List[TrackingResult]:
        """
        Track multiple shipments.

        Args:
            tracking_numbers: List of tracking numbers (max recommended: 10)

        Returns:
            List of TrackingResult objects
        """
        if not self.is_configured():
            logger.error("SingPost Tracking API not configured - missing API key")
            return [TrackingResult(
                tracking_number=tn,
                found=False,
                error="API not configured - missing API key"
            ) for tn in tracking_numbers]

        try:
            # Build request
            xml_payload = self._build_request_xml(tracking_numbers)

            headers = {
                'Content-Type': 'application/xml',
                'Authorization': self.api_key,
                'User-Agent': 'TrueLog-Inventory/1.0'
            }

            logger.info(f"Tracking {len(tracking_numbers)} shipment(s) via SingPost API")

            response = requests.post(
                self.base_url,
                data=xml_payload,
                headers=headers,
                timeout=30
            )

            if response.status_code != 200:
                logger.error(f"API returned status {response.status_code}: {response.text}")
                return [TrackingResult(
                    tracking_number=tn,
                    found=False,
                    error=f"API error: HTTP {response.status_code}"
                ) for tn in tracking_numbers]

            # Parse response
            results = self._parse_response_xml(response.text)

            # Ensure we have results for all requested tracking numbers
            found_numbers = {r.tracking_number for r in results}
            for tn in tracking_numbers:
                if tn not in found_numbers:
                    results.append(TrackingResult(
                        tracking_number=tn,
                        found=False,
                        error="Tracking number not found in response"
                    ))

            return results

        except requests.exceptions.Timeout:
            logger.error("SingPost API request timed out")
            return [TrackingResult(
                tracking_number=tn,
                found=False,
                error="Request timed out"
            ) for tn in tracking_numbers]
        except requests.exceptions.RequestException as e:
            logger.error(f"SingPost API request failed: {str(e)}")
            return [TrackingResult(
                tracking_number=tn,
                found=False,
                error=str(e)
            ) for tn in tracking_numbers]
        except Exception as e:
            logger.error(f"Unexpected error tracking shipment: {str(e)}")
            return [TrackingResult(
                tracking_number=tn,
                found=False,
                error=str(e)
            ) for tn in tracking_numbers]

    def track_single(self, tracking_number: str) -> Optional[Dict]:
        """
        Track a single shipment and return formatted dictionary.

        Args:
            tracking_number: The tracking number to look up

        Returns:
            Dictionary with tracking info formatted for display
        """
        results = self.track([tracking_number])

        if not results:
            return {
                'success': False,
                'tracking_number': tracking_number,
                'error': 'No response from API'
            }

        result = results[0]

        if not result.found:
            return {
                'success': False,
                'tracking_number': tracking_number,
                'error': result.error or 'Tracking number not found'
            }

        # Format events for display
        events = []
        for event in result.events:
            events.append({
                'code': event.status_code,
                'description': event.status_description,
                'date': event.date,
                'time': event.time,
                'reason_code': event.reason_code,
                'location': None,
                'signatory': None
            })

        # Determine overall status from first (most recent) event
        status = 'Unknown'
        if result.events:
            latest = result.events[0]
            status = latest.status_description

        return {
            'success': True,
            'tracking_number': result.tracking_number,
            'carrier': 'SingPost',
            'status': status,
            'origin_country': result.origin_country,
            'destination_country': result.destination_country,
            'posting_date': result.posting_date,
            'events': events,
            'was_pushed': result.was_pushed,  # True if physically received by SingPost
            'last_updated': datetime.utcnow().isoformat(),
            'source': 'SingPost Tracking API'
        }


# Singleton instance
_client_instance = None

def get_singpost_tracking_client() -> SingPostTrackingClient:
    """Get the singleton SingPost Tracking client instance"""
    global _client_instance
    if _client_instance is None:
        _client_instance = SingPostTrackingClient()
    return _client_instance
