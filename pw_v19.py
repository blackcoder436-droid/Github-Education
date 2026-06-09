"""Education v19: Full DOM interaction approach.
Navigate to form, interact with autocomplete, submit via Turbo."""
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
        geolocation={"latitude": 16.8661, "longitude": 96.1951},
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

    # === Navigate to form ===
    print("\n=== Navigate to form ===")
    page.goto("https://github.com/settings/education/developer_pack_applications/new", timeout=120000, wait_until="load")
    page.wait_for_timeout(5000)
    print(f"  URL: {page.url}")

    # === Click Student radio ===
    print("\n=== Step 1: Fill form ===")
    student_radio = page.query_selector('input[name="dev_pack_form[application_type]"][value="student"]')
    if student_radio:
        # Click the label or parent since radio might be hidden
        student_label = page.query_selector('label:has(input[value="student"])')
        if student_label:
            student_label.click()
        else:
            student_radio.click()
        page.wait_for_timeout(1000)
        print("  Selected student")
    else:
        print("  Student radio not found!")

    # === Type in school search and trigger autocomplete ===
    school_search = page.query_selector('#js-school-name-search')
    if school_search:
        # Focus and type
        school_search.click()
        page.wait_for_timeout(500)

        # Listen for responses
        school_api_responses = []
        def on_response(resp):
            if 'schools' in resp.url:
                try:
                    body = resp.text()
                except:
                    body = ''
                school_api_responses.append({'url': resp.url, 'status': resp.status, 'body': body[:2000]})
        page.on("response", on_response)

        # Type character by character
        page.keyboard.type("University of Computer Studies, Yang", delay=150)
        page.wait_for_timeout(3000)

        print(f"  Autocomplete API responses: {len(school_api_responses)}")
        for r in school_api_responses:
            print(f"    {r['status']} {r['url'][:100]}")

        # Check dropdown
        dropdown_items = page.evaluate('''() => {
            const list = document.getElementById('js-school-name-list');
            if (!list) return {error: "no list"};
            const items = [];
            list.querySelectorAll('[role="option"], li').forEach(el => {
                const attrs = {};
                Array.from(el.attributes).forEach(a => {
                    if (a.name.startsWith('data-')) attrs[a.name] = a.value.substring(0, 200);
                });
                items.push({
                    text: el.textContent.trim().substring(0, 100),
                    attrs
                });
            });
            return {itemCount: items.length, items: items.slice(0, 10), html: list.innerHTML.substring(0, 500)};
        }''')
        print(f"  Dropdown items: {dropdown_items.get('itemCount', 0)}")
        for item in dropdown_items.get('items', [])[:5]:
            print(f"    {item['text']} | {item.get('attrs', {}).get('data-selected-school-id', '?')}")

        # If no dropdown items, the autocomplete might not have triggered
        # Try dispatching input event manually
        if dropdown_items.get('itemCount', 0) == 0:
            print("\n  No dropdown items. Trying manual dispatch...")
            page.evaluate('''() => {
                const input = document.getElementById('js-school-name-search');
                input.dispatchEvent(new Event('input', {bubbles: true}));
                input.dispatchEvent(new Event('change', {bubbles: true}));
            }''')
            page.wait_for_timeout(3000)

            print(f"  API responses after dispatch: {len(school_api_responses)}")
            dropdown_items2 = page.evaluate('''() => {
                const list = document.getElementById('js-school-name-list');
                if (!list) return {error: "no list"};
                return {itemCount: list.querySelectorAll('[role="option"], li').length, html: list.innerHTML.substring(0, 500)};
            }''')
            print(f"  Dropdown after dispatch: {dropdown_items2}")

        # If still no items, try fetching autocomplete manually and injecting
        if dropdown_items.get('itemCount', 0) == 0:
            print("\n  Injecting autocomplete results manually...")
            inject_result = page.evaluate('''async () => {
                const q = document.getElementById('js-school-name-search').value;
                const r = await fetch("/settings/education/developer_pack_applications/schools?q=" + encodeURIComponent(q), {
                    headers: {"Accept": "text/fragment+html"},
                    credentials: "same-origin",
                });
                const html = await r.text();

                // Inject into the dropdown
                const list = document.getElementById('js-school-name-list');
                if (list) {
                    list.innerHTML = html;
                    list.showPopover && list.showPopover();
                }

                // Parse to find UCSY
                const doc = new DOMParser().parseFromString('<div>' + html + '</div>', 'text/html');
                const items = [];
                doc.querySelectorAll('[data-selected-school-id]').forEach(el => {
                    items.push({
                        id: el.getAttribute('data-selected-school-id'),
                        name: el.getAttribute('data-school-name'),
                        value: el.getAttribute('data-autocomplete-value'),
                    });
                });
                return {status: r.status, items, htmlLen: html.length};
            }''')
            print(f"  Injected {len(inject_result.get('items', []))} items")
            for item in inject_result.get('items', [])[:5]:
                print(f"    [{item['id']}] {item['name']}")

            # Click on the UCSY result
            ucsy_clicked = page.evaluate('''() => {
                const list = document.getElementById('js-school-name-list');
                const item = list.querySelector('[data-selected-school-id="7620"]');
                if (!item) return {error: "UCSY not found"};

                // Click it
                item.click();

                // Wait and check state
                return {
                    clicked: true,
                    hiddenSchoolName: document.querySelector('input.d-none[name="dev_pack_form[school_name]"]')?.value || '',
                    searchValue: document.getElementById('js-school-name-search')?.value || '',
                };
            }''')
            print(f"  UCSY click: {ucsy_clicked}")
            page.wait_for_timeout(2000)

            # Check what happened after clicking
            after_click = page.evaluate('''() => {
                const inputs = {};
                document.querySelectorAll('input').forEach(el => {
                    if (el.name && (el.name.includes('school') || el.name.includes('enrollment'))) {
                        inputs[el.name + '_' + (el.className || '')] = el.value.substring(0, 200);
                    }
                });
                return inputs;
            }''')
            print(f"  Inputs after click: {json.dumps(after_click, indent=2)}")

    # === Check if "Continue" button is available ===
    print("\n=== Looking for Continue/Submit button ===")
    buttons = page.evaluate('''() => {
        const btns = [];
        document.querySelectorAll('button, input[type="submit"]').forEach(el => {
            const text = el.textContent?.trim() || el.value || '';
            if (text.toLowerCase().includes('continue') || text.toLowerCase().includes('submit')) {
                btns.push({text: text.substring(0, 100), visible: el.offsetParent !== null, type: el.type, name: el.name || ''});
            }
        });
        return btns;
    }''')
    print(f"  Buttons: {buttons}")

    # === Set location, email and try to submit step 1 ===
    print("\n=== Setting remaining fields ===")
    # Set location
    page.evaluate('''() => {
        const lat = document.getElementById('dev_pack_form_latitude') || document.querySelector('input[name="dev_pack_form[latitude]"]');
        if (lat) lat.value = '16.8661';
        const lng = document.getElementById('dev_pack_form_longitude') || document.querySelector('input[name="dev_pack_form[longitude]"]');
        if (lng) lng.value = '96.1951';
        const loc = document.getElementById('js-developer-pack-application-location-shared-input') || document.querySelector('input[name="dev_pack_form[location_shared]"]');
        if (loc) loc.value = 'true';
    }''')

    # Check all form data that would be submitted
    form_data = page.evaluate('''() => {
        const form = document.querySelector('form[action="/settings/education/developer_pack_applications"]');
        if (!form) return {error: "no form"};
        const fd = new FormData(form);
        const data = {};
        for (const [key, value] of fd.entries()) {
            if (key === 'authenticity_token') continue;
            data[key] = typeof value === 'string' ? value.substring(0, 200) : value.name;
        }
        return data;
    }''')
    print(f"  Form data: {json.dumps(form_data, indent=2)}")

    # Intercept submission
    requests_captured = []
    def on_request(req):
        if 'developer_pack' in req.url and req.method == 'POST':
            requests_captured.append({
                'url': req.url,
                'method': req.method,
                'postData': req.post_data[:2000] if req.post_data else '',
            })
    page.on("request", on_request)

    # Try to submit
    continue_btn = page.query_selector('button:has-text("Continue")')
    if continue_btn:
        print("  Found Continue button, clicking...")
        try:
            continue_btn.click(timeout=5000)
            page.wait_for_timeout(5000)
            print(f"  Captured requests: {len(requests_captured)}")
            for r in requests_captured:
                print(f"    {r['method']} {r['url']}")
                print(f"    Body: {r['postData'][:300]}")
        except Exception as e:
            print(f"  Click failed: {e}")
    else:
        print("  No Continue button found")

    # Take a screenshot-equivalent: dump all visible text
    page_text = page.evaluate('document.body?.innerText?.substring(0, 1000) || ""')
    print(f"\n  Page text: {page_text[:500]}")

    browser.close()

print("\nDone!")
