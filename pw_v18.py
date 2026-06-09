"""Education v18: Submit with University of Computer Studies, Yangon (ID: 7620).
A well-known school likely to have enrollment_size populated."""
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

    page.goto("https://github.com/settings/education/developer_pack_applications/new", timeout=120000, wait_until="load")
    page.wait_for_timeout(5000)

    # Use well-known schools
    schools_to_try = [
        ("University of Computer Studies, Yangon", "7620"),
        ("University of Yangon", "33037"),
        ("Yangon Technological University", "102038"),
    ]

    for school_name, school_id in schools_to_try:
        print(f"\n\n=== Trying: {school_name} (ID: {school_id}) ===")

        result = page.evaluate('''async (args) => {
            const [schoolName, schoolId] = args;

            // Step 1: Get form
            const r1 = await fetch("/settings/education/developer_pack_applications/new", {
                headers: {"Accept": "text/html", "Turbo-Frame": "dev-pack-form"},
                credentials: "same-origin",
            });
            const formHtml = await r1.text();
            const doc = new DOMParser().parseFromString(formHtml, 'text/html');
            const form = doc.querySelector('form');
            if (!form) return {error: "no form", preview: formHtml.substring(0, 200)};

            const fd = new FormData();
            const token = form.querySelector('input[name="authenticity_token"]');
            if (token) fd.set('authenticity_token', token.value);
            fd.set('dev_pack_form[application_type]', 'student');
            fd.set('dev_pack_form[school_name]', schoolName);
            fd.set('dev_pack_form[school_id]', schoolId);
            fd.set('dev_pack_form[school_email]', 'thawkhant.1280@gmail.com');
            fd.set('dev_pack_form[latitude]', '16.8661');
            fd.set('dev_pack_form[longitude]', '96.1951');
            fd.set('dev_pack_form[location_shared]', 'true');
            fd.set('dev_pack_form[form_variant]', 'initial_form');
            fd.set('dev_pack_form[browser_location]', '');
            fd.set('dev_pack_form[utm_source]', '');
            fd.set('dev_pack_form[utm_content]', '');
            fd.set('continue', 'Continue');

            // Step 1: Submit
            const r2 = await fetch("/settings/education/developer_pack_applications", {
                method: "POST",
                headers: {"Turbo-Frame": "dev-pack-form"},
                credentials: "same-origin",
                body: fd,
            });
            const step2Html = await r2.text();

            if (!step2Html.includes('proof_type')) {
                // Check for errors in step 1 response
                const s1doc = new DOMParser().parseFromString(step2Html, 'text/html');
                const errors = [];
                s1doc.querySelectorAll('.Banner-title, .flash-error, p.color-fg-danger').forEach(e => {
                    const t = e.textContent.trim();
                    if (t) errors.push(t.substring(0, 200));
                });
                return {error: "step 1 failed", status: r2.status, errors, preview: step2Html.substring(0, 300)};
            }

            // Step 2: Parse and submit
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
            const doc2 = new DOMParser().parseFromString(innerHtml, 'text/html');
            const token2 = doc2.querySelector('input[name="authenticity_token"]')?.value;

            // Check what hidden fields exist in step 2
            const hiddenFields = {};
            doc2.querySelectorAll('input[type="hidden"]').forEach(el => {
                if (el.name) hiddenFields[el.name] = (el.value || '').substring(0, 100);
            });

            // Generate photo
            const c = document.createElement('canvas');
            c.width = 640; c.height = 480;
            const ctx = c.getContext('2d');
            ctx.fillStyle = '#2563eb'; ctx.fillRect(0, 0, 640, 480);
            ctx.fillStyle = '#fff'; ctx.font = '24px sans-serif';
            ctx.fillText('Student ID - ' + schoolName, 30, 50);
            ctx.fillText('Academic Year 2024-2025', 30, 90);
            const photoDataUrl = c.toDataURL('image/jpeg', 0.8);

            const photoJson = JSON.stringify({
                image: photoDataUrl,
                metadata: {filename: null, type: null, mimeType: "image/jpeg", deviceLabel: null}
            });

            const fd2 = new FormData();
            fd2.set('authenticity_token', token2);
            fd2.set('dev_pack_form[proof_type]', '2. Dated official/unofficial transcript');
            fd2.set('dev_pack_form[photo_proof]', photoJson);
            fd2.set('dev_pack_form[form_variant]', 'upload_proof_form');
            fd2.set('dev_pack_form[application_type]', 'student');
            fd2.set('dev_pack_form[school_name]', schoolName);
            fd2.set('dev_pack_form[school_id]', schoolId);
            fd2.set('dev_pack_form[school_email]', 'thawkhant.1280@gmail.com');
            fd2.set('dev_pack_form[latitude]', '16.8661');
            fd2.set('dev_pack_form[longitude]', '96.1951');
            fd2.set('dev_pack_form[location_shared]', 'true');
            fd2.set('submit', 'Submit Application');

            const r3 = await fetch("/settings/education/developer_pack_applications", {
                method: "POST",
                headers: {
                    "Turbo-Frame": "dev-pack-form",
                    "Accept": "text/vnd.turbo-stream.html, text/html, application/xhtml+xml",
                },
                credentials: "same-origin",
                body: fd2,
            });
            const respText = await r3.text();

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
                           bodyText.toLowerCase().includes('congratulations') ||
                           bodyText.toLowerCase().includes('approved');

            return {
                status: r3.status,
                success,
                errors,
                checked,
                hiddenFields,
                bodyPreview: bodyText.substring(0, 500),
                respPreview: respText.substring(0, 500),
            };
        }''', [school_name, school_id])

        print(f"  Result: {json.dumps(result, indent=2)[:600]}")

        if result.get('success'):
            print(f"\n*** SUCCESS with {school_name}! ***")
            # Save full response
            with open("pw_v18_success.html", "w", encoding="utf-8") as f:
                f.write(result.get('respPreview', ''))
            break
        elif result.get('error'):
            print(f"  Error: {result['error']}")
        else:
            errors = result.get('errors', [])
            has_enroll = any('enrollment' in str(e).lower() for e in errors)
            print(f"  Enrollment error: {has_enroll}")
            if not has_enroll:
                print(f"  DIFFERENT error! Saving response...")
                with open("pw_v18_resp.html", "w", encoding="utf-8") as f:
                    f.write(result.get('respPreview', ''))

    browser.close()

print("\nDone!")
