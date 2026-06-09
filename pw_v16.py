"""Education v16: Navigate to form page, type to trigger autocomplete, 
intercept school list response, find schools with enrollment data."""
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

    # === Go directly to form page ===
    print("\n=== Navigate to Form ===")
    page.goto("https://github.com/settings/education/developer_pack_applications/new", timeout=120000, wait_until="load")
    page.wait_for_timeout(5000)
    print(f"  URL: {page.url}")

    # First try fetching schools API from this page context
    print("\n=== Schools API from form page ===")
    api_test = page.evaluate('''async () => {
        const results = {};
        const queries = ["University", "MIT", "Yangon"];
        for (const q of queries) {
            try {
                const r = await fetch("/settings/education/developer_pack_applications/schools?q=" + encodeURIComponent(q), {
                    headers: {"Accept": "text/fragment+html"},
                    credentials: "same-origin",
                });
                const text = await r.text();
                results[q] = {status: r.status, contentType: r.headers.get('content-type'), body: text.substring(0, 500)};
            } catch(e) {
                results[q] = {error: e.message};
            }
        }
        return results;
    }''')
    for q, res in api_test.items():
        print(f"\n  Query: {q}")
        print(f"    Status: {res.get('status', 'ERR')}, CT: {res.get('contentType', '')}")
        print(f"    Body: {res.get('body', '')[:300]}")

    # === Intercept network and type to trigger autocomplete ===
    print("\n=== Typing in autocomplete ===")
    
    # Set up request/response interception
    school_responses = []
    def on_response(response):
        if 'school' in response.url.lower():
            try:
                body = response.text()
            except:
                body = '<error reading>'
            school_responses.append({
                'url': response.url,
                'status': response.status,
                'ct': response.headers.get('content-type', ''),
                'body': body[:2000],
            })
    page.on("response", on_response)

    # Click on student radio first
    student_radio = page.query_selector('input[name="dev_pack_form[application_type]"][value="student"]')
    if student_radio:
        student_radio.click()
        page.wait_for_timeout(1000)
        print("  Clicked student radio")

    # Type in school search - character by character
    school_input = page.query_selector('#js-school-name-search')
    if school_input:
        school_input.click()
        page.wait_for_timeout(500)
        # Type slowly to trigger autocomplete
        page.keyboard.type("Univer", delay=100)
        page.wait_for_timeout(3000)

        print(f"  School responses collected: {len(school_responses)}")
        for resp in school_responses:
            print(f"    {resp['status']} {resp['url']}")
            print(f"    CT: {resp['ct']}")
            print(f"    Body: {resp['body'][:400]}")

        # Check what's in the dropdown list
        list_content = page.evaluate('''() => {
            const list = document.getElementById('js-school-name-list');
            if (!list) return {error: "no list"};
            const items = list.querySelectorAll('li, [role="option"]');
            const results = [];
            items.forEach(item => {
                results.push({
                    text: item.textContent.trim().substring(0, 200),
                    value: item.getAttribute('data-autocomplete-value') || item.getAttribute('value') || '',
                    attrs: Array.from(item.attributes).map(a => a.name + '=' + (a.value||'').substring(0, 50)),
                });
            });
            return {html: list.innerHTML.substring(0, 1000), itemCount: items.length, items: results.slice(0, 10)};
        }''')
        print(f"\n  Dropdown content: {list_content}")

        # Clear and try again with different text
        school_input.fill("")
        page.wait_for_timeout(500)
        school_input.click()
        page.keyboard.type("Yangon", delay=100)
        page.wait_for_timeout(3000)

        print(f"\n  After 'Yangon' - responses: {len(school_responses)}")
        for resp in school_responses[len(school_responses)-5:]:
            print(f"    {resp['status']} {resp['url']}")
            print(f"    Body: {resp['body'][:400]}")

        list_content2 = page.evaluate('''() => {
            const list = document.getElementById('js-school-name-list');
            if (!list) return {error: "no list"};
            const items = list.querySelectorAll('li, [role="option"]');
            const results = [];
            items.forEach(item => {
                results.push({
                    text: item.textContent.trim().substring(0, 200),
                    value: item.getAttribute('data-autocomplete-value') || '',
                    allData: {},
                });
                // Get all data attributes
                Array.from(item.attributes).forEach(a => {
                    if (a.name.startsWith('data-')) {
                        results[results.length-1].allData[a.name] = a.value.substring(0, 100);
                    }
                });
            });
            return {itemCount: items.length, items: results.slice(0, 10)};
        }''')
        print(f"  Dropdown: {list_content2}")

        # Try selecting a school from the list
        if list_content2.get('itemCount', 0) > 0:
            print("\n  Clicking first result...")
            first_item = page.query_selector('#js-school-name-list li, #js-school-name-list [role="option"]')
            if first_item:
                first_item.click()
                page.wait_for_timeout(1000)
                # Check what got set in hidden input
                hidden_val = page.evaluate('''() => {
                    const inputs = {};
                    document.querySelectorAll('input').forEach(el => {
                        if (el.name && el.name.includes('school')) {
                            inputs[el.name + '_' + el.type] = el.value.substring(0, 200);
                        }
                    });
                    return inputs;
                }''')
                print(f"  Hidden values after selection: {hidden_val}")
    else:
        print("  School input not found!")

    browser.close()

print("\nDone!")
