"""
SingPost Ezy2ship SOAP API Client
Provides shipment tracking and history via the Ezy2ship Web Services API.
"""

import hashlib
import base64
import os
import logging
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Check if required cryptography libraries are available
CRYPTO_AVAILABLE = False
try:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad
    CRYPTO_AVAILABLE = True
except ImportError:
    try:
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        from cryptography.hazmat.backends import default_backend
        CRYPTO_AVAILABLE = True
    except ImportError:
        logger.warning("Cryptography libraries not available - SingPost Ezy2ship API will not work")

# Check if zeep (SOAP client) is available
ZEEP_AVAILABLE = False
try:
    from zeep import Client
    from zeep.transports import Transport
    from requests import Session
    ZEEP_AVAILABLE = True
except ImportError:
    logger.warning("zeep library not available - SingPost Ezy2ship API will not work")


@dataclass
class TrackingEvent:
    """Represents a single tracking event"""
    event_code: str
    event_name: str
    event_date: str
    event_time: str
    signatory_name: Optional[str] = None
    location: Optional[str] = None


@dataclass
class ShipmentInfo:
    """Represents shipment tracking information"""
    tracking_number: str
    carrier_code: str
    carrier_tracking_number: Optional[str]
    status: str
    events: List[TrackingEvent]
    last_updated: datetime


