"""Education v17: Query schools API to find schools with enrollment data."""
import os, sys, json
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
import pyotp
load_dotenv()

USERNAME = os.environ['GITHUB_USERNAME']
PASSWORD = os.environ['GITHUB_PASSWORD']
TOTP_SECRET = "SFDHLAA7MDH2S7TN"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=[
        '--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream',
    ])
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
        permissions=["camera"],
    )
    page = context.new_page()

    # === LOGIN ===
    print("=== Login ===")
    page.goto("https://github.com/login", timeout=60000, wait_until="load")
    page.wait_for_timeout(3000)
    if "login" in page.url:
        login_field = page.query_selector('#login_field')
        if login_field:
            login_field.fill(USERNAME)
            page.fill('#password', PASSWORD)
            page.wait_for_timeout(500)
            page.click('input[name="commit"]')
            page.wait_for_timeout(5000)
            cur = page.url
            if "two-factor" in cur or "two_factor" in cur or "sessions" in cur:
                otp = pyotp.TOTP(TOTP_SECRET).now()
                for sel in ['#app_totp', 'input[name="app_otp"]', 'input[name="otp"]']:
                    f = page.query_selector(sel)
                    if f: f.fill(otp); break
                page.wait_for_timeout(500)
                try: page.click('button[type="submit"]', timeout=5000)
                except: pass
                page.wait_for_load_state("load", timeout=30000)
                page.wait_for_timeout(3000)
    print(f"  Logged in: {'login' not in page.url}")

    page.goto("https://github.com/settings/education/developer_pack_applications/new", timeout=120000, wait_until="load")
    page.wait_for_timeout(5000)

    # === Query schools ===
    print("\n=== Schools API Queries ===")
    queries = [
        "SKT International",
        "University of Yangon",
        "Yangon Technological",
        "University of Computer Studies",
        "Mandalay",
        "Myanmar",
        "Stanford",
        "Harvard",
    ]

    for q in queries:
        result = page.evaluate('''async (query) => {
            const r = await fetch("/settings/education/developer_pack_applications/schools?q=" + encodeURIComponent(query), {
                headers: {"Accept": "text/fragment+html"},
                credentials: "same-origin",
            });
            const html = await r.text();
            
            // Parse all school items
            const doc = new DOMParser().parseFromString('<div>' + html + '</div>', 'text/html');
            const items = doc.querySelectorAll('[data-selected-school-id]');
            const schools = [];
            items.forEach(item => {
                const attrs = {};
                Array.from(item.attributes).forEach(a => {
                    attrs[a.name] = a.value;
                });
                schools.push(attrs);
            });
            
            return {
                status: r.status,
                schoolCount: items.length,
                schools: schools,
                rawHtml: html.substring(0, 2000),
            };
        }''', q)
        
        print(f"\n  Query: '{q}' -> {result.get('schoolCount', 0)} schools")
        for s in result.get('schools', []):
            name = s.get('data-school-name', 'unknown')
            sid = s.get('data-selected-school-id', '?')
            tfa = s.get('data-two-factor-required', '?')
            cam = s.get('data-camera-required', '?')
            dist = s.get('data-override-distance-limit', '?')
            domains = s.get('data-email-domains', '')[:100]
            # Print ALL attributes to find enrollment_size
            all_keys = sorted(s.keys())
            print(f"    [{sid}] {name}")
            print(f"      2fa={tfa} camera={cam} dist_override={dist}")
            print(f"      domains={domains[:80]}")
            print(f"      ALL attrs: {all_keys}")

        # Also print raw HTML for first result to see full structure
        if result.get('schoolCount', 0) > 0 and q == queries[0]:
            print(f"\n  Raw HTML (first query): {result.get('rawHtml', '')[:800]}")

    browser.close()

print("\nDone!")
