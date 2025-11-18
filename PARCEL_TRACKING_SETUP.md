# Parcel Tracking Setup Guide

## Overview
The parcel tracking feature allows developer accounts to track parcels by scraping data from Ship24.com using Playwright. This is a free alternative to paid tracking APIs.

## Features
- **Single Parcel Tracking**: Track individual parcels by tracking number
- **Bulk Tracking**: Track up to 10 parcels simultaneously
- **Carrier Auto-detection**: Ship24 automatically detects carriers
- **Real-time Results**: Get current tracking status, location, and event history
- **Developer-Only Access**: Restricted to users with Developer account type

## Installation

### 1. Playwright is Already Installed
The Python Playwright package has been installed in your virtual environment:
```bash
pip3 install playwright  # Already done
```

### 2. Install Browser Drivers
**IMPORTANT**: You need to install the Chromium browser for Playwright to work:

```bash
source venv/bin/activate
playwright install chromium
```

**Note**: If you encounter disk space issues during installation, you may need to:
- Free up disk space on your system
- Or install just the dependencies: `playwright install-deps chromium`

### 3. Verify Installation
To verify Playwright is working:
```bash
source venv/bin/activate
python3 -c "from playwright.sync_api import sync_playwright; print('Playwright installed successfully')"
```

## Usage

### Access the Page
1. Log in with a **Developer** account
2. Navigate to **Parcel Tracking** from the main navigation menu
3. The page is available at: `/parcel-tracking/`

### Track a Single Parcel
1. Enter the tracking number in the input field
2. Optionally select a carrier (or leave as "Auto-detect")
3. Click "Track Parcel"
4. Results will display below with:
   - Tracking number
   - Carrier name
   - Current status
   - Current location
   - Estimated delivery date
   - Tracking event history

### Track Multiple Parcels
1. Enter tracking numbers in the bulk textarea (one per line)
2. Maximum 10 tracking numbers at once
3. Click "Track All"
4. Results will display for each tracking number

## Technical Details

### Files Created
1. **Backend**:
   - `/utils/ship24_tracker.py` - Ship24 scraping utility using Playwright
   - `/routes/parcel_tracking.py` - Flask routes for parcel tracking

2. **Frontend**:
   - `/templates/parcel_tracking/index.html` - Parcel tracking UI

3. **Configuration**:
   - Updated `/app.py` to register the parcel_tracking blueprint
   - Updated `/templates/base.html` to add navigation link for developers

### API Endpoints
All endpoints require developer authentication:

- **GET** `/parcel-tracking/` - Main tracking page
- **POST** `/parcel-tracking/track` - Track single parcel
  ```json
  {
    "tracking_number": "1234567890",
    "carrier": "dhl"  // optional
  }
  ```

- **POST** `/parcel-tracking/track/bulk` - Track multiple parcels
  ```json
  {
    "tracking_numbers": ["1234567890", "0987654321"]
  }
  ```

- **GET** `/parcel-tracking/carriers` - Get list of supported carriers

### How It Works
1. User enters tracking number
2. Backend launches headless Chromium browser using Playwright
3. Navigates to Ship24.com tracking page
4. Fills in tracking number and clicks track
5. Waits for JavaScript content to load
6. Scrapes tracking information from the page
7. Returns structured data to frontend
8. Frontend displays results in a beautiful UI

### Supported Carriers
- DHL Express
- FedEx
- UPS
- USPS
- Singapore Post
- BlueDart
- DTDC
- Aramex
- TNT
- DPD
- And many more (Ship24 supports 1,500+ carriers)

## Troubleshooting

### "Failed to download Chromium" Error
This means there's not enough disk space. Solutions:
1. Free up disk space on your system
2. Use a different browser: Edit `ship24_tracker.py` and change `p.chromium` to `p.firefox` or `p.webkit`
3. Install browsers manually: `playwright install firefox`

### "Playwright not found" Error
Make sure you're running in the virtual environment:
```bash
source venv/bin/activate
```

### Tracking Returns No Results
Possible causes:
1. Tracking number is invalid or doesn't exist
2. Ship24.com changed their HTML structure (selectors need updating)
3. Network timeout - try again
4. Ship24 may require captcha verification (use headless=False to debug)

### Access Denied Error
Only users with `user_type = 'DEVELOPER'` can access this feature. Check:
```sql
SELECT username, user_type FROM users WHERE user_type = 'DEVELOPER';
```

## Maintenance

### Updating Selectors
If Ship24 changes their website structure, you may need to update the CSS selectors in `/utils/ship24_tracker.py`:

```python
async def _extract_tracking_data(self, page) -> Dict:
    # Update these selectors if Ship24 changes their HTML
    carrier_element = await page.query_selector('[class*="carrier"]')
    status_element = await page.query_selector('[class*="status"]')
    # ... etc
```

### Performance Optimization
- Each tracking request launches a browser instance (resource intensive)
- Consider implementing caching for recently tracked parcels
- Bulk tracking processes parcels sequentially to avoid resource issues
- For production, consider setting up a queue system (Celery + Redis)

## Security Considerations
- This feature is restricted to developer accounts only
- No sensitive data is stored
- Browser runs in headless mode (no UI)
- No user data is sent to Ship24 beyond the tracking number

## Future Enhancements
- [ ] Cache tracking results for 5-10 minutes
- [ ] Add tracking history database
- [ ] Support for more tracking websites
- [ ] Async bulk tracking for better performance
- [ ] Export tracking results to CSV
- [ ] Email notifications for tracking updates
- [ ] Integration with ticket tracking numbers

## Cost
**FREE** - This solution uses web scraping instead of paid APIs. No API keys or subscriptions required.

## Alternatives Considered
1. **Firecrawl**: Paid service, costs add up quickly
2. **TrackingMore API**: Free tier limited to 100 calls/month
3. **Ship24 API**: Free tier limited to 100 calls/month
4. **Playwright** (chosen): Free, unlimited tracking, no API required

---

**For issues or questions, contact the development team.**
