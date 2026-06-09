"""Education v26: Match debug_js.py settings exactly, then interact with autocomplete."""
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
    logs = []
    page.on("console", lambda m: logs.append(f"[{m.type}] {m.text[:200]}"))
    page.on("pageerror", lambda e: logs.append(f"[ERROR] {str(e)[:200]}"))

    # === LOGIN ===
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
    print(f"Logged in: {'login' not in page.url}, URL: {page.url}")

    # === NAVIGATE ===
    logs.clear()
    page.goto("https://github.com/settings/education/developer_pack_applications/new", timeout=120000, wait_until="networkidle")
    print(f"Page URL after nav: {page.url}")
    page.wait_for_timeout(10000)

    # Check JS
    info = page.evaluate('''() => ({
        scripts: document.querySelectorAll('script[src]').length,
        ce: {
            rp: !!customElements.get('react-partial'),
            ac: !!customElements.get('auto-complete'),
            tf: !!customElements.get('turbo-frame'),
        },
        perf: performance.getEntriesByType('resource').length,
    })''')
    print(f"Scripts: {info['scripts']}, CE: {info['ce']}, Perf: {info['perf']}")

    # Check if React partial rendered
    rp_html = page.evaluate('''() => {
        const rp = document.querySelector('react-partial[partial-name="education-schools-auto-complete"]');
        if (!rp) return "not found";
        const root = rp.querySelector('[data-target="react-partial.reactRoot"]');
        return root ? root.innerHTML.substring(0, 500) : "no root";
    }''')
    print(f"React root: {rp_html[:300]}")

    # Check autocomplete element details
    ac_info = page.evaluate('''() => {
        const ac = document.querySelector('auto-complete');
        if (!ac) return "not found";
        return {
            src: ac.getAttribute('src'),
            forAttr: ac.getAttribute('for'),
            outerHTML: ac.outerHTML.substring(0, 500),
            childCount: ac.children.length,
        };
    }''')
    print(f"Auto-complete: {json.dumps(ac_info, indent=2)[:400]}")

    # Try clicking student radio
    page.evaluate('''() => {
        const r = document.querySelector('input[value="student"]');
        if (r) {r.click(); r.dispatchEvent(new Event('change', {bubbles: true}));}
    }''')
    page.wait_for_timeout(1000)

    # Find the search input
    search = page.query_selector('#js-school-name-search')
    if search:
        search.click()
        page.wait_for_timeout(500)

        # Listen for responses
        resp_data = []
        def on_resp(r):
            if 'school' in r.url.lower():
                try: body = r.text()
                except: body = '<error>'
                resp_data.append({'url': r.url, 'status': r.status, 'body': body[:300]})
        page.on("response", on_resp)

        # Type slowly
        page.keyboard.type("Univer", delay=150)
        page.wait_for_timeout(3000)

        print(f"\nSchool responses: {len(resp_data)}")
        for r in resp_data:
            print(f"  {r['status']} {r['url'][:100]}")
            print(f"  Body: {r['body'][:200]}")

        # Check dropdown
        dropdown = page.evaluate('''() => {
            const list = document.getElementById('js-school-name-list');
            const items = list ? list.querySelectorAll('[data-autocomplete-value]') : [];
            return {count: items.length, listId: list?.id, listHTML: list?.innerHTML?.substring(0, 500)};
        }''')
        print(f"Dropdown: {json.dumps(dropdown, indent=2)[:400]}")

        # If 0 responses, try dispatching input event manually
        if len(resp_data) == 0:
            print("\n=== Trying manual input event dispatch ===")
            page.evaluate('''() => {
                const input = document.getElementById('js-school-name-search');
                input.dispatchEvent(new Event('input', {bubbles: true}));
                input.dispatchEvent(new InputEvent('input', {bubbles: true, data: 'Univer', inputType: 'insertText'}));
            }''')
            page.wait_for_timeout(3000)
            print(f"  Responses after dispatch: {len(resp_data)}")
    else:
        print("Search input not found!")

    # Print console logs
    print(f"\nConsole logs ({len(logs)}):")
    for l in logs[:20]:
        print(f"  {l}")

    browser.close()
print("Done!")
