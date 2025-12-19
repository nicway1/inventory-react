# SingPost Ezy2ship API Summary

## Overview
SingPost Ezy2ship Web Services provides SOAP-based APIs for shipment management, tracking, and logistics operations.

## API Endpoints

| Environment | WSDL URL |
|-------------|----------|
| UAT | `https://uatapi.ezyparcels.com/ezy2ship/api.wsdl` |
| Production | `https://api.ezyparcels.com/ezy2ship/api.wsdl` |

## Authentication

All API requests require an encrypted authentication ticket.

### Ticket Construction Process

1. **SHA1 encode the password**
2. **Concatenate**: `CustomerID + Username + SHA1Password + CurrentDate(YYYYMMDD)`
3. **AES-256 encrypt** using CBC mode with PKCS7 padding
4. **Base64 encode** the result
5. **Replace reserved characters**:
   - `+` → `-`
   - `/` → `_`
   - `=` → `,`

### Required Credentials
- Customer ID (e.g., `108`)
- Username (provided by Quantium)
- Password (provided by Quantium)
- AES Encryption Key (provided by Quantium)

### Python Implementation

```python
import hashlib
import base64
from datetime import datetime
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

def generate_ticket(customer_id: int, username: str, password: str, aes_key: str) -> str:
    """Generate authentication ticket for SingPost API."""
    # Step 1: SHA1 encode password
    password_sha1 = hashlib.sha1(password.encode()).hexdigest()

    # Step 2: Concatenate
    date_str = datetime.now().strftime('%Y%m%d')
    ticket_plain = f"{customer_id}{username}{password_sha1}{date_str}"

    # Step 3: AES-256 encrypt (CBC mode, PKCS7 padding)
    # Decode the base64 AES key
    key = base64.b64decode(aes_key)
    # IV is first 16 bytes of the key
    iv = key[:16]
    cipher = AES.new(key, AES.MODE_CBC, iv)
    encrypted = cipher.encrypt(pad(ticket_plain.encode(), AES.block_size))

    # Step 4: Base64 encode
    ticket_b64 = base64.b64encode(encrypted).decode()

    # Step 5: Replace reserved characters
    ticket_final = ticket_b64.replace('+', '-').replace('/', '_').replace('=', ',')

    return ticket_final
```

---

## Web Services for Shipment Tracking

### 1. getShipmentsInfo

Retrieves tracking/trace information for multiple shipments.

**Request Structure:**
```xml
<getShipmentsInfo>
    <ticket>ENCRYPTED_TICKET</ticket>
    <trackingNumbers>
        <string>TRACKING_NUMBER_1</string>
        <string>TRACKING_NUMBER_2</string>
    </trackingNumbers>
</getShipmentsInfo>
```

**Response Structure:**
```xml
<getShipmentsInfoResponse>
    <getShipmentsInfoResult>
        <ShipmentInfoData>
            <TrackingNumber>string</TrackingNumber>
            <CarrierCode>string</CarrierCode>
            <CarrierTrackingNumber>string</CarrierTrackingNumber>
            <TrackTrace>
                <TrackTraceData>
                    <EventCode>string</EventCode>
                    <EventName>string</EventName>
                    <EventDate>date</EventDate>
                    <EventTime>time</EventTime>
                    <EventSignatoryName>string</EventSignatoryName>
                </TrackTraceData>
            </TrackTrace>
        </ShipmentInfoData>
    </getShipmentsInfoResult>
</getShipmentsInfoResponse>
```

**Key Fields:**
| Field | Description |
|-------|-------------|
| TrackingNumber | The shipment tracking number |
| CarrierCode | Carrier code (LOG=Speedpost, MAI=Mail, QSC=Quantium) |
| CarrierTrackingNumber | Carrier's internal tracking number |
| EventCode | Event status code |
| EventName | Human-readable event description |
| EventDate | Date of event (YYYY-MM-DD) |
| EventTime | Time of event (HH:MM:SS) |
| EventSignatoryName | Name of person who signed (for delivery) |

---

### 2. getShipment

Retrieves detailed information for a single shipment.

