"""Quick test: schools API with different Accept headers."""
import os, json
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
import pyotp
load_dotenv()

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    page = context.new_page()

    # Login
    page.goto("https://github.com/login", timeout=60000, wait_until="load")
    page.wait_for_timeout(3000)
    if "login" in page.url:
        f = page.query_selector('#login_field')
        if f:
            f.fill(os.environ['GITHUB_USERNAME'])
            page.fill('#password', os.environ['GITHUB_PASSWORD'])
            page.wait_for_timeout(500)
            page.click('input[name="commit"]')
            page.wait_for_timeout(5000)
            if "two-factor" in page.url or "sessions" in page.url:
                otp = pyotp.TOTP("SFDHLAA7MDH2S7TN").now()
                for sel in ['#app_totp', 'input[name="otp"]']:
                    el = page.query_selector(sel)
                    if el: el.fill(otp); break
                page.wait_for_timeout(500)
                try: page.click('button[type="submit"]', timeout=5000)
                except: pass
                page.wait_for_load_state("load", timeout=30000)
                page.wait_for_timeout(3000)
    print(f"Logged in: {'login' not in page.url}")

    page.goto("https://github.com/settings/education/benefits", timeout=60000, wait_until="load")
    page.wait_for_timeout(3000)

    # Try different Accept headers for schools API
    accepts = [
        "text/fragment+html",
        "text/html",
        "application/json",
        "*/*",
        "text/vnd.turbo-stream.html",
        "text/html, application/xhtml+xml",
    ]
    for accept in accepts:
        result = page.evaluate(f'''async () => {{
            try {{
                const r = await fetch("/settings/education/developer_pack_applications/schools?q=SKT", {{
                    headers: {{"Accept": "{accept}"}},
                    credentials: "same-origin",
                }});
                const text = await r.text();
                return {{accept: "{accept}", status: r.status, len: text.length, body: text.substring(0, 300)}};
            }} catch(e) {{
                return {{accept: "{accept}", error: e.message}};
            }}
        }}''')
        print(f"\nAccept: {result.get('accept')}")
        print(f"  Status: {result.get('status', result.get('error'))}, Len: {result.get('len', '?')}")
        if result.get('body'):
            print(f"  Body: {result['body'][:200]!r}")

    browser.close()
print("\nDone!")
