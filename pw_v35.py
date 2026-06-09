"""v35: Complete 3-step education application.
Step 1: School info -> Step 2: Photo proof -> Step 3: Why not on campus -> Submit
"""
import os, sys, json
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
import pyotp
load_dotenv()

USERNAME = os.environ['GITHUB_USERNAME']
PASSWORD = os.environ['GITHUB_PASSWORD']
TOTP_SECRET = "SFDHLAA7MDH2S7TN"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
    )
    page = context.new_page()

    # Login
    page.goto("https://github.com/login", timeout=60000, wait_until="load")
    page.wait_for_timeout(2000)
    if "login" in page.url:
        page.fill('#login_field', USERNAME)
        page.fill('#password', PASSWORD)
        page.click('input[name="commit"]')
        page.wait_for_timeout(5000)
        if "two-factor" in page.url or "sessions" in page.url:
            otp = pyotp.TOTP(TOTP_SECRET).now()
            for sel in ['#app_totp', 'input[name="app_otp"]', 'input[name="otp"]']:
                f = page.query_selector(sel)
                if f: f.fill(otp); break
            page.wait_for_timeout(500)
            try: page.click('button[type="submit"]', timeout=5000)
            except: pass
            page.wait_for_load_state("load", timeout=30000)
            page.wait_for_timeout(3000)
    print(f"Logged in: {'login' not in page.url}")

    page.goto("https://github.com/settings/education/developer_pack_applications/new", timeout=120000, wait_until="load")
    page.wait_for_timeout(3000)

    # === ALL 3 STEPS IN ONE evaluate ===
    result = page.evaluate('''async () => {
        const log = [];

        // === STEP 1: School info ===
        log.push("=== Step 1: School info ===");
        const r1 = await fetch("/settings/education/developer_pack_applications/new", {
            headers: {"Accept": "text/html", "Turbo-Frame": "dev-pack-form"},
            credentials: "same-origin",
        });
        const formHtml = await r1.text();
        const doc = new DOMParser().parseFromString(formHtml, 'text/html');
        const form = doc.querySelector('form');
        if (!form) return {error: "no form for step 1", log};

        const fd1 = new FormData();
        const token1 = form.querySelector('input[name="authenticity_token"]');
        if (token1) fd1.set('authenticity_token', token1.value);
        fd1.set('dev_pack_form[application_type]', 'student');
        fd1.set('dev_pack_form[school_name]', 'Yangon Technological University');
        fd1.set('dev_pack_form[school_email]', 'thawkhant.1280@gmail.com');
        fd1.set('dev_pack_form[latitude]', '16.8661');
        fd1.set('dev_pack_form[longitude]', '96.1951');
        fd1.set('dev_pack_form[location_shared]', 'true');
        fd1.set('dev_pack_form[form_variant]', 'initial_form');
        fd1.set('dev_pack_form[browser_location]', '');
        fd1.set('dev_pack_form[utm_source]', '');
        fd1.set('dev_pack_form[utm_content]', '');
        fd1.set('continue', 'Continue');

        const s1 = await fetch("/settings/education/developer_pack_applications", {
            method: "POST",
            headers: {"Turbo-Frame": "dev-pack-form"},
            credentials: "same-origin",
            body: fd1,
        });
        const s1Text = await s1.text();
        if (!s1Text.includes('proof_type')) {
            return {error: "step 1 failed", log, preview: s1Text.substring(0, 500)};
        }
        log.push("Step 1 SUCCESS - got proof form");

        // Parse step 2 form
        let s2Html = s1Text;
        if (s1Text.includes('<turbo-stream')) {
            const tmp = new DOMParser().parseFromString(s1Text, 'text/html');
            const tmpl = tmp.querySelector('template');
            if (tmpl) {
                const c = document.createElement('div');
                c.appendChild(tmpl.content.cloneNode(true));
                s2Html = c.innerHTML;
            }
        }
        const doc2 = new DOMParser().parseFromString(s2Html, 'text/html');
        const token2 = doc2.querySelector('input[name="authenticity_token"]');

        // === STEP 2: Photo proof ===
        log.push("=== Step 2: Photo proof ===");

        // Generate photo
        const canvas = document.createElement('canvas');
        canvas.width = 640; canvas.height = 480;
        const ctx = canvas.getContext('2d');
        ctx.fillStyle = '#2563eb'; ctx.fillRect(0, 0, 640, 480);
        ctx.fillStyle = '#fff'; ctx.font = '24px sans-serif';
        ctx.fillText('Student ID - Yangon Technological University', 30, 50);
        ctx.fillText('Academic Year 2024-2025', 30, 90);
        ctx.fillText('Student Name: Nwe Yi', 30, 130);
        ctx.fillText('Registration No: YTU-2024-1234', 30, 170);
        const photoDataUrl = canvas.toDataURL('image/jpeg', 0.8);

        const photoJson = JSON.stringify({
            image: photoDataUrl,
            metadata: {filename: null, type: null, mimeType: "image/jpeg", deviceLabel: null}
        });

        const fd2 = new FormData();
        if (token2) fd2.set('authenticity_token', token2.value);
        // Include all hidden fields from step 2 form
        doc2.querySelectorAll('input[type="hidden"]').forEach(el => {
            if (el.name && el.name !== 'authenticity_token')
                fd2.set(el.name, el.value || '');
        });
        fd2.set('dev_pack_form[proof_type]', '2. Dated official/unofficial transcript');
        fd2.set('dev_pack_form[photo_proof]', photoJson);
        fd2.set('dev_pack_form[form_variant]', 'upload_proof_form');
        fd2.set('continue', 'Process my application');

        const s2 = await fetch("/settings/education/developer_pack_applications", {
            method: "POST",
            headers: {"Turbo-Frame": "dev-pack-form"},
            credentials: "same-origin",
            body: fd2,
        });
        const s2Text = await s2.text();

        // Check if step 2 succeeded
        const hasCampus = s2Text.includes('not on campus') || s2Text.includes('far_from_campus');
        const hasSuccess = s2Text.toLowerCase().includes('thank') ||
                          s2Text.toLowerCase().includes('submitted') ||
                          s2Text.toLowerCase().includes('pending') ||
                          s2Text.toLowerCase().includes('approved');
        const hasError = s2Text.includes('Banner--error') || s2Text.includes('flash-error');

        if (hasError && !hasCampus) {
            const errDoc = new DOMParser().parseFromString(s2Text, 'text/html');
            const errors = [];
            errDoc.querySelectorAll('.Banner-title, [data-target*="titleText"]').forEach(el => {
                errors.push(el.textContent.trim().substring(0, 200));
            });
            return {error: "step 2 failed", errors, log, preview: s2Text.substring(0, 500)};
        }

        if (hasSuccess) {
            log.push("Step 2 SUCCESS - application submitted!");
            return {success: true, log, bodyText: new DOMParser().parseFromString(s2Text, 'text/html').body?.textContent?.trim()?.substring(0, 500) || ''};
        }

        if (hasCampus) {
            log.push("Step 2 SUCCESS - got campus question form");

            // Parse step 3 form
            let s3Html = s2Text;
            if (s2Text.includes('<turbo-stream')) {
                const tmp = new DOMParser().parseFromString(s2Text, 'text/html');
                const tmpl = tmp.querySelector('template');
                if (tmpl) {
                    const c = document.createElement('div');
                    c.appendChild(tmpl.content.cloneNode(true));
                    s3Html = c.innerHTML;
                }
            }
            const doc3 = new DOMParser().parseFromString(s3Html, 'text/html');
            const token3 = doc3.querySelector('input[name="authenticity_token"]');

            // List radio options for campus reason
            const radioOptions = [];
            doc3.querySelectorAll('input[type="radio"]').forEach(el => {
                const label = doc3.querySelector('label[for="' + el.id + '"]');
                radioOptions.push({
                    name: el.name,
                    value: el.value,
                    label: label?.textContent?.trim()?.substring(0, 100) || '',
                });
            });
            log.push("Radio options: " + JSON.stringify(radioOptions));

            // Get all hidden fields
            const hiddenFields = {};
            doc3.querySelectorAll('input[type="hidden"]').forEach(el => {
                if (el.name && el.name !== 'authenticity_token')
                    hiddenFields[el.name] = (el.value || '').substring(0, 80);
            });
            log.push("Hidden fields: " + JSON.stringify(hiddenFields));

            // Check for file upload field
            const fileInputs = [];
            doc3.querySelectorAll('input[type="file"]').forEach(el => {
                fileInputs.push({name: el.name, id: el.id});
            });
            log.push("File inputs: " + JSON.stringify(fileInputs));

            // Check for textarea
            const textareas = [];
            doc3.querySelectorAll('textarea').forEach(el => {
                textareas.push({name: el.name, id: el.id});
            });
            log.push("Textareas: " + JSON.stringify(textareas));

            // === STEP 3: Submit campus reason ===
            log.push("=== Step 3: Campus reason ===");

            const fd3 = new FormData();
            if (token3) fd3.set('authenticity_token', token3.value);
            // Include all hidden fields
            doc3.querySelectorAll('input[type="hidden"]').forEach(el => {
                if (el.name && el.name !== 'authenticity_token')
                    fd3.set(el.name, el.value || '');
            });

            // Select reason: "All coursework is via distance learning"
            // Find the correct field name from radio buttons
            if (radioOptions.length > 0) {
                const distanceOption = radioOptions.find(o =>
                    o.label.toLowerCase().includes('distance') ||
                    o.value.toLowerCase().includes('distance')
                );
                const semesterOption = radioOptions.find(o =>
                    o.label.toLowerCase().includes('not yet started') ||
                    o.value.toLowerCase().includes('not_started')
                );
                const chosenOption = distanceOption || semesterOption || radioOptions[0];
                fd3.set(chosenOption.name, chosenOption.value);
                log.push("Chosen option: " + JSON.stringify(chosenOption));
            }

            // Use the form_variant from the hidden fields (far_from_campus_proof_form)
            // Don't override - it's already set from hidden fields
            fd3.set('continue', 'Submit Application');

            const s3 = await fetch("/settings/education/developer_pack_applications", {
                method: "POST",
                headers: {"Turbo-Frame": "dev-pack-form"},
                credentials: "same-origin",
                body: fd3,
            });
            const s3Text = await s3.text();

            // Check final result
            const finalDoc = new DOMParser().parseFromString(s3Text, 'text/html');
            const finalText = finalDoc.body?.textContent?.trim()?.replace(/\\s+/g, ' ') || '';
            const finalSuccess = s3Text.toLowerCase().includes('thank') ||
                               s3Text.toLowerCase().includes('submitted') ||
                               s3Text.toLowerCase().includes('pending') ||
                               s3Text.toLowerCase().includes('approved') ||
                               s3Text.toLowerCase().includes('review');
            const finalErrors = [];
            finalDoc.querySelectorAll('.Banner-title, [data-target*="titleText"], .flash-error').forEach(el => {
                finalErrors.push(el.textContent.trim().substring(0, 200));
            });

            // Sent fields for debugging
            const sent3 = {};
            for (const [k, v] of fd3.entries()) {
                if (k !== 'authenticity_token')
                    sent3[k] = (typeof v === 'string' ? v.substring(0, 80) : v.name);
            }

            return {
                step: 3,
                status: s3.status,
                success: finalSuccess,
                errors: finalErrors,
                sent: sent3,
                bodyText: finalText.substring(0, 800),
                htmlPreview: s3Text.substring(0, 1000),
                log,
            };
        }

        // Unknown state
        return {
            error: "unknown state after step 2",
            log,
            bodyText: new DOMParser().parseFromString(s2Text, 'text/html').body?.textContent?.trim()?.substring(0, 500) || '',
            htmlPreview: s2Text.substring(0, 500),
        };
    }''')

    print("\n".join(result.get('log', [])))
    print(f"\n=== FINAL RESULT ===")
    print(f"Success: {result.get('success', False)}")
    print(f"Errors: {result.get('errors', [])}")
    if result.get('sent'):
        print(f"Sent: {json.dumps(result.get('sent', {}), indent=2)}")
    print(f"\nBody text:\n{result.get('bodyText', '')[:500]}")
    if result.get('error'):
        print(f"\nError: {result['error']}")
        if result.get('preview'):
            print(f"Preview: {result['preview'][:300]}")

    browser.close()
print("\nDone!")
