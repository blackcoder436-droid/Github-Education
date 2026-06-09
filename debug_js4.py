"""Debug v4: Check why HEAD is empty, use 'load' instead of 'networkidle', dump raw response."""
import os, sys, json
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
import pyotp
load_dotenv()

USERNAME = os.environ['GITHUB_USERNAME']
PASSWORD = os.environ['GITHUB_PASSWORD']
TOTP_SECRET = "SFDHLAA7MDH2S7TN"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
    )
    page = context.new_page()

    # Intercept the education page response to see raw HTML
    edu_response_body = [None]
    edu_response_headers = [None]
    def on_response(response):
        if 'developer_pack_applications/new' in response.url:
            try:
                edu_response_body[0] = response.text()
                edu_response_headers[0] = response.headers
            except: pass
    page.on("response", on_response)

    # Login
    page.goto("https://github.com/login", timeout=60000, wait_until="load")
    page.wait_for_timeout(2000)
    if "login" in page.url:
        page.fill('#login_field', USERNAME)
        page.fill('#password', PASSWORD)
        page.click('input[name="commit"]')
        page.wait_for_timeout(5000)
        if "two-factor" in page.url or "sessions" in page.url:
            otp = pyotp.TOTP(TOTP_SECRET).now()
            for sel in ['#app_totp', 'input[name="app_otp"]', 'input[name="otp"]']:
                f = page.query_selector(sel)
                if f: f.fill(otp); break
            page.wait_for_timeout(500)
            try: page.click('button[type="submit"]', timeout=5000)
            except: pass
            page.wait_for_load_state("load", timeout=30000)
            page.wait_for_timeout(3000)
    print(f"Logged in: {'login' not in page.url}")

    # Check homepage JS first
    home_info = page.evaluate('''() => ({
        scripts: document.querySelectorAll('script[src]').length,
        headLen: document.head.innerHTML.length,
        title: document.title,
        url: location.href,
    })''')
    print(f"Home page: scripts={home_info['scripts']}, headLen={home_info['headLen']}, title='{home_info['title']}'")

    # Navigate to education form with 'load'
    resp = page.goto("https://github.com/settings/education/developer_pack_applications/new", timeout=120000, wait_until="load")
    print(f"\nResponse status: {resp.status if resp else 'None'}")
    
    # Check response headers
    if edu_response_headers[0]:
        ct = edu_response_headers[0].get('content-type', 'unknown')
        turbo = edu_response_headers[0].get('x-turbo-frame', 'none')
        print(f"Content-Type: {ct}")
        print(f"X-Turbo-Frame: {turbo}")
        # Print all interesting headers
        for k, v in edu_response_headers[0].items():
            if k.startswith('x-') or 'turbo' in k.lower() or 'frame' in k.lower():
                print(f"  {k}: {v}")

    # Check raw response body
    if edu_response_body[0]:
        raw = edu_response_body[0]
        print(f"\nRaw response length: {len(raw)}")
        has_html_tag = '<html' in raw[:500].lower()
        has_head_tag = '<head' in raw[:500].lower()
        has_script = '<script' in raw
        has_turbo_stream = '<turbo-stream' in raw[:200]
        has_turbo_frame = '<turbo-frame' in raw[:200]
        print(f"Has <html>: {has_html_tag}, <head>: {has_head_tag}, <script>: {has_script}")
        print(f"Has turbo-stream: {has_turbo_stream}, turbo-frame: {has_turbo_frame}")
        print(f"First 500 chars of response:\n{raw[:500]}")
        print(f"\n...last 300 chars:\n{raw[-300:]}")
        
        # Count script tags in raw response
        import re
        script_tags = re.findall(r'<script[^>]*src="([^"]*)"', raw)
        print(f"\nScript tags in response: {len(script_tags)}")
        for s in script_tags[:5]:
            print(f"  {s[:100]}")

    # Wait 20s for JS to load
    print("\nWaiting 20s for JS...")
    page.wait_for_timeout(20000)

    after = page.evaluate('''() => ({
        scripts: document.querySelectorAll('script[src]').length,
        inlineScripts: document.querySelectorAll('script:not([src])').length,
        headLen: document.head.innerHTML.length,
        ce_rp: !!customElements.get('react-partial'),
        ce_ac: !!customElements.get('auto-complete'),
        ce_tf: !!customElements.get('turbo-frame'),
        perf: performance.getEntriesByType('resource').length,
        title: document.title,
        url: location.href,
    })''')
    print(f"After wait: scripts={after['scripts']}, inline={after['inlineScripts']}, headLen={after['headLen']}")
    print(f"CE: rp={after['ce_rp']}, ac={after['ce_ac']}, tf={after['ce_tf']}")
    print(f"Perf: {after['perf']}, Title: '{after['title']}'")

    browser.close()
print("Done!")
