"""Education v9: Inject step 2 HTML into DOM, fill values, submit NATIVELY via Turbo.
Also intercept the actual request to see what's being sent vs what the server expects."""
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
    )
    page = context.new_page()

    # === Track ALL request bodies ===
    captured_requests = []
    def on_request(req):
        if 'developer_pack_applications' in req.url and req.method == 'POST':
            body = req.post_data or ''
            headers = dict(req.headers)
            captured_requests.append({
                "url": req.url,
                "method": req.method,
                "content_type": headers.get('content-type', 'unknown'),
                "body_len": len(body),
                "body_preview": body[:500] if len(body) < 2000 else body[:200] + f'...({len(body)} total)...' + body[-200:],
                "has_photo_proof": 'photo_proof' in body,
                "headers": {k: v for k, v in headers.items() if k in ['content-type', 'accept', 'turbo-frame', 'x-csrf-token']},
            })
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
        const hasProof = html.includes('proof_type');
        return {status: r2.status, hasProof, body: html};
    }''')
    print(f"  Status: {step1_result.get('status')}, Proof: {step1_result.get('hasProof')}")
    if not step1_result.get('hasProof'):
        print("  Step 2 not reached!"); browser.close(); sys.exit(1)

    step2_html = step1_result["body"]

    # === Approach A: Inject into DOM and submit natively ===
    print("\n=== Approach A: DOM injection + native Turbo form submit ===")
    result_a = page.evaluate('''async (step2Html) => {
        // Extract the inner HTML from turbo-stream template
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

        // Inject into the turbo-frame on the page
        const frame = document.querySelector('#dev-pack-form');
        if (!frame) return {error: "no turbo-frame"};
        frame.innerHTML = formHtml;

        // Wait for DOM to settle
        await new Promise(r => setTimeout(r, 1000));

        // Generate photo
        const c = document.createElement('canvas'); c.width=1280; c.height=720;
        const ctx = c.getContext('2d');
        const g = ctx.createLinearGradient(0,0,1280,720);
        g.addColorStop(0,'#1a365d'); g.addColorStop(0.5,'#2563eb'); g.addColorStop(1,'#f59e0b');
        ctx.fillStyle = g; ctx.fillRect(0,0,1280,720);
        ctx.fillStyle = '#fff'; ctx.font = 'bold 48px sans-serif';
        ctx.fillText('Student Enrollment Proof', 60, 100);
        ctx.font = '32px sans-serif';
        ctx.fillText('SKT International College', 60, 160);
        ctx.fillText('Date: ' + new Date().toLocaleDateString(), 60, 210);
        const photoDataUrl = c.toDataURL('image/jpeg', 0.9);

        // Set photo_proof hidden input
        const photoInput = document.getElementById('photo_proof');
        if (!photoInput) return {error: "no photo_proof input"};
        photoInput.value = photoDataUrl;

        // Set proof_type hidden input
        const proofTypeInput = document.querySelector('input[name="dev_pack_form[proof_type]"]');
        if (proofTypeInput) {
            proofTypeInput.value = '2. Dated official/unofficial transcript';
        }

        // Fix form_variant - ensure it says upload_proof_form
        document.querySelectorAll('input[name="dev_pack_form[form_variant]"]').forEach(el => {
            el.value = 'upload_proof_form';
        });

        // Verify all inputs before submit
        const form = document.querySelector('#dev-pack-form form');
        if (!form) return {error: "no form in DOM"};

        const allInputs = {};
        const formData = new FormData(form);
        for (const [k, v] of formData.entries()) {
            if (k.includes('token')) allInputs[k] = '[TOKEN]';
            else if (k.includes('photo_proof')) allInputs[k] = '[' + (typeof v === 'string' ? v.length : 'blob:' + v.size) + ' chars]';
            else allInputs[k] = typeof v === 'string' ? v.substring(0, 100) : '[Blob]';
        }

        return {
            injected: true,
            photoLen: photoDataUrl.length,
            photoInputValue: photoInput.value.length,
            formAction: form.action,
            formMethod: form.method,
            allInputs,
            formVariantCount: document.querySelectorAll('input[name="dev_pack_form[form_variant]"]').length,
        };
    }''', step2_html)
    print(f"  Result: {json.dumps(result_a, indent=2)}")

    if result_a.get('injected'):
        # Now try submitting the form via DOM click
        print("\n  Clicking submit button via DOM...")
        
        # Use route interception to capture the EXACT request body
        captured_body = []
        def handle_route(route):
            req = route.request
            body = req.post_data or ''
            captured_body.append({
                "content_type": req.headers.get('content-type', 'unknown'),
                "body_len": len(body),
                "has_photo": 'photo_proof' in body,
                "photo_positions": [],
            })
            # Find photo_proof in the body
            idx = body.find('photo_proof')
            while idx != -1:
                captured_body[-1]['photo_positions'].append({
                    'pos': idx,
                    'context': body[max(0,idx-50):idx+100]
                })
                idx = body.find('photo_proof', idx + 1)
            
            route.continue_()

        page.route("**/developer_pack_applications", handle_route)

        try:
            page.click('button[name="submit"]', timeout=10000)
            page.wait_for_timeout(10000)
        except Exception as e:
            print(f"  Click error: {e}")

        page.unroute("**/developer_pack_applications")

        # Check captured request
        if captured_body:
            print(f"\n  Captured {len(captured_body)} request(s):")
            for i, cap in enumerate(captured_body):
                print(f"    Request {i}: content_type={cap['content_type']}, body_len={cap['body_len']}, has_photo={cap['has_photo']}")
                for pp in cap.get('photo_positions', []):
                    print(f"      photo_proof at pos {pp['pos']}: ...{pp['context'][:150]}...")
        else:
            print("  No requests captured!")

        # Check response
        result_text = page.evaluate('''() => {
            const frame = document.querySelector('#dev-pack-form');
            return frame ? frame.textContent.trim().substring(0, 500) : 'no frame';
        }''')
        print(f"\n  Response text: {result_text[:300]}")

    # === Approach B: Direct fetch with exact same FormData as native form ===
    print("\n\n=== Approach B: Build FormData from DOM form element (like Turbo does) ===")
    result_b = page.evaluate('''async () => {
        // Re-inject form if needed
        const form = document.querySelector('#dev-pack-form form');
        if (!form) return {error: "no form"};

        // Set values again (form may have been updated by response)
        const photoInput = document.getElementById('photo_proof');
        if (photoInput) {
            const c = document.createElement('canvas'); c.width=1280; c.height=720;
            const ctx = c.getContext('2d');
            ctx.fillStyle = '#2563eb'; ctx.fillRect(0,0,1280,720);
            ctx.fillStyle = '#fff'; ctx.font = 'bold 36px sans-serif';
            ctx.fillText('Student Enrollment Proof - SKT International College', 40, 100);
            ctx.fillText('Date: ' + new Date().toLocaleDateString(), 40, 150);
            photoInput.value = c.toDataURL('image/jpeg', 0.9);
        }

        const proofTypeInput = document.querySelector('input[name="dev_pack_form[proof_type]"]');
        if (proofTypeInput) proofTypeInput.value = '2. Dated official/unofficial transcript';

        document.querySelectorAll('input[name="dev_pack_form[form_variant]"]').forEach(el => {
            el.value = 'upload_proof_form';
        });

        // Build FormData FROM the DOM form element (exactly like Turbo/browser would)
        const fd = new FormData(form);
        
        // Also add the submit button value (browsers do this for the clicked button)
        fd.set('submit', 'Submit Application');

        // Log what's in the FormData
        const entries = {};
        for (const [k, v] of fd.entries()) {
            if (k.includes('token')) entries[k] = '[TOKEN]';
            else if (k.includes('photo_proof')) {
                const val = typeof v === 'string' ? v : 'blob';
                entries[k] = typeof v === 'string' ? `[string: ${v.length} chars, prefix: ${v.substring(0,40)}]` : `[blob: ${v.size}]`;
            }
            else entries[k] = typeof v === 'string' ? v.substring(0, 100) : '[Blob]';
        }

        // Count how many of each key
        const keyCounts = {};
        for (const [k] of fd.entries()) {
            keyCounts[k] = (keyCounts[k] || 0) + 1;
        }
        const duplicateKeys = Object.entries(keyCounts).filter(([k, v]) => v > 1);

        // Now submit via fetch (mimicking Turbo)
        const r = await fetch(form.action, {
            method: 'POST',
            headers: {
                'Accept': 'text/vnd.turbo-stream.html, text/html, application/xhtml+xml',
                'Turbo-Frame': 'dev-pack-form',
            },
            credentials: 'same-origin',
            body: fd,
        });
        const respText = await r.text();

        // Parse
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
        respDoc.querySelectorAll('p.color-fg-danger').forEach(e => {
            const t = e.textContent.trim();
            if (t) errors.push('inline: ' + t);
        });
        const checked = [];
        respDoc.querySelectorAll('[aria-checked="true"]').forEach(e => checked.push(e.textContent.trim().substring(0, 80)));

        const success = respDoc.body?.textContent?.toLowerCase().includes('thank') ||
                       respDoc.body?.textContent?.toLowerCase().includes('submitted') ||
                       respDoc.body?.textContent?.toLowerCase().includes('pending');

        return {
            status: r.status,
            entries,
            duplicateKeys,
            errors,
            checked,
            success,
            textPreview: respDoc.body?.textContent?.trim().substring(0, 300),
        };
    }''')
    print(f"  FormData entries: {json.dumps(result_b.get('entries', {}), indent=2)}")
    print(f"  Duplicate keys: {result_b.get('duplicateKeys')}")
    print(f"  Status: {result_b.get('status')}")
    print(f"  Success: {result_b.get('success')}")
    print(f"  Errors: {result_b.get('errors')}")
    print(f"  Checked: {result_b.get('checked')}")

    # Also check captured requests from approach A
    print(f"\n\n=== All captured POST requests ===")
    for i, req in enumerate(captured_requests):
        print(f"  Request {i}: {req['method']} {req['url']}")
        print(f"    Content-Type: {req['content_type']}")
        print(f"    Body length: {req['body_len']}")
        print(f"    Has photo_proof: {req['has_photo_proof']}")
        print(f"    Headers: {json.dumps(req.get('headers', {}))}")

    browser.close()

print("\nDone!")
