"""Education v10: Inject step 2 form + webcam react-partial into page DOM,
then interact with the webcam component to understand how it captures and stores photos."""
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
        '--use-fake-ui-for-media-stream',
        '--use-fake-device-for-media-stream',
        '--use-file-for-fake-video-capture=',
    ])
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
        permissions=["camera"],
    )
    page = context.new_page()

    # Track network requests
    net_requests = []
    def on_request(req):
        url = req.url
        if any(kw in url for kw in ['upload', 'photo', 'webcam', 'blob', 'presign', 'education', 'developer_pack']):
            net_requests.append({"method": req.method, "url": url[:200], "type": req.resource_type})
    page.on("request", on_request)

    # Track console messages
    console_msgs = []
    page.on("console", lambda msg: console_msgs.append(f"[{msg.type}] {msg.text[:200]}"))

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

    # === Navigate to parent page ===
    page.goto("https://github.com/settings/education/benefits", timeout=120000, wait_until="load")
    page.wait_for_timeout(5000)

    # === Step 1 via fetch ===
    print("\n=== Step 1 ===")
    step1_result = page.evaluate('''async () => {
        const r1 = await fetch("/settings/education/developer_pack_applications/new", {
            headers: {"Accept": "text/html", "Turbo-Frame": "dev-pack-form"},
            credentials: "same-origin",
        });
        const formHtml = await r1.text();
        const doc = new DOMParser().parseFromString(formHtml, 'text/html');
        const form = doc.querySelector('form');
        if (!form) return {error: "no form"};

        const fd = new FormData();
        const token = form.querySelector('input[name="authenticity_token"]');
        if (token) fd.set('authenticity_token', token.value);

        fd.set('dev_pack_form[application_type]', 'student');
        fd.set('dev_pack_form[school_name]', 'SKT International College');
        fd.set('dev_pack_form[school_email]', 'thawkhant.1280@gmail.com');
        fd.set('dev_pack_form[latitude]', '16.8661');
        fd.set('dev_pack_form[longitude]', '96.1951');
        fd.set('dev_pack_form[location_shared]', 'true');
        fd.set('dev_pack_form[form_variant]', 'initial_form');
        fd.set('dev_pack_form[browser_location]', '');
        fd.set('dev_pack_form[utm_source]', '');
        fd.set('dev_pack_form[utm_content]', '');
        fd.set('continue', 'Continue');

        const r2 = await fetch("/settings/education/developer_pack_applications", {
            method: "POST",
            headers: {"Turbo-Frame": "dev-pack-form"},
            credentials: "same-origin",
            body: fd,
        });
        const html = await r2.text();
        return {status: r2.status, hasProof: html.includes('proof_type'), body: html};
    }''')
    print(f"  Status: {step1_result.get('status')}, Proof: {step1_result.get('hasProof')}")
    if not step1_result.get('hasProof'):
        print("  Step 2 not reached!"); browser.close(); sys.exit(1)

    step2_html = step1_result["body"]

    # === Inject step 2 into turbo-frame and wait for webcam to render ===
    print("\n=== Injecting step 2 into DOM ===")
    inject_result = page.evaluate('''(step2Html) => {
        // Extract from turbo-stream template
        let formHtml = step2Html;
        if (step2Html.includes('<turbo-stream')) {
            const tmpDoc = new DOMParser().parseFromString(step2Html, 'text/html');
            const template = tmpDoc.querySelector('template');
            if (template) {
                const container = document.createElement('div');
                container.appendChild(template.content.cloneNode(true));
                formHtml = container.innerHTML;
            }
        }

        // Inject into turbo-frame
        const frame = document.querySelector('#dev-pack-form');
        if (!frame) return {error: "no turbo-frame"};
        frame.innerHTML = formHtml;

        return {injected: true, frameChildren: frame.childElementCount};
    }''', step2_html)
    print(f"  Injected: {inject_result}")

    # Wait for React to hydrate the webcam-upload partial
    print("\n=== Waiting for webcam component to hydrate ===")
    for i in range(10):
        page.wait_for_timeout(3000)
        state = page.evaluate('''() => {
            const partial = document.querySelector('react-partial[partial-name="webcam-upload"]');
            if (!partial) return {found: false};
            const root = partial.querySelector('[data-target="react-partial.reactRoot"]');
            const children = root ? root.childElementCount : 0;
            const hasVideo = root ? !!root.querySelector('video') : false;
            const hasCanvas = root ? !!root.querySelector('canvas') : false;
            const buttons = root ? Array.from(root.querySelectorAll('button')).map(b => ({
                text: b.textContent.trim().substring(0, 80),
                disabled: b.disabled,
                type: b.type || 'button',
                classes: b.className.substring(0, 100),
            })) : [];
            const allText = root ? root.textContent.trim().substring(0, 300) : '';
            return {found: true, children, hasVideo, hasCanvas, buttons, text: allText};
        }''')
        print(f"  [{(i+1)*3}s] children={state.get('children', 0)}, video={state.get('hasVideo')}, buttons={len(state.get('buttons', []))}")
        if state.get('buttons'):
            for btn in state['buttons']:
                print(f"    Button: '{btn['text']}' disabled={btn['disabled']}")
        if state.get('hasVideo') or (state.get('buttons') and len(state['buttons']) > 0):
            print(f"    Text: {state.get('text', '')[:200]}")
            break

    # Full webcam component HTML
    webcam_html = page.evaluate('''() => {
        const root = document.querySelector('react-partial[partial-name="webcam-upload"] [data-target="react-partial.reactRoot"]');
        return root ? root.innerHTML : "empty";
    }''')
    print(f"\n  Webcam HTML ({len(webcam_html)} chars):")
    print(f"  {webcam_html[:1000]}")

    # Check if there's a "Start camera" or "Take photo" button
    print("\n=== Attempting to interact with webcam ===")

    # Click any button in the webcam component
    webcam_buttons = page.evaluate('''() => {
        const root = document.querySelector('react-partial[partial-name="webcam-upload"] [data-target="react-partial.reactRoot"]');
        if (!root) return [];
        return Array.from(root.querySelectorAll('button')).map((b, i) => ({
            index: i,
            text: b.textContent.trim(),
            disabled: b.disabled,
            visible: b.offsetParent !== null,
            rect: b.getBoundingClientRect(),
        }));
    }''')
    print(f"  Buttons: {json.dumps(webcam_buttons, indent=2)}")

    for btn in webcam_buttons:
        if not btn['disabled']:
            print(f"\n  Clicking button: '{btn['text']}'")
            # Use evaluate to click by index
            click_result = page.evaluate(f'''() => {{
                const root = document.querySelector('react-partial[partial-name="webcam-upload"] [data-target="react-partial.reactRoot"]');
                const btns = root.querySelectorAll('button');
                btns[{btn['index']}].click();
                return true;
            }}''')
            page.wait_for_timeout(5000)

            # Check state after click
            after_click = page.evaluate('''() => {
                const root = document.querySelector('react-partial[partial-name="webcam-upload"] [data-target="react-partial.reactRoot"]');
                if (!root) return {error: "no root"};
                const hasVideo = !!root.querySelector('video');
                const hasCanvas = !!root.querySelector('canvas');
                const buttons = Array.from(root.querySelectorAll('button')).map(b => ({
                    text: b.textContent.trim(),
                    disabled: b.disabled,
                }));
                // Check photo_proof
                const pp = document.getElementById('photo_proof');
                const ppVal = pp ? pp.value : null;
                return {
                    hasVideo, hasCanvas, buttons,
                    photoProofLen: ppVal ? ppVal.length : 0,
                    photoProofPrefix: ppVal ? ppVal.substring(0, 50) : null,
                    text: root.textContent.trim().substring(0, 300),
                    html: root.innerHTML.substring(0, 500),
                };
            }''')
            print(f"  After click: video={after_click.get('hasVideo')}, canvas={after_click.get('hasCanvas')}")
            print(f"  Buttons: {json.dumps(after_click.get('buttons', []))}")
            print(f"  photo_proof: len={after_click.get('photoProofLen')}, prefix={after_click.get('photoProofPrefix')}")
            print(f"  Text: {after_click.get('text', '')[:200]}")
            print(f"  HTML: {after_click.get('html', '')[:300]}")

            # If video appeared, wait and look for capture button
            if after_click.get('hasVideo'):
                print("\n  Video active! Waiting for capture button...")
                page.wait_for_timeout(3000)
                for nxt_btn in after_click.get('buttons', []):
                    text = nxt_btn['text'].lower()
                    if any(kw in text for kw in ['take', 'capture', 'photo', 'snap']):
                        print(f"  Clicking capture: '{nxt_btn['text']}'")
                        page.evaluate(f'''() => {{
                            const root = document.querySelector('react-partial[partial-name="webcam-upload"] [data-target="react-partial.reactRoot"]');
                            const btns = root.querySelectorAll('button');
                            for (const b of btns) {{
                                if (b.textContent.trim().toLowerCase().includes('take') ||
                                    b.textContent.trim().toLowerCase().includes('capture') ||
                                    b.textContent.trim().toLowerCase().includes('photo')) {{
                                    b.click(); break;
                                }}
                            }}
                        }}''')
                        page.wait_for_timeout(5000)

                        # Check photo_proof after capture
                        capture_result = page.evaluate('''() => {
                            const pp = document.getElementById('photo_proof');
                            const ppVal = pp ? pp.value : null;
                            return {
                                photoProofLen: ppVal ? ppVal.length : 0,
                                photoProofPrefix: ppVal ? ppVal.substring(0, 80) : null,
                            };
                        }''')
                        print(f"  After capture: len={capture_result.get('photoProofLen')}, prefix={capture_result.get('photoProofPrefix')}")
                        break

    # Check for any network requests to upload endpoints
    upload_requests = [r for r in net_requests if 'upload' in r['url'].lower() or 'photo' in r['url'].lower() or 'blob' in r['url'].lower()]
    all_edu_requests = [r for r in net_requests]
    print(f"\n=== Network requests ===")
    print(f"  Upload-related: {len(upload_requests)}")
    for r in upload_requests:
        print(f"    {r['method']} {r['url']}")
    print(f"  All education/upload: {len(all_edu_requests)}")
    for r in all_edu_requests[:20]:
        print(f"    {r['method']} {r['url'][:150]}")

    # Console errors
    errors = [m for m in console_msgs if 'error' in m.lower() or 'exception' in m.lower()]
    if errors:
        print(f"\n=== Console errors ({len(errors)}) ===")
        for e in errors[:10]:
            print(f"  {e}")

    # Any warnings about camera
    cam_msgs = [m for m in console_msgs if any(kw in m.lower() for kw in ['camera', 'media', 'device', 'webcam', 'permission', 'stream'])]
    if cam_msgs:
        print(f"\n=== Camera-related console messages ({len(cam_msgs)}) ===")
        for m in cam_msgs:
            print(f"  {m}")

    page.screenshot(path="pw_v10_webcam.png")
    browser.close()

print("\nDone!")