class SingPostEzy2shipClient:
    """
    Client for SingPost Ezy2ship SOAP Web Services API.

    Authentication uses AES-256 encrypted ticket containing:
    CustomerID + Username + SHA1Password + Date(YYYYMMDD)
    """

    # API Endpoints
    UAT_WSDL = "https://uatapi.ezyparcels.com/ezy2ship/api.wsdl"
    PROD_WSDL = "https://api.ezyparcels.com/ezy2ship/api.wsdl"

    # Carrier codes
    CARRIER_SPEEDPOST = "LOG"
    CARRIER_MAIL = "MAI"
    CARRIER_QUANTIUM = "QSC"

    def __init__(
        self,
        customer_id: Optional[int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        aes_key: Optional[str] = None,
        use_production: bool = False
    ):
        """
        Initialize the Ezy2ship client.

        Credentials can be passed directly or loaded from environment variables:
        - SINGPOST_EZY2SHIP_CUSTOMER_ID
        - SINGPOST_EZY2SHIP_USERNAME
        - SINGPOST_EZY2SHIP_PASSWORD
        - SINGPOST_EZY2SHIP_AES_KEY
        - SINGPOST_EZY2SHIP_USE_PRODUCTION (true/false)
        """
        self.customer_id = customer_id or int(os.environ.get('SINGPOST_EZY2SHIP_CUSTOMER_ID', 0))
        self.username = username or os.environ.get('SINGPOST_EZY2SHIP_USERNAME', '')
        self.password = password or os.environ.get('SINGPOST_EZY2SHIP_PASSWORD', '')
        self.aes_key = aes_key or os.environ.get('SINGPOST_EZY2SHIP_AES_KEY', '')

        if use_production or os.environ.get('SINGPOST_EZY2SHIP_USE_PRODUCTION', 'false').lower() == 'true':
            self.wsdl_url = self.PROD_WSDL
        else:
            self.wsdl_url = self.UAT_WSDL

        self._client = None

    def is_configured(self) -> bool:
        """Check if the client has all required credentials configured"""
        return bool(
            self.customer_id and
            self.username and
            self.password and
            self.aes_key and
            CRYPTO_AVAILABLE and
            ZEEP_AVAILABLE
        )

    def _get_client(self):
        """Get or create the SOAP client"""
        if not ZEEP_AVAILABLE:
            raise RuntimeError("zeep library not available. Install with: pip install zeep")

        if self._client is None:
            session = Session()
            session.timeout = 30
            transport = Transport(session=session)
            self._client = Client(self.wsdl_url, transport=transport)

        return self._client

    def _generate_ticket(self) -> str:
        """
        Generate the authentication ticket for API requests.

        Process:
        1. SHA1 encode the password
        2. Concatenate: CustomerID + Username + SHA1Password + Date(YYYYMMDD)
        3. AES-256 encrypt with CBC mode
        4. Base64 encode
        5. Replace reserved characters: + -> -, / -> _, = -> ,
        """
        if not CRYPTO_AVAILABLE:
            raise RuntimeError("Cryptography library not available")

        # Step 1: SHA1 encode password
        password_sha1 = hashlib.sha1(self.password.encode()).hexdigest()

        # Step 2: Concatenate ticket components
        date_str = datetime.now().strftime('%Y%m%d')
        ticket_plain = f"{self.customer_id}{self.username}{password_sha1}{date_str}"

        # Step 3: AES-256 encrypt
        # Decode the base64 AES key
        key = base64.b64decode(self.aes_key)
        # IV is first 16 bytes of the key
        iv = key[:16]

        try:
            # Try PyCryptodome first
            from Crypto.Cipher import AES
            from Crypto.Util.Padding import pad
            cipher = AES.new(key, AES.MODE_CBC, iv)
            encrypted = cipher.encrypt(pad(ticket_plain.encode(), AES.block_size))
        except ImportError:
            # Fall back to cryptography library
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
            from cryptography.hazmat.backends import default_backend
            from cryptography.hazmat.primitives import padding

            # PKCS7 padding
            padder = padding.PKCS7(128).padder()
            padded_data = padder.update(ticket_plain.encode()) + padder.finalize()

            cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
            encryptor = cipher.encryptor()
            encrypted = encryptor.update(padded_data) + encryptor.finalize()

        # Step 4: Base64 encode
        ticket_b64 = base64.b64encode(encrypted).decode()

        # Step 5: Replace reserved characters
        ticket_final = ticket_b64.replace('+', '-').replace('/', '_').replace('=', ',')

        return ticket_final

    def get_shipments_info(self, tracking_numbers: List[str]) -> List[ShipmentInfo]:
        """
        Get tracking information for multiple shipments.

        Args:
            tracking_numbers: List of tracking numbers (max 100)

        Returns:
            List of ShipmentInfo objects with tracking events
        """
        if not self.is_configured():
            logger.error("SingPost Ezy2ship client not configured")
            return []

        if len(tracking_numbers) > 100:
            logger.warning("Maximum 100 tracking numbers per request, truncating")
            tracking_numbers = tracking_numbers[:100]

        try:
            client = self._get_client()
            ticket = self._generate_ticket()

            # Call the getShipmentsInfo service
            result = client.service.getShipmentsInfo(
                ticket=ticket,
                trackingNumbers={'string': tracking_numbers}
            )

            shipments = []
            if result:
                for shipment_data in result:
                    events = []
                    if hasattr(shipment_data, 'TrackTrace') and shipment_data.TrackTrace:
                        for event in shipment_data.TrackTrace:
                            events.append(TrackingEvent(
                                event_code=str(getattr(event, 'EventCode', '')),
                                event_name=str(getattr(event, 'EventName', '')),
                                event_date=str(getattr(event, 'EventDate', '')),
                                event_time=str(getattr(event, 'EventTime', '')),
                                signatory_name=str(getattr(event, 'EventSignatoryName', '')) or None
                            ))

                    # Determine status from latest event
                    status = 'Unknown'
                    if events:
                        latest_event = events[0]
                        status = latest_event.event_name

                    shipments.append(ShipmentInfo(
                        tracking_number=str(getattr(shipment_data, 'TrackingNumber', '')),
                        carrier_code=str(getattr(shipment_data, 'CarrierCode', '')),
                        carrier_tracking_number=str(getattr(shipment_data, 'CarrierTrackingNumber', '')) or None,
                        status=status,
                        events=events,
                        last_updated=datetime.utcnow()
                    ))

            return shipments

        except Exception as e:
            logger.error(f"Error calling getShipmentsInfo: {str(e)}")
            return []

    def get_shipment(self, tracking_number: str) -> Optional[Dict]:
        """
        Get detailed shipment information for a single tracking number.

        Args:
            tracking_number: The shipment tracking number

        Returns:
            Dictionary with full shipment details including addresses
        """
        if not self.is_configured():
            logger.error("SingPost Ezy2ship client not configured")
            return None

        try:
            client = self._get_client()
            ticket = self._generate_ticket()

            # Call the getShipment service
            result = client.service.getShipment(
                ticket=ticket,
                trackingNumber=tracking_number
            )

            if result:
                return {
                    'tracking_number': str(getattr(result, 'TrackingNumber', '')),
                    'manifest_number': str(getattr(result, 'ManifestNumber', '')),
                    'shipment_type': str(getattr(result, 'ShipmentType', '')),
                    'service_code': str(getattr(result, 'ServiceCode', '')),
                    'carrier_code': str(getattr(result, 'CarrierCode', '')),
                    'status': str(getattr(result, 'Status', '')),
                    'sender': {
                        'name': str(getattr(result, 'SenderName', '')),
                        'company': str(getattr(result, 'SenderCompany', '')),
                        'address1': str(getattr(result, 'SenderAddress1', '')),
                        'address2': str(getattr(result, 'SenderAddress2', '')),
                        'city': str(getattr(result, 'SenderCity', '')),
                        'state': str(getattr(result, 'SenderState', '')),
                        'postcode': str(getattr(result, 'SenderPostcode', '')),
                        'country': str(getattr(result, 'SenderCountryCode', '')),
                        'phone': str(getattr(result, 'SenderPhone', '')),
                        'email': str(getattr(result, 'SenderEmail', ''))
                    },
                    'receiver': {
                        'name': str(getattr(result, 'ReceiverName', '')),
                        'company': str(getattr(result, 'ReceiverCompany', '')),
                        'address1': str(getattr(result, 'ReceiverAddress1', '')),
                        'address2': str(getattr(result, 'ReceiverAddress2', '')),
                        'city': str(getattr(result, 'ReceiverCity', '')),
                        'state': str(getattr(result, 'ReceiverState', '')),
                        'postcode': str(getattr(result, 'ReceiverPostcode', '')),
                        'country': str(getattr(result, 'ReceiverCountryCode', '')),
                        'phone': str(getattr(result, 'ReceiverPhone', '')),
                        'email': str(getattr(result, 'ReceiverEmail', ''))
                    },
                    'last_updated': datetime.utcnow().isoformat()
                }

            return None

        except Exception as e:
            logger.error(f"Error calling getShipment: {str(e)}")
            return None

    def get_tracking_history(self, tracking_number: str) -> Optional[Dict]:
        """
        Get tracking history formatted for display in the shipment history page.

        This is a convenience method that combines getShipmentsInfo and getShipment.

        Returns:
            Dictionary with tracking events and shipment details
        """
        if not self.is_configured():
            return {
                'success': False,
                'error': 'SingPost Ezy2ship API not configured',
                'tracking_number': tracking_number
            }

        try:
            # Get tracking events
            shipments_info = self.get_shipments_info([tracking_number])

            if not shipments_info:
                return {
                    'success': False,
                    'error': 'Tracking number not found',
                    'tracking_number': tracking_number
                }

            shipment_info = shipments_info[0]

            # Convert events to displayable format
            events = []
            for event in shipment_info.events:
                events.append({
                    'code': event.event_code,
                    'description': event.event_name,
                    'date': event.event_date,
                    'time': event.event_time,
                    'signatory': event.signatory_name,
                    'location': event.location
                })

            return {
                'success': True,
                'tracking_number': shipment_info.tracking_number,
                'carrier': self._get_carrier_name(shipment_info.carrier_code),
                'carrier_code': shipment_info.carrier_code,
                'carrier_tracking_number': shipment_info.carrier_tracking_number,
                'status': shipment_info.status,
                'events': events,
                'last_updated': shipment_info.last_updated.isoformat(),
                'source': 'SingPost Ezy2ship API'
            }

        except Exception as e:
            logger.error(f"Error getting tracking history: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'tracking_number': tracking_number
            }

    def _get_carrier_name(self, carrier_code: str) -> str:
        """Convert carrier code to human-readable name"""
        carriers = {
            'LOG': 'Speedpost',
            'MAI': 'Singapore Post Mail',
            'QSC': 'Quantium Solutions'
        }
        return carriers.get(carrier_code, carrier_code)

    def get_manifests(self, date_from: Optional[str] = None, date_to: Optional[str] = None,
                      carrier_code: Optional[str] = None) -> List[Dict]:
        """
        Get list of manifests for the account.

        Args:
            date_from: Start date in YYYY-MM-DD format (default: 30 days ago)
            date_to: End date in YYYY-MM-DD format (default: today)
            carrier_code: Filter by carrier (LOG, MAI, QSC)

        Returns:
            List of manifest dictionaries
        """
        if not self.is_configured():
            logger.error("SingPost Ezy2ship client not configured")
            return []

        try:
            from datetime import timedelta
            client = self._get_client()
            ticket = self._generate_ticket()

            # Default date range: last 30 days
            if not date_to:
                date_to = datetime.now().strftime('%Y-%m-%d')
            if not date_from:
                date_from = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')

            # Call the getManifests service
            params = {
                'ticket': ticket,
                'dateFrom': date_from,
                'dateTo': date_to
            }
            if carrier_code:
                params['carrierCode'] = carrier_code

            result = client.service.getManifests(**params)

            manifests = []
            if result:
                for manifest in result:
                    manifests.append({
                        'manifest_number': str(getattr(manifest, 'ManifestNumber', '')),
                        'manifest_date': str(getattr(manifest, 'ManifestDate', '')),
                        'carrier_code': str(getattr(manifest, 'CarrierCode', '')),
                        'carrier': self._get_carrier_name(str(getattr(manifest, 'CarrierCode', ''))),
                        'shipment_count': int(getattr(manifest, 'ShipmentCount', 0)),
                        'status': str(getattr(manifest, 'Status', ''))
                    })

            return manifests

        except Exception as e:
            logger.error(f"Error calling getManifests: {str(e)}")
            return []

    def get_manifest_shipments(self, manifest_number: str) -> List[Dict]:
        """
        Get all shipments for a specific manifest.

        Args:
            manifest_number: The manifest number

        Returns:
            List of shipment dictionaries
        """
        if not self.is_configured():
            logger.error("SingPost Ezy2ship client not configured")
            return []

        try:
            client = self._get_client()
            ticket = self._generate_ticket()

            # Call the getManifest service to get shipment details
            result = client.service.getManifest(
                ticket=ticket,
                manifestNumber=manifest_number
            )

            shipments = []
            if result and hasattr(result, 'Shipments'):
                for shipment in result.Shipments:
                    shipments.append({
                        'tracking_number': str(getattr(shipment, 'TrackingNumber', '')),
                        'docket_number': str(getattr(shipment, 'DocketNumber', '')),
                        'manifest_number': manifest_number,
                        'manifest_date': str(getattr(result, 'ManifestDate', '')),
                        'service_code': str(getattr(shipment, 'ServiceCode', '')),
                        'carrier_code': str(getattr(shipment, 'CarrierCode', '')),
                        'carrier': self._get_carrier_name(str(getattr(shipment, 'CarrierCode', ''))),
                        'weight': float(getattr(shipment, 'Weight', 0)),
                        'receiver_name': str(getattr(shipment, 'ReceiverName', '')),
                        'receiver_address': str(getattr(shipment, 'ReceiverAddress1', '')),
                        'receiver_city': str(getattr(shipment, 'ReceiverCity', '')),
                        'receiver_postcode': str(getattr(shipment, 'ReceiverPostcode', '')),
                        'receiver_country': str(getattr(shipment, 'ReceiverCountryCode', '')),
                        'status': str(getattr(shipment, 'Status', 'Unknown'))
                    })

            return shipments

        except Exception as e:
            logger.error(f"Error calling getManifest: {str(e)}")
            return []

    def get_all_shipments(self, date_from: Optional[str] = None, date_to: Optional[str] = None,
                          limit: int = 100) -> List[Dict]:
        """
        Get all shipments from all manifests within date range.

        Args:
            date_from: Start date in YYYY-MM-DD format
            date_to: End date in YYYY-MM-DD format
            limit: Maximum number of shipments to return

        Returns:
            List of shipment dictionaries with tracking info
        """
        if not self.is_configured():
            return []

        try:
            # First get all manifests
            manifests = self.get_manifests(date_from, date_to)

            all_shipments = []
            for manifest in manifests:
                if len(all_shipments) >= limit:
                    break

                # Get shipments for each manifest
                shipments = self.get_manifest_shipments(manifest['manifest_number'])
                for shipment in shipments:
                    if len(all_shipments) >= limit:
                        break
                    all_shipments.append(shipment)

            # Get tracking status for all shipments
            if all_shipments:
                tracking_numbers = [s['tracking_number'] for s in all_shipments]
                tracking_info = self.get_shipments_info(tracking_numbers[:100])

                # Map tracking info to shipments
                tracking_map = {t.tracking_number: t for t in tracking_info}
                for shipment in all_shipments:
                    if shipment['tracking_number'] in tracking_map:
                        info = tracking_map[shipment['tracking_number']]
                        shipment['status'] = info.status
                        shipment['events_count'] = len(info.events)
                        shipment['last_event'] = info.events[0].event_name if info.events else None

            return all_shipments

        except Exception as e:
            logger.error(f"Error getting all shipments: {str(e)}")
            return []

    def get_credentials_status(self) -> Dict:
        """Check which credentials are configured"""
        return {
            'customer_id': bool(self.customer_id),
            'username': bool(self.username),
            'password': bool(self.password),
            'aes_key': bool(self.aes_key),
            'crypto_available': CRYPTO_AVAILABLE,
            'zeep_available': ZEEP_AVAILABLE,
            'is_configured': self.is_configured(),
            'wsdl_url': self.wsdl_url
        }


# Singleton instance for easy import
_client_instance = None

def get_ezy2ship_client() -> SingPostEzy2shipClient:
    """Get the singleton Ezy2ship client instance"""
    global _client_instance
    if _client_instance is None:
        _client_instance = SingPostEzy2shipClient()
    return _client_instance
