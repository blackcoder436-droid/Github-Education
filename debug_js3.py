"""Debug v3: First load full GitHub page with all scripts, then navigate to education form."""
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
    print(f"After login URL: {page.url}")

    # First: go to settings (full page with all JS)
    page.goto("https://github.com/settings", timeout=60000, wait_until="networkidle")
    page.wait_for_timeout(5000)
    
    before = page.evaluate('''() => ({
        scripts: document.querySelectorAll('script[src]').length,
        headLen: document.head.innerHTML.length,
        ce_rp: !!customElements.get('react-partial'),
        ce_ac: !!customElements.get('auto-complete'),
        ce_tf: !!customElements.get('turbo-frame'),
        title: document.title,
    })''')
    print(f"\nSettings page: scripts={before['scripts']}, head={before['headLen']}, ce_rp={before['ce_rp']}, ce_ac={before['ce_ac']}, ce_tf={before['ce_tf']}")
    print(f"Title: {before['title']}")

    # Now navigate to education form via Turbo (click link or use turbo navigation)
    print("\n=== Navigating to education form ===")
    
    # Method 1: Use window.location to force full page load
    resp = page.goto("https://github.com/settings/education/developer_pack_applications/new", timeout=120000, wait_until="networkidle")
    page.wait_for_timeout(10000)

    after = page.evaluate('''() => ({
        scripts: document.querySelectorAll('script[src]').length,
        headLen: document.head.innerHTML.length,
        ce_rp: !!customElements.get('react-partial'),
        ce_ac: !!customElements.get('auto-complete'),
        ce_tf: !!customElements.get('turbo-frame'),
        title: document.title,
        url: location.href,
        bodyLen: document.body.innerHTML.length,
        perf: performance.getEntriesByType('resource').length,
    })''')
    print(f"Education page: scripts={after['scripts']}, head={after['headLen']}, ce={after['ce_rp']}/{after['ce_ac']}/{after['ce_tf']}")
    print(f"Title: {after['title']}, URL: {after['url']}")
    print(f"Body: {after['bodyLen']}, Perf: {after['perf']}")

    # If still no scripts, try method 2: navigate via Turbo.visit
    if after['scripts'] == 0:
        print("\n=== Still no scripts. Trying Turbo.visit from settings ===")
        page.goto("https://github.com/settings", timeout=60000, wait_until="networkidle")
        page.wait_for_timeout(5000)
        
        # Check if Turbo is available
        has_turbo = page.evaluate('typeof Turbo !== "undefined"')
        print(f"Turbo available: {has_turbo}")

        if has_turbo:
            # Use Turbo.visit to navigate
            page.evaluate('Turbo.visit("/settings/education/developer_pack_applications/new")')
            page.wait_for_timeout(15000)
        else:
            # Try clicking a link instead
            page.evaluate('''() => {
                const a = document.createElement('a');
                a.href = '/settings/education/developer_pack_applications/new';
                a.textContent = 'Go';
                document.body.appendChild(a);
                a.click();
            }''')
            page.wait_for_timeout(15000)

        after2 = page.evaluate('''() => ({
            scripts: document.querySelectorAll('script[src]').length,
            headLen: document.head.innerHTML.length,
            ce_rp: !!customElements.get('react-partial'),
            ce_ac: !!customElements.get('auto-complete'),
            ce_tf: !!customElements.get('turbo-frame'),
            title: document.title,
            url: location.href,
            bodyLen: document.body.innerHTML.length,
            perf: performance.getEntriesByType('resource').length,
        })''')
        print(f"After Turbo: scripts={after2['scripts']}, head={after2['headLen']}, ce={after2['ce_rp']}/{after2['ce_ac']}/{after2['ce_tf']}")
        print(f"URL: {after2['url']}, Body: {after2['bodyLen']}, Perf: {after2['perf']}")

        # Check React partial
        rp = page.evaluate('''() => {
            const rp = document.querySelector('react-partial[partial-name="education-schools-auto-complete"]');
            if (!rp) return "not found";
            const root = rp.querySelector('[data-target="react-partial.reactRoot"]');
            return {
                html: root?.innerHTML?.substring(0, 200) || 'empty',
                childCount: root?.children?.length || 0,
            };
        }''')
        print(f"React partial: {rp}")

        # Check autocomplete
        ac = page.query_selector('auto-complete')
        print(f"Auto-complete element: {ac is not None}")

    browser.close()
print("Done!")
