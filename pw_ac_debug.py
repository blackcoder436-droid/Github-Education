"""Diagnose autocomplete: check network calls and try different searches."""
import os, sys, json, time
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
    )
    page = context.new_page()

    # Capture ALL network
    api_calls = []
    def on_response(resp):
        if "school" in resp.url.lower() or "autocomplete" in resp.url.lower() or "education" in resp.url.lower():
            body = ""
            try: body = resp.text()[:500]
            except: pass
            api_calls.append({
                "url": resp.url[:200],
                "status": resp.status,
                "body_len": len(body),
                "body_preview": body[:200],
            })
    page.on("response", on_response)

    # Login
    print("=== Login ===")
    page.goto("https://github.com/login", timeout=60000, wait_until="load")
    page.wait_for_timeout(3000)

    # Check if already logged in (redirected away from login)
    if "login" not in page.url:
        print(f"  Already logged in! (URL: {page.url})")
    else:
        login_field = page.query_selector('#login_field')
        if login_field:
            login_field.fill(USERNAME)
            page.fill('#password', PASSWORD)
            page.wait_for_timeout(500)
            page.click('input[name="commit"]')
            page.wait_for_timeout(5000)
            if "two-factor" in page.url or "two_factor" in page.url:
                otp = pyotp.TOTP(TOTP_SECRET).now()
                otp_field = page.query_selector('#app_totp')
                if otp_field: otp_field.fill(otp)
                else: page.fill('input[name="otp"]', otp)
                page.wait_for_timeout(500)
                try:
                    page.click('button[type="submit"]', timeout=5000)
                except Exception:
                    pass
                page.wait_for_load_state("load", timeout=30000)
                page.wait_for_timeout(3000)
        else:
            print(f"  No login field found. Page URL: {page.url}")
            page.screenshot(path="pw_ac_login.png")
    print(f"  Status: {'login' not in page.url} ({page.url})")

    # Navigate
    print("\n=== Navigate to education page ===")
    page.goto("https://github.com/settings/education/benefits", timeout=120000, wait_until="load")
    page.wait_for_timeout(10000)

    # Check page basics
    print(f"  URL: {page.url}")
    print(f"  Title: {page.title()}")
    body_len = page.evaluate('document.body?.innerHTML?.length || 0')
    print(f"  Body HTML length: {body_len}")

    # Check turbo-frame
    tf_info = page.evaluate('''(() => {
        const tf = document.querySelector('#dev-pack-form');
        if (!tf) return {exists: false};
        return {
            exists: true,
            tagName: tf.tagName,
            src: tf.getAttribute('src'),
            loading: tf.getAttribute('loading'),
            complete: tf.getAttribute('complete'),
            childCount: tf.childElementCount,
            innerHTML_len: tf.innerHTML?.length || 0,
            innerHTML_preview: tf.innerHTML?.substring(0, 300) || '',
        };
    })()''')
    print(f"  Turbo-frame: {json.dumps(tf_info, indent=2)}")

    if tf_info.get('exists') and tf_info.get('innerHTML_len', 0) < 100:
        print("  Turbo-frame empty! Forcing load...")
        # Scroll into view and set loading=eager
        page.evaluate('''(() => {
            const tf = document.querySelector('#dev-pack-form');
            tf.scrollIntoView({behavior:'instant', block:'center'});
            tf.loading = 'eager';
            if (tf.src) { const s = tf.src; tf.src = ''; tf.src = s; }
        })()''')
        page.wait_for_timeout(10000)
        tf_info2 = page.evaluate('''(() => {
            const tf = document.querySelector('#dev-pack-form');
            return {
                childCount: tf?.childElementCount || 0,
                innerHTML_len: tf?.innerHTML?.length || 0,
                innerHTML_preview: tf?.innerHTML?.substring(0, 300) || '',
            };
        })()''')
        print(f"  After force: {json.dumps(tf_info2, indent=2)}")

    # Wait for form
    print("\n=== Waiting for form ===")
    for attempt in range(20):
        if page.evaluate('!!document.querySelector("#dev-pack-form form")'):
            print(f"  Form found after {(attempt+1)*2}s")
            break
        page.wait_for_timeout(2000)
    else:
        print("  Form NOT found after 40s!")
        page.screenshot(path="pw_ac_noform.png")
        # Check what IS in dev-pack-form
        content = page.evaluate('document.querySelector("#dev-pack-form")?.innerHTML?.substring(0, 1000) || "EMPTY"')
        print(f"  Frame content: {content}")

    # Check form structure
    print("\n=== Form structure ===")
    form_info = page.evaluate('''(() => {
        const form = document.querySelector('#dev-pack-form form');
        if (!form) return {error: "no form"};
        const inputs = form.querySelectorAll('input, select, textarea');
        const result = [];
        inputs.forEach(i => {
            result.push({
                tag: i.tagName, type: i.type || '',
                name: i.name, id: i.id,
                value: (i.value || '').substring(0, 50),
                required: i.required,
            });
        });
        return result;
    })()''')
    if isinstance(form_info, list):
        for inp in form_info:
            print(f"  <{inp['tag']} name={inp['name']!r} id={inp['id']!r} type={inp['type']!r} value={inp['value']!r}>")
    else:
        print(f"  form_info = {json.dumps(form_info)}")

    # Check autocomplete component
    print("\n=== Autocomplete component ===")
    ac_info = page.evaluate('''(() => {
        const rp = document.querySelector('react-partial[partial-name="education-schools-auto-complete"]');
        if (!rp) return {error: "no react-partial"};
        const root = rp.querySelector('[data-target="react-partial.reactRoot"]');
        const result = {
            hasRoot: !!root,
            childCount: root?.childElementCount || 0,
            innerHTML: root?.innerHTML?.substring(0, 500) || '',
            dataAttrs: {},
        };
        // Check all data attributes on react-partial
        for (const attr of rp.attributes) {
            if (attr.name.startsWith('data-')) result.dataAttrs[attr.name] = attr.value.substring(0, 200);
        }
        return result;
    })()''')
    print(f"  Root: {ac_info.get('hasRoot')}, children: {ac_info.get('childCount')}")
    print(f"  Data attrs: {json.dumps(ac_info.get('dataAttrs', {}), indent=2)}")
    print(f"  HTML preview: {ac_info.get('innerHTML', '')[:300]}")

    # Select student first
    page.evaluate('document.querySelector(\'input[value="student"]\')?.click()')
    page.wait_for_timeout(3000)

    # Try typing in autocomplete
    searches = ["SKT", "International", "MIT", "Stanford", "Harvard"]
    for q in searches:
        print(f"\n=== Search: {q!r} ===")
        api_calls.clear()
        inp = page.query_selector('#js-school-name-search')
        if inp:
            inp.fill("")
            page.wait_for_timeout(300)
            inp.type(q, delay=100)
            page.wait_for_timeout(5000)

            # Check results
            results = page.evaluate('''(() => {
                const list = document.querySelector('#js-school-name-list, [role="listbox"]');
                if (!list) return {listFound: false, count: 0, items: []};
                const items = list.querySelectorAll('[role="option"], li, button');
                return {
                    listFound: true,
                    count: items.length,
                    html: list.outerHTML?.substring(0, 500) || '',
                    items: Array.from(items).slice(0, 5).map(i => ({
                        text: i.textContent?.trim()?.substring(0, 100),
                        value: i.dataset?.autocompleteValue || i.dataset?.value || '',
                    })),
                };
            })()''')
            print(f"  List found: {results.get('listFound')}, items: {results.get('count')}")
            for item in results.get('items', []):
                print(f"    - {item['text']!r} (value={item['value']!r})")

            print(f"  API calls: {len(api_calls)}")
            for call in api_calls:
                print(f"    {call['url']}")
                print(f"    status={call['status']}, body={call['body_preview'][:100]!r}")
        else:
            print("  Input #js-school-name-search not found!")
            # Look for any text input
            alt = page.evaluate('''(() => {
                const inputs = document.querySelectorAll('#dev-pack-form input[type="text"]');
                return Array.from(inputs).map(i => ({name: i.name, id: i.id, placeholder: i.placeholder}));
            })()''')
            print(f"  Alt text inputs: {json.dumps(alt)}")
            break

    browser.close()
print("\nDone!")
