"""Education flow v8: HEADED mode - let React webcam component work naturally.
Use fake camera with visible browser to get the webcam component to hydrate and capture."""
import os, sys, json
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
import pyotp
load_dotenv()

USERNAME = os.environ['GITHUB_USERNAME']
PASSWORD = os.environ['GITHUB_PASSWORD']
TOTP_SECRET = "SFDHLAA7MDH2S7TN"

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=False,
        args=[
            '--use-fake-ui-for-media-stream',
            '--use-fake-device-for-media-stream',
            '--auto-accept-camera-and-microphone-capture',
        ]
    )
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
        permissions=["camera"],
        viewport={"width": 1280, "height": 900},
    )
    page = context.new_page()

    # Track network requests for debugging
    requests_log = []
    def on_request(req):
        if 'developer_pack' in req.url or 'education' in req.url or 'upload' in req.url:
            requests_log.append({"method": req.method, "url": req.url, "type": req.resource_type})
    page.on("request", on_request)

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
    logged_in = "login" not in page.url
    print(f"  Logged in: {logged_in}")
    if not logged_in:
        browser.close(); sys.exit(1)

    # === Navigate to parent page (NOT the turbo-frame URL) ===
    print("\n=== Navigate to /settings/education/benefits ===")
    page.goto("https://github.com/settings/education/benefits", timeout=120000, wait_until="load")
    page.wait_for_timeout(8000)
    print(f"  URL: {page.url}")

    # Check if turbo-frame loaded the form
    turbo_frame = page.query_selector('#dev-pack-form')
    if turbo_frame:
        tf_children = page.evaluate('document.querySelector("#dev-pack-form")?.childElementCount || 0')
        print(f"  Turbo-frame children: {tf_children}")
    else:
        print("  No turbo-frame found!")

    # Wait for the form to load (turbo-frame lazy loading)
    print("  Waiting for form to load...")
    for i in range(12):
        page.wait_for_timeout(5000)
        form_present = page.evaluate('!!document.querySelector("#dev-pack-form form, #dev-pack-form input")')
        frame_src = page.evaluate('document.querySelector("#dev-pack-form")?.getAttribute("src") || "none"')
        if form_present:
            print(f"  [{(i+1)*5}s] Form loaded!")
            break
        print(f"  [{(i+1)*5}s] No form yet. Frame src: {frame_src}")
        # Try scrolling to the turbo frame to trigger IntersectionObserver
        if i == 2:
            page.evaluate('document.querySelector("#dev-pack-form")?.scrollIntoView({behavior: "smooth"})')
            print("    (scrolled to turbo-frame)")

    # Check form state
    form_html = page.evaluate('document.querySelector("#dev-pack-form")?.innerHTML?.substring(0, 500) || "empty"')
    print(f"  Form HTML preview: {form_html[:200]}")

    # If form didn't load via turbo-frame, force it via fetch and inject
    if not page.evaluate('!!document.querySelector("#dev-pack-form form")'):
        print("\n  Form didn't load naturally. Injecting via fetch...")
        page.evaluate('''async () => {
            const r = await fetch("/settings/education/developer_pack_applications/new", {
                headers: {"Accept": "text/html", "Turbo-Frame": "dev-pack-form"},
                credentials: "same-origin",
            });
            const html = await r.text();
            const frame = document.querySelector("#dev-pack-form");
            if (frame) frame.innerHTML = html;
        }''')
        page.wait_for_timeout(3000)

    # Now fill step 1
    print("\n=== Step 1: Fill school info ===")

    # Try autocomplete for school
    school_input = page.query_selector('#js-school-name-search')
    if school_input:
        print("  Found autocomplete input, typing school name...")
        school_input.click()
        page.wait_for_timeout(500)
        school_input.type("SKT International", delay=50)
        page.wait_for_timeout(5000)

        # Check autocomplete results
        ac_results = page.evaluate('''() => {
            const items = document.querySelectorAll('#js-school-name-list [role="option"], .autocomplete-results li');
            return Array.from(items).map(i => i.textContent.trim().substring(0, 100));
        }''')
        print(f"  Autocomplete results: {ac_results}")

        if ac_results:
            # Click first matching result
            page.evaluate('''() => {
                const items = document.querySelectorAll('#js-school-name-list [role="option"]');
                for (const item of items) {
                    if (item.textContent.includes("SKT")) { item.click(); return true; }
                }
                if (items[0]) { items[0].click(); return true; }
                return false;
            }''')
            page.wait_for_timeout(2000)
        else:
            # Set manually
            page.evaluate('''() => {
                document.querySelectorAll('input[name="dev_pack_form[school_name]"]').forEach(i => i.value = "SKT International College");
            }''')
    else:
        print("  No autocomplete input, setting school manually")
        page.evaluate('''() => {
            document.querySelectorAll('input[name="dev_pack_form[school_name]"]').forEach(i => i.value = "SKT International College");
        }''')

    # Select Student radio
    page.evaluate('document.querySelector(\'input[value="student"]\')?.click()')
    page.wait_for_timeout(500)

    # School email
    page.evaluate('''() => {
        const sel = document.querySelector('select[name="dev_pack_form[school_email]"]');
        if (sel) { sel.value = "thawkhant.1280@gmail.com"; sel.dispatchEvent(new Event("change", {bubbles:true})); }
    }''')

    # Location
    page.evaluate('''() => {
        const set = (n, v) => document.querySelectorAll('[name="'+n+'"]').forEach(e => e.value = v);
        set('dev_pack_form[latitude]', '16.8661');
        set('dev_pack_form[longitude]', '96.1951');
        set('dev_pack_form[location_shared]', 'true');
    }''')

    # Enable continue button and click
    page.evaluate('document.querySelector(\'button[name="continue"]\').disabled = false')
    page.wait_for_timeout(500)
    print("  Clicking Continue...")
    page.click('button[name="continue"]')

    # Wait for step 2 to load
    print("\n=== Waiting for Step 2 ===")
    for i in range(12):
        page.wait_for_timeout(5000)
        has_proof = page.evaluate('!!document.querySelector(\'input[name="dev_pack_form[proof_type]"]\')')
        has_webcam = page.evaluate('''() => {
            const root = document.querySelector('react-partial[partial-name="webcam-upload"] [data-target="react-partial.reactRoot"]');
            return root ? root.childElementCount : -1;
        }''')
        print(f"  [{(i+1)*5}s] proof_type: {has_proof}, webcam children: {has_webcam}")
        if has_proof and has_webcam > 0:
            print("  Step 2 loaded with hydrated webcam!")
            break
        if has_proof and has_webcam <= 0:
            print("  Step 2 loaded but webcam not hydrated yet...")

    # Take screenshot
    page.screenshot(path="pw_v8_step2.png")

    # Check webcam component state
    webcam_state = page.evaluate('''() => {
        const partial = document.querySelector('react-partial[partial-name="webcam-upload"]');
        if (!partial) return {found: false};
        const root = partial.querySelector('[data-target="react-partial.reactRoot"]');
        const children = root ? root.childElementCount : 0;
        const buttons = root ? Array.from(root.querySelectorAll('button')).map(b => ({
            text: b.textContent.trim().substring(0, 80),
            disabled: b.disabled,
        })) : [];
        const video = root ? !!root.querySelector('video') : false;
        const canvas = root ? !!root.querySelector('canvas') : false;
        return {found: true, children, buttons, video, canvas};
    }''')
    print(f"\n  Webcam state: {json.dumps(webcam_state, indent=2)}")

    if webcam_state.get('video'):
        print("\n=== Webcam video active! Attempting capture ===")
        page.wait_for_timeout(2000)  # Let video stream stabilize

        # Look for capture button
        for btn in webcam_state.get('buttons', []):
            text = btn['text'].lower()
            if any(kw in text for kw in ['take', 'capture', 'photo', 'snap', 'camera']):
                print(f"  Clicking: {btn['text']}")
                page.click(f'button:has-text("{btn["text"]}")')
                page.wait_for_timeout(3000)
                break

        # Check photo_proof value
        pp_value = page.evaluate('document.getElementById("photo_proof")?.value || ""')
        print(f"  photo_proof length: {len(pp_value)}")
        if pp_value:
            print(f"  photo_proof prefix: {pp_value[:60]}")

        # Screenshot after capture
        page.screenshot(path="pw_v8_captured.png")

        # If photo was captured, try to select proof type and submit
        if len(pp_value) > 100:
            print("\n=== Photo captured! Setting proof_type and submitting ===")

            # Click proof_type dropdown
            page.click('action-menu button')
            page.wait_for_timeout(1000)
            # Select transcript option
            page.click('button[data-value="2. Dated official/unofficial transcript"]')
            page.wait_for_timeout(1000)

            # Click submit
            print("  Submitting...")
            page.click('button[name="submit"]')
            page.wait_for_timeout(10000)

            # Check result
            page.screenshot(path="pw_v8_result.png")
            result_text = page.evaluate('document.body?.textContent?.substring(0, 1000) || ""')
            print(f"  Result text preview: {result_text[:300]}")

            # Check for success/error
            errors = page.evaluate('''() => {
                const errs = [];
                document.querySelectorAll('.Banner-title, [data-target="x-banner.titleText"]').forEach(e => errs.push(e.textContent.trim()));
                document.querySelectorAll('.flash-error').forEach(e => errs.push(e.textContent.trim().substring(0, 200)));
                return errs;
            }''')
            print(f"  Errors: {errors}")
    else:
        print("\n  Webcam not active. Trying to understand the component...")
        # If webcam didn't hydrate, check what's in the component
        inner_html = page.evaluate('''() => {
            const root = document.querySelector('react-partial[partial-name="webcam-upload"] [data-target="react-partial.reactRoot"]');
            return root ? root.innerHTML.substring(0, 2000) : "empty";
        }''')
        print(f"  Webcam inner HTML: {inner_html[:500]}")

        # Also check if we need to manually trigger the React partial to load
        # Check all loaded JS chunks
        js_count = page.evaluate('document.querySelectorAll("script[src]").length')
        print(f"  Script tags: {js_count}")

    # Final network requests log
    edu_requests = [r for r in requests_log if 'developer_pack' in r['url']]
    print(f"\n=== Network requests ({len(edu_requests)} education-related) ===")
    for r in edu_requests[:20]:
        print(f"  {r['method']} {r['url'].split('?')[0]}")

    # Keep browser open for a moment to observe
    page.wait_for_timeout(5000)
    browser.close()

print("\nDone!")
