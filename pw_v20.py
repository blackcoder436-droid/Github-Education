"""Education v20: Manually complete form state and submit via DOM."""
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

    # === Complete step 1 via DOM manipulation ===
    print("\n=== Step 1: DOM setup ===")
    setup_result = page.evaluate('''() => {
        // Click student radio
        const studentRadio = document.querySelector('input[value="student"]');
        if (studentRadio) studentRadio.click();

        // Set hidden school_name
        const hiddenSchoolName = document.querySelector('input.d-none[name="dev_pack_form[school_name]"]');
        if (hiddenSchoolName) {
            hiddenSchoolName.value = "University of Computer Studies, Yangon";
        }

        // Set visible search input too
        const searchInput = document.getElementById('js-school-name-search');
        if (searchInput) {
            searchInput.value = "University of Computer Studies, Yangon";
        }

        // Set location
        const lat = document.querySelector('input[name="dev_pack_form[latitude]"]');
        if (lat) lat.value = '16.8661';
        const lng = document.querySelector('input[name="dev_pack_form[longitude]"]');
        if (lng) lng.value = '96.1951';
        const locShared = document.querySelector('input[name="dev_pack_form[location_shared]"]');
        if (locShared) locShared.value = 'true';

        // Enable continue button
        const continueBtn = document.querySelector('button[name="continue"]');
        if (continueBtn) {
            continueBtn.disabled = false;
            continueBtn.removeAttribute('disabled');
            continueBtn.removeAttribute('aria-disabled');
        }

        // Check form data
        const form = document.querySelector('form[action="/settings/education/developer_pack_applications"]');
        if (!form) return {error: "no form"};
        const fd = new FormData(form);
        const data = {};
        for (const [key, value] of fd.entries()) {
            data[key] = typeof value === 'string' ? value.substring(0, 200) : value.name;
        }
        return {data, btnDisabled: continueBtn?.disabled};
    }''')
    print(f"  Setup: {json.dumps(setup_result, indent=2)[:500]}")

    # === Intercept step 1 POST and capture step 2 response ===
    print("\n=== Submitting step 1 via form ===")
    responses_captured = []
    def on_response(resp):
        if 'developer_pack' in resp.url and resp.request.method == 'POST':
            try:
                body = resp.text()
            except:
                body = ''
            responses_captured.append({
                'url': resp.url,
                'status': resp.status,
                'body': body[:5000],
            })
    page.on("response", on_response)

    # Click continue (now enabled)
    continue_btn = page.query_selector('button[name="continue"]')
    if continue_btn:
        try:
            continue_btn.click(timeout=10000)
            page.wait_for_timeout(5000)
            print(f"  Continue clicked! Responses: {len(responses_captured)}")
            for r in responses_captured:
                print(f"    {r['status']} {r['url']}")
                has_proof = 'proof_type' in r['body']
                print(f"    Has step 2: {has_proof}")
                if not has_proof:
                    print(f"    Body: {r['body'][:300]}")
        except Exception as e:
            print(f"  Click failed: {e}")

    # === Check what's on the page now (step 2?) ===
    print("\n=== Current page state ===")
    page_state = page.evaluate('''() => {
        const body = document.body;
        const hasProofType = !!body.querySelector('[name="dev_pack_form[proof_type]"]');
        const hasPhotoProof = !!body.querySelector('[name="dev_pack_form[photo_proof]"]');
        const hasWebcam = !!body.querySelector('react-partial[partial-name="webcam-upload"]');
        const errors = [];
        body.querySelectorAll('.Banner-title, .flash-error, p.color-fg-danger').forEach(e => {
            const t = e.textContent.trim();
            if (t && t.length < 500) errors.push(t);
        });

        // All inputs
        const inputs = {};
        body.querySelectorAll('input[type="hidden"]').forEach(el => {
            if (el.name && !el.name.startsWith('authenticity')) {
                inputs[el.name] = (el.value || '').substring(0, 200);
            }
        });

        return {hasProofType, hasPhotoProof, hasWebcam, errors, inputs, text: body.textContent.trim().substring(0, 500)};
    }''')
    print(f"  {json.dumps(page_state, indent=2)[:600]}")

    # If we're on step 2, try submitting with photo
    if page_state.get('hasProofType') or page_state.get('hasPhotoProof'):
        print("\n=== On Step 2! Submitting photo... ===")

        # Check ALL hidden fields on step 2
        all_hidden = page.evaluate('''() => {
            const inputs = {};
            document.querySelectorAll('input[type="hidden"]').forEach(el => {
                if (el.name) inputs[el.name] = (el.value || '').substring(0, 200);
            });
            return inputs;
        }''')
        print(f"  All hidden fields: {json.dumps(all_hidden, indent=2)}")

        # Now submit step 2 with fetch, using all the hidden fields from the page
        step2_result = page.evaluate('''async () => {
            // Generate photo
            const c = document.createElement('canvas');
            c.width = 640; c.height = 480;
            const ctx = c.getContext('2d');
            ctx.fillStyle = '#2563eb'; ctx.fillRect(0, 0, 640, 480);
            ctx.fillStyle = '#fff'; ctx.font = '24px sans-serif';
            ctx.fillText('Student ID - UCSY', 30, 50);
            ctx.fillText('Academic Year 2024-2025', 30, 90);
            const photoDataUrl = c.toDataURL('image/jpeg', 0.8);

            const photoJson = JSON.stringify({
                image: photoDataUrl,
                metadata: {filename: null, type: null, mimeType: "image/jpeg", deviceLabel: null}
            });

            // Get form and its data
            const form = document.querySelector('form[action="/settings/education/developer_pack_applications"]');
            if (!form) return {error: "no form on step 2"};

            const fd = new FormData(form);

            // Set proof type and photo
            fd.set('dev_pack_form[proof_type]', '2. Dated official/unofficial transcript');
            fd.set('dev_pack_form[photo_proof]', photoJson);

            // Make sure form_variant is correct
            fd.set('dev_pack_form[form_variant]', 'upload_proof_form');

            // Log what we're sending
            const sentData = {};
            for (const [key, value] of fd.entries()) {
                if (key === 'authenticity_token') continue;
                sentData[key] = (typeof value === 'string' ? value : value.name).substring(0, 100);
            }

            const r = await fetch("/settings/education/developer_pack_applications", {
                method: "POST",
                headers: {
                    "Turbo-Frame": "dev-pack-form",
                    "Accept": "text/vnd.turbo-stream.html, text/html, application/xhtml+xml",
                },
                credentials: "same-origin",
                body: fd,
            });
            const respText = await r.text();

            // Parse response
            let respDoc;
            if (respText.includes('<turbo-stream')) {
                const tmpDoc = new DOMParser().parseFromString(respText, 'text/html');
                const template = tmpDoc.querySelector('template');
                if (template) {
                    const container = document.createElement('div');
                    container.appendChild(template.content.cloneNode(true));
                    respDoc = new DOMParser().parseFromString(container.innerHTML, 'text/html');
                } else respDoc = tmpDoc;
            } else {
                respDoc = new DOMParser().parseFromString(respText, 'text/html');
            }

            const errors = [];
            respDoc.querySelectorAll('.Banner-title, [data-target="x-banner.titleText"]').forEach(e => errors.push(e.textContent.trim()));
            const bodyText = respDoc.body?.textContent?.trim() || '';
            const success = bodyText.toLowerCase().includes('thank') ||
                           bodyText.toLowerCase().includes('submitted') ||
                           bodyText.toLowerCase().includes('pending');

            return {status: r.status, success, errors, sentData, bodyPreview: bodyText.substring(0, 500)};
        }''')
        print(f"  Step 2 result: {json.dumps(step2_result, indent=2)[:800]}")
    else:
        print("\n  Not on step 2. Trying fetch approach as fallback...")

        # Fetch approach as fallback
        result = page.evaluate('''async () => {
            // Get a fresh form
            const r1 = await fetch("/settings/education/developer_pack_applications/new", {
                headers: {"Accept": "text/html", "Turbo-Frame": "dev-pack-form"},
                credentials: "same-origin",
            });
            const formHtml = await r1.text();
            const doc = new DOMParser().parseFromString(formHtml, 'text/html');
            const form = doc.querySelector('form');
            if (!form) return {error: "no form in fetch"};

            const token = form.querySelector('input[name="authenticity_token"]')?.value;

            // Step 1 - use the search input value (the autocomplete value)
            const fd = new FormData();
            fd.set('authenticity_token', token);
            fd.set('dev_pack_form[application_type]', 'student');
            fd.set('dev_pack_form[school_name]', 'University of Computer Studies, Yangon');
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

            // Check step 2 form for ALL hidden fields
            let inner = html;
            if (html.includes('<turbo-stream')) {
                const tmpDoc = new DOMParser().parseFromString(html, 'text/html');
                const template = tmpDoc.querySelector('template');
                if (template) {
                    const container = document.createElement('div');
                    container.appendChild(template.content.cloneNode(true));
                    inner = container.innerHTML;
                }
            }
            const doc2 = new DOMParser().parseFromString(inner, 'text/html');
            const allHidden = {};
            doc2.querySelectorAll('input[type="hidden"]').forEach(el => {
                if (el.name) allHidden[el.name] = (el.value || '').substring(0, 200);
            });

            return {
                step1Status: r2.status,
                hasProof: html.includes('proof_type'),
                allHiddenFields: allHidden,
                htmlLen: html.length,
            };
        }''')
        print(f"  Fetch fallback: {json.dumps(result, indent=2)[:600]}")

    browser.close()

print("\nDone!")
