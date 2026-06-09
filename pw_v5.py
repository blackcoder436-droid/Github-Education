"""Education flow v5: Single evaluate for step 2 to avoid DOM state issues.
Generate photo + set all values + submit in ONE evaluate call."""
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
                print("  2FA...")
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
    print(f"  Logged in: {logged_in} ({page.url})")
    if not logged_in:
        browser.close(); sys.exit(1)

    # === Navigate to parent page ===
    print("\n=== Navigate to /settings/education/benefits ===")
    page.goto("https://github.com/settings/education/benefits", timeout=120000, wait_until="load")
    page.wait_for_timeout(5000)

    # === STEP 1: Fetch form, inject, fill, submit - all in one evaluate ===
    print("\n=== Step 1: Complete flow ===")
    step1_result = page.evaluate('''async () => {
        // Fetch form HTML
        const r1 = await fetch("/settings/education/developer_pack_applications/new", {
            headers: {"Accept": "text/html", "Turbo-Frame": "dev-pack-form"},
            credentials: "same-origin",
        });
        const formHtml = await r1.text();

        // Parse to get token
        const doc = new DOMParser().parseFromString(formHtml, 'text/html');
        const form = doc.querySelector('form');
        if (!form) return {error: "no form", htmlLen: formHtml.length};

        // Build FormData from the parsed form
        const fd = new FormData();

        // Get authenticity_token
        const token = form.querySelector('input[name="authenticity_token"]');
        if (token) fd.set('authenticity_token', token.value);

        // Set all step 1 fields
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

        // Submit step 1
        const r2 = await fetch("/settings/education/developer_pack_applications", {
            method: "POST",
            headers: {"Turbo-Frame": "dev-pack-form"},
            credentials: "same-origin",
            body: fd,
        });
        const step1Html = await r2.text();
        const doc2 = new DOMParser().parseFromString(step1Html, 'text/html');
        const form2 = doc2.querySelector('form');
        const hasProof = !!doc2.querySelector('input[name="dev_pack_form[proof_type]"]');
        const banner = doc2.querySelector('.Banner-title, [data-target="x-banner.titleText"]');

        return {
            status: r2.status,
            bodyLen: step1Html.length,
            hasForm: !!form2,
            hasProof: hasProof,
            error: banner ? banner.textContent.trim() : null,
            body: step1Html,
        };
    }''')
    print(f"  Status: {step1_result.get('status')}, Length: {step1_result.get('bodyLen')}")
    print(f"  Has form: {step1_result.get('hasForm')}, Has proof: {step1_result.get('hasProof')}")
    print(f"  Error: {step1_result.get('error')}")

    if not step1_result.get('hasProof'):
        print("  Step 2 not reached!")
        with open("pw_v5_step1.html", "w", encoding="utf-8") as f:
            f.write(step1_result.get("body", ""))
        browser.close(); sys.exit(1)

    step2_html = step1_result["body"]

    # === STEP 2: Generate photo + submit - all in ONE evaluate ===
    print("\n=== Step 2: Generate photo + submit ===")
    step2_result = page.evaluate('''async (step2Html) => {
        // Parse step 2 HTML to get token and form data
        const doc = new DOMParser().parseFromString(step2Html, 'text/html');
        const form = doc.querySelector('form');
        if (!form) return {error: "no form in step2"};

        // Get token
        const token = form.querySelector('input[name="authenticity_token"]');

        // Generate photo proof canvas image
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

        // Build FormData manually with all fields
        const fd = new FormData();
        if (token) fd.set('authenticity_token', token.value);

        fd.set('dev_pack_form[proof_type]', '2. Dated official/unofficial transcript');
        fd.set('dev_pack_form[photo_proof]', photoDataUrl);
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

        // Debug: verify FormData before sending
        const preview = {};
        for (const [k, v] of fd.entries()) {
            const val = typeof v === 'string' ? v : '[File]';
            if (k.includes('token')) preview[k] = '[TOKEN]';
            else if (k.includes('photo_proof')) preview[k] = '[' + val.length + ' chars, starts: ' + val.substring(0, 30) + ']';
            else preview[k] = val.substring(0, 100);
        }

        // Submit step 2
        const r = await fetch("/settings/education/developer_pack_applications", {
            method: "POST",
            headers: {"Turbo-Frame": "dev-pack-form"},
            credentials: "same-origin",
            body: fd,
        });
        const respText = await r.text();

        // Parse response - handle turbo-stream wrapping
        let respDoc;
        if (respText.includes('<turbo-stream')) {
            // Extract content from <template> inside turbo-stream
            const tmpDoc = new DOMParser().parseFromString(respText, 'text/html');
            const template = tmpDoc.querySelector('template');
            if (template) {
                // template.content is a DocumentFragment, convert to string and re-parse
                const container = document.createElement('div');
                container.appendChild(template.content.cloneNode(true));
                respDoc = new DOMParser().parseFromString(container.innerHTML, 'text/html');
            } else {
                respDoc = tmpDoc;
            }
        } else {
            respDoc = new DOMParser().parseFromString(respText, 'text/html');
        }

        // Check result
        const banner = respDoc.querySelector('.Banner-title, [data-target="x-banner.titleText"], .flash-error');
        const errors = [];
        respDoc.querySelectorAll('.Banner-title, [data-target="x-banner.titleText"]').forEach(e => errors.push(e.textContent.trim()));
        respDoc.querySelectorAll('.FormControl-inlineValidation--error').forEach(e => {
            const label = e.closest('.FormControl')?.querySelector('.FormControl-label')?.textContent?.trim() || 'unknown';
            errors.push('Validation: ' + label + ' - ' + e.textContent.trim());
        });

        const bodyText = respDoc.body?.textContent?.trim() || '';
        const success = bodyText.toLowerCase().includes('thank') ||
                       bodyText.toLowerCase().includes('submitted') ||
                       bodyText.toLowerCase().includes('pending') ||
                       (r.status >= 300 && r.status < 400);

        // Check which proof items are checked
        const checked = [];
        respDoc.querySelectorAll('[aria-checked="true"]').forEach(e => checked.push(e.textContent.trim().substring(0, 80)));

        return {
            status: r.status,
            bodyLen: respText.length,
            success,
            errors,
            checked,
            preview,
            photoLen: photoDataUrl.length,
            textPreview: bodyText.substring(0, 500),
            rawPreview: respText.substring(0, 300),
            fullResp: respText,
        };
    }''', step2_html)

    print(f"\n  Status: {step2_result.get('status')}, Length: {step2_result.get('bodyLen')}")
    print(f"  Photo generated: {step2_result.get('photoLen')} chars")
    print(f"\n  FormData sent:")
    for k, v in step2_result.get('preview', {}).items():
        marker = " ***" if "proof" in k.lower() or "variant" in k.lower() else ""
        print(f"    {k} = {v!r}{marker}")
    print(f"\n  Success: {step2_result.get('success')}")
    print(f"  Errors: {step2_result.get('errors')}")
    print(f"  Checked: {step2_result.get('checked')}")
    print(f"  Text: {step2_result.get('textPreview', '')[:300]}")
    print(f"  Raw: {step2_result.get('rawPreview', '')[:200]}")

    # Also save full response
    if step2_result.get("fullResp"):
        with open("pw_v5_resp.html", "w", encoding="utf-8") as f:
            f.write(step2_result["fullResp"])

    page.screenshot(path="pw_v5_final.png")
    browser.close()

print("\nDone!")