**Request Structure:**
```xml
<getShipment>
    <ticket>ENCRYPTED_TICKET</ticket>
    <trackingNumber>TRACKING_NUMBER</trackingNumber>
</getShipment>
```

**Response Structure:**
```xml
<getShipmentResponse>
    <getShipmentResult>
        <ShipmentData>
            <TrackingNumber>string</TrackingNumber>
            <ManifestNumber>string</ManifestNumber>
            <ShipmentType>string</ShipmentType>
            <ServiceCode>string</ServiceCode>
            <CarrierCode>string</CarrierCode>
            <Status>string</Status>
            <SenderName>string</SenderName>
            <SenderCompany>string</SenderCompany>
            <SenderAddress1>string</SenderAddress1>
            <SenderAddress2>string</SenderAddress2>
            <SenderCity>string</SenderCity>
            <SenderState>string</SenderState>
            <SenderPostcode>string</SenderPostcode>
            <SenderCountryCode>string</SenderCountryCode>
            <SenderPhone>string</SenderPhone>
            <SenderEmail>string</SenderEmail>
            <ReceiverName>string</ReceiverName>
            <ReceiverCompany>string</ReceiverCompany>
            <ReceiverAddress1>string</ReceiverAddress1>
            <ReceiverAddress2>string</ReceiverAddress2>
            <ReceiverCity>string</ReceiverCity>
            <ReceiverState>string</ReceiverState>
            <ReceiverPostcode>string</ReceiverPostcode>
            <ReceiverCountryCode>string</ReceiverCountryCode>
            <ReceiverPhone>string</ReceiverPhone>
            <ReceiverEmail>string</ReceiverEmail>
            <HandlingUnits>
                <HandlingUnitData>
                    <Weight>decimal</Weight>
                    <Length>decimal</Length>
                    <Width>decimal</Width>
                    <Height>decimal</Height>
                </HandlingUnitData>
            </HandlingUnits>
            <Contents>
                <ContentData>
                    <Description>string</Description>
                    <Quantity>int</Quantity>
                    <Value>decimal</Value>
                    <Currency>string</Currency>
                </ContentData>
            </Contents>
        </ShipmentData>
    </getShipmentResult>
</getShipmentResponse>
```

---

## Carrier Codes

| Code | Description |
|------|-------------|
| LOG | Speedpost |
| MAI | Mail |
| QSC | Quantium |

## Common Event Codes

| Code | Description |
|------|-------------|
| CRE | Shipment Created |
| COL | Collected |
| DEP | Departed |
| ARR | Arrived |
| OFD | Out for Delivery |
| DEL | Delivered |
| RTS | Return to Sender |
| EXC | Exception |

---

## Error Handling

API responses include error information when requests fail:

```xml
<Error>
    <ErrorCode>int</ErrorCode>
    <ErrorDescription>string</ErrorDescription>
</Error>
```

**Common Error Codes:**
| Code | Description |
|------|-------------|
| 0 | Success |
| 1 | Invalid Ticket |
| 2 | Ticket Expired |
| 3 | Invalid Tracking Number |
| 4 | Shipment Not Found |
| 5 | Service Unavailable |

---

## Python SOAP Client Example

```python
from zeep import Client
from zeep.transports import Transport
from requests import Session

# Create session and client
session = Session()
transport = Transport(session=session)
client = Client(
    'https://api.ezyparcels.com/ezy2ship/api.wsdl',
    transport=transport
)

# Generate ticket
ticket = generate_ticket(
    customer_id=108,
    username='your_username',
    password='your_password',
    aes_key='your_aes_key'
)

# Get shipment info
result = client.service.getShipmentsInfo(
    ticket=ticket,
    trackingNumbers=['TRACKING123', 'TRACKING456']
)

# Process results
for shipment in result:
    print(f"Tracking: {shipment.TrackingNumber}")
    for event in shipment.TrackTrace:
        print(f"  {event.EventDate} {event.EventTime} - {event.EventName}")
```

---

## Rate Limiting

- Maximum 100 tracking numbers per `getShipmentsInfo` request
- Rate limit: 60 requests per minute
- Recommended polling interval: 15 minutes for tracking updates
