#!/usr/bin/env python3
"""
Quick proxy tester for tracking sites
Tests if proxies can reach Ship24 without getting blocked by CloudFront
"""

import asyncio
import sys

# List of ISP-range proxies to test
PROXIES_TO_TEST = [
    'http://113.177.204.26:8080',      # Vietnam ISP
    'http://121.167.212.146:8081',     # Korea ISP
    'http://175.208.236.55:8044',      # Korea ISP
    'http://182.52.25.243:8080',       # Thailand ISP
    'http://186.103.130.91:8080',      # Chile ISP
    'http://190.113.40.202:999',       # Latin America ISP
    'http://200.24.159.230:8080',      # Latin America ISP
    'http://87.120.166.178:8080',      # Europe ISP
    'http://89.43.132.75:8080',        # Europe ISP
    'http://41.223.119.156:3128',      # Africa ISP
]

async def test_proxy(proxy_url: str, timeout: int = 15):
    """Test if a proxy can reach Ship24 without CloudFront blocking"""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("Playwright not installed. Run: pip install playwright && playwright install chromium")
        return None

    test_url = "https://www.ship24.com"

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )

            context = await browser.new_context(
                proxy={'server': proxy_url},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )

            page = await context.new_page()

            print(f"  Testing {proxy_url}...", end=" ", flush=True)

            response = await page.goto(test_url, wait_until='domcontentloaded', timeout=timeout * 1000)

            if response:
                status = response.status

                # Get page content to check for CloudFront block
                content = await page.content()

                await browser.close()

                if status == 403 or 'cloudfront' in content.lower() or 'error' in content[:500].lower():
                    print(f"BLOCKED (status={status})")
                    return False
                elif status == 200:
                    print(f"SUCCESS! (status={status})")
                    return True
                else:
                    print(f"UNKNOWN (status={status})")
                    return None
            else:
                await browser.close()
                print("NO RESPONSE")
                return False

    except asyncio.TimeoutError:
        print("TIMEOUT")
        return False
    except Exception as e:
        error_msg = str(e)[:50]
        print(f"ERROR: {error_msg}")
        return False

async def main():
    print("=" * 60)
    print("Proxy Tester for Ship24 Tracking")
    print("=" * 60)
    print()

    working_proxies = []

    for proxy in PROXIES_TO_TEST:
        result = await test_proxy(proxy)
        if result is True:
            working_proxies.append(proxy)
        # Small delay between tests
        await asyncio.sleep(1)

    print()
    print("=" * 60)
    print("RESULTS")
    print("=" * 60)

    if working_proxies:
        print(f"\nWorking proxies ({len(working_proxies)}):")
        for proxy in working_proxies:
            print(f"  {proxy}")
        print(f"\nAdd to your WSGI file:")
        print(f"  os.environ['TRACKING_PROXY_URL'] = '{working_proxies[0]}'")
    else:
        print("\nNo working free proxies found.")
        print("Recommendation: Use fallback mode (remove TRACKING_PROXY_URL)")
        print("The fallback provides tracking links that users can click.")

if __name__ == '__main__':
    asyncio.run(main())
