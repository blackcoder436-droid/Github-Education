"""Quick fix: correct field names and test school API."""
import os, sys, json, time
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
import pyotp
load_dotenv()

USERNAME = os.environ['GITHUB_USERNAME']
PASSWORD = os.environ['GITHUB_PASSWORD']
TOTP_SECRET = "SFDHLAA7MDH2S7TN"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36")
    page = context.new_page()

    # Login
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

    # Nav to benefits page for cookies
    page.goto("https://github.com/settings/education/benefits", timeout=120000, wait_until="load")
    page.wait_for_timeout(3000)

    # Test schools API
    print("\n=== Schools API ===")
    for q in ["SKT", "SKT International", "MIT", "Stanford"]:
        result = page.evaluate(f'''async () => {{
            const r = await fetch("/settings/education/developer_pack_applications/schools?q={q}", {{
                headers: {{"Accept": "text/html"}},
                credentials: "same-origin",
            }});
            return {{status: r.status, body: (await r.text()).substring(0, 1000)}};
        }}''')
        print(f"\n  Search '{q}': status={result['status']}")
        # Parse the HTML response for list items
        items = page.evaluate('''(html) => {
            const doc = new DOMParser().parseFromString(html, 'text/html');
            const items = doc.querySelectorAll('[role="option"], li, [data-autocomplete-value]');
            return Array.from(items).slice(0, 5).map(i => ({
                text: i.textContent.trim().substring(0, 100),
                value: i.dataset?.autocompleteValue || i.getAttribute('data-autocomplete-value') || '',
                html: i.outerHTML.substring(0, 200),
            }));
        }''', result['body'])
        print(f"  Items: {len(items)}")
        for item in items:
            print(f"    {item['text']!r} (value={item['value']!r})")
        if not items:
            print(f"  Raw: {result['body'][:300]}")

    # Fetch the initial form to see ALL fields
    print("\n=== Initial form fields ===")
    form_html = page.evaluate('''async () => {
        const r = await fetch("/settings/education/developer_pack_applications/new", {
            headers: {"Accept": "text/html", "Turbo-Frame": "dev-pack-form"},
            credentials: "same-origin",
        });
        return await r.text();
    }''')

    # Get ALL form elements including radios, selects, hidden
    all_fields = page.evaluate('''(html) => {
        const doc = new DOMParser().parseFromString(html, 'text/html');
        const form = doc.querySelector('form');
        if (!form) return {error: "no form"};
        const fields = [];
        form.querySelectorAll('input, select, textarea, button').forEach(el => {
            fields.push({
                tag: el.tagName,
                type: el.type || '',
                name: el.name || '',
                id: el.id || '',
                value: (el.value || '').substring(0, 80),
                checked: el.checked || false,
                required: el.required || false,
                options: el.tagName === 'SELECT' ?
                    Array.from(el.options).map(o => ({v: o.value, t: o.textContent.trim().substring(0, 50)})) : [],
            });
        });
        // Also get labels
        const labels = Array.from(form.querySelectorAll('label')).map(l => ({
            for: l.htmlFor,
            text: l.textContent.trim().substring(0, 80),
        }));
        return {fields, labels};
    }''', form_html)

    if isinstance(all_fields, dict) and 'fields' in all_fields:
        print(f"  Fields ({len(all_fields['fields'])}):")
        for f in all_fields['fields']:
            checked = " CHECKED" if f['checked'] else ""
            opts = f" opts={[o['t'] for o in f['options']]}" if f['options'] else ""
            print(f"    <{f['tag']} name={f['name']!r} type={f['type']!r} value={f['value']!r}{checked}{opts}>")
        print(f"\n  Labels ({len(all_fields['labels'])}):")
        for l in all_fields['labels']:
            print(f"    for={l['for']!r}: {l['text']!r}")
    else:
        print(f"  {json.dumps(all_fields)}")

    browser.close()
print("\nDone!")
