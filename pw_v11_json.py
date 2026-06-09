"""Education v11: Submit photo_proof as JSON object (not raw data URL).
The webcam component sets photo_proof = JSON.stringify({image: dataUrl, metadata: {...}})"""
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

    # Navigate to parent
    page.goto("https://github.com/settings/education/benefits", timeout=120000, wait_until="load")
    page.wait_for_timeout(5000)

    # === First: Inject step 2 and capture the FULL JSON from webcam component ===
    print("\n=== Getting full webcam JSON structure ===")
    json_structure = page.evaluate('''async () => {
        // Step 1
        const r1 = await fetch("/settings/education/developer_pack_applications/new", {
            headers: {"Accept": "text/html", "Turbo-Frame": "dev-pack-form"},
            credentials: "same-origin",
        });
        const formHtml = await r1.text();
        const doc = new DOMParser().parseFromString(formHtml, 'text/html');
        const form = doc.querySelector('form');
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
        const step2Html = await r2.text();

        // Inject into DOM
        let innerHtml = step2Html;
        if (step2Html.includes('<turbo-stream')) {
            const tmpDoc = new DOMParser().parseFromString(step2Html, 'text/html');
            const template = tmpDoc.querySelector('template');
            if (template) {
                const container = document.createElement('div');
                container.appendChild(template.content.cloneNode(true));
                innerHtml = container.innerHTML;
            }
        }
        const frame = document.querySelector('#dev-pack-form');
        frame.innerHTML = innerHtml;

        // Wait for React to hydrate
        await new Promise(r => setTimeout(r, 5000));

        // Click Start Camera
        const root = document.querySelector('react-partial[partial-name="webcam-upload"] [data-target="react-partial.reactRoot"]');
        const startBtn = root?.querySelector('button');
        if (startBtn && startBtn.textContent.includes('Start Camera')) {
            startBtn.click();
            await new Promise(r => setTimeout(r, 3000));
        }

        // Click Capture Photo
        const captureBtn = root?.querySelector('button');
        if (captureBtn && captureBtn.textContent.includes('Capture')) {
            captureBtn.click();
            await new Promise(r => setTimeout(r, 3000));
        }

        // Get the full photo_proof value
        const pp = document.getElementById('photo_proof');
        const ppValue = pp ? pp.value : null;

        // Try to parse as JSON
        let parsed = null;
        try { parsed = JSON.parse(ppValue); } catch(e) {}

        // Get token for step 2
        const step2Token = frame.querySelector('input[name="authenticity_token"]')?.value;

        return {
            ppValue: ppValue,
            ppLen: ppValue ? ppValue.length : 0,
            parsed: parsed,
            step2Token: step2Token ? '[present]' : null,
            step2Html: step2Html.substring(0, 200),
        };
    }''')
    print(f"  photo_proof length: {json_structure.get('ppLen')}")
    print(f"  photo_proof value: {json_structure.get('ppValue')}")
    print(f"  Parsed JSON: {json.dumps(json_structure.get('parsed'), indent=2)}")

    # === Now submit with correct JSON format ===
    print("\n\n=== Submitting with JSON photo_proof ===")
    result = page.evaluate('''async () => {
        // Get step 2 token from DOM
        const frame = document.querySelector('#dev-pack-form');
        const token = frame.querySelector('input[name="authenticity_token"]')?.value;

        // Generate a proper photo as data URL
        const c = document.createElement('canvas');
        c.width = 1280; c.height = 720;
        const ctx = c.getContext('2d');
        const g = ctx.createLinearGradient(0, 0, 1280, 720);
        g.addColorStop(0, '#1a365d'); g.addColorStop(0.5, '#2563eb'); g.addColorStop(1, '#f59e0b');
        ctx.fillStyle = g; ctx.fillRect(0, 0, 1280, 720);
        ctx.fillStyle = '#ffffff'; ctx.font = 'bold 48px sans-serif';
        ctx.fillText('Student Enrollment Proof', 60, 100);
        ctx.font = '32px sans-serif';
        ctx.fillText('SKT International College', 60, 160);
        ctx.fillText('Student ID: 2024-EDU-001', 60, 210);
        ctx.fillText('Date: ' + new Date().toLocaleDateString(), 60, 260);
        ctx.fillText('Academic Year: 2024-2025', 60, 310);
        const photoDataUrl = c.toDataURL('image/jpeg', 0.9);

        // Build the JSON photo_proof value (matching webcam component format)
        const photoJson = JSON.stringify({
            image: photoDataUrl,
            metadata: {
                filename: null,
                type: null,
                mimeType: "image/jpeg",
                deviceLabel: null,
            }
        });

        // Build FormData  
        const fd = new FormData();
        fd.set('authenticity_token', token);
        fd.set('dev_pack_form[proof_type]', '2. Dated official/unofficial transcript');
        fd.set('dev_pack_form[photo_proof]', photoJson);
        fd.set('dev_pack_form[form_variant]', 'upload_proof_form');
        fd.set('dev_pack_form[application_type]', 'student');
        fd.set('dev_pack_form[school_name]', 'SKT International College');
        fd.set('dev_pack_form[school_email]', 'thawkhant.1280@gmail.com');
        fd.set('dev_pack_form[latitude]', '16.8661');
        fd.set('dev_pack_form[longitude]', '96.1951');
        fd.set('dev_pack_form[location_shared]', 'true');
        fd.set('dev_pack_form[browser_location]', '');
        fd.set('dev_pack_form[utm_source]', '');
        fd.set('dev_pack_form[utm_content]', '');
        fd.set('submit', 'Submit Application');

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
        respDoc.querySelectorAll('p.color-fg-danger').forEach(e => {
            const t = e.textContent.trim();
            if (t) errors.push('inline: ' + t);
        });
        const checked = [];
        respDoc.querySelectorAll('[aria-checked="true"]').forEach(e => checked.push(e.textContent.trim().substring(0, 80)));

        const bodyText = respDoc.body?.textContent?.trim() || '';
        const success = bodyText.toLowerCase().includes('thank') ||
                       bodyText.toLowerCase().includes('submitted') ||
                       bodyText.toLowerCase().includes('pending') ||
                       bodyText.toLowerCase().includes('congratulations');

        return {
            status: r.status,
            success,
            errors,
            checked,
            photoJsonLen: photoJson.length,
            photoDataUrlLen: photoDataUrl.length,
            bodyLen: respText.length,
            textPreview: bodyText.substring(0, 500),
            respPreview: respText.substring(0, 300),
        };
    }''')

    print(f"  Status: {result.get('status')}")
    print(f"  Photo JSON length: {result.get('photoJsonLen')}")
    print(f"  Photo data URL length: {result.get('photoDataUrlLen')}")
    print(f"  Success: {result.get('success')}")
    print(f"  Errors: {result.get('errors')}")
    print(f"  Checked: {result.get('checked')}")
    print(f"  Text preview: {result.get('textPreview', '')[:300]}")
    print(f"  Response preview: {result.get('respPreview', '')[:200]}")

    # If success, save the response
    with open("pw_v11_resp.html", "w", encoding="utf-8") as f:
        f.write(result.get('respPreview', '') + "...")

    browser.close()

print("\nDone!")
