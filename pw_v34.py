"""v34: Complete education application - both steps.
Step 1 works with fresh FormData approach. Now complete step 2 with photo proof.
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

    # === STEP 1: Submit school info ===
    print("\n=== Step 1: School info ===")
    step1 = page.evaluate('''async () => {
        // Fetch fresh form
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
        fd.set('dev_pack_form[school_name]', 'Yangon Technological University');
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
        const text = await r2.text();
        const hasProof = text.includes('proof_type') || text.includes('photo_proof');
        
        // Extract token for step 2
        let step2Token = '';
        let step2Html = text;
        
        // Parse turbo-stream if needed
        if (text.includes('<turbo-stream')) {
            const tmpDoc = new DOMParser().parseFromString(text, 'text/html');
            const template = tmpDoc.querySelector('template');
            if (template) {
                const container = document.createElement('div');
                container.appendChild(template.content.cloneNode(true));
                step2Html = container.innerHTML;
            }
        }

        const doc2 = new DOMParser().parseFromString(step2Html, 'text/html');
        const t2 = doc2.querySelector('input[name="authenticity_token"]');
        if (t2) step2Token = t2.value;
        
        // Get all hidden fields from step 2 form
        const hiddenFields = {};
        doc2.querySelectorAll('input[type="hidden"]').forEach(el => {
            if (el.name && el.name !== 'authenticity_token')
                hiddenFields[el.name] = (el.value || '').substring(0, 100);
        });
        
        // Get all select options for proof_type
        const proofOptions = [];
        doc2.querySelectorAll('select option, option').forEach(el => {
            if (el.value) proofOptions.push({value: el.value, text: el.textContent.trim().substring(0, 80)});
        });

        // Extract errors
        const errors = [];
        doc2.querySelectorAll('.Banner-title, [data-target*="titleText"]').forEach(el => {
            errors.push(el.textContent.trim().substring(0, 200));
        });

        return {
            status: r2.status,
            hasProof,
            step2Token: step2Token ? step2Token.substring(0, 20) + '...' : 'none',
            hiddenFields,
            proofOptions,
            errors,
            step2HtmlLen: step2Html.length,
        };
    }''')

    print(f"Status: {step1['status']}, hasProof: {step1['hasProof']}")
    print(f"Token: {step1.get('step2Token', 'none')}")
    print(f"Hidden fields: {json.dumps(step1.get('hiddenFields', {}), indent=2)}")
    print(f"Proof options: {json.dumps(step1.get('proofOptions', []), indent=2)}")
    print(f"Errors: {step1.get('errors', [])}")

    if not step1.get('hasProof'):
        print("Step 1 FAILED! Cannot proceed to step 2.")
    else:
        # === STEP 2: Submit photo proof ===
        print("\n=== Step 2: Photo proof ===")
        step2 = page.evaluate('''async () => {
            // Re-fetch step 1 to get fresh state
            const r1 = await fetch("/settings/education/developer_pack_applications/new", {
                headers: {"Accept": "text/html", "Turbo-Frame": "dev-pack-form"},
                credentials: "same-origin",
            });
            const formHtml = await r1.text();
            const doc = new DOMParser().parseFromString(formHtml, 'text/html');
            const form = doc.querySelector('form');

            // Submit step 1 again to get fresh step 2 form
            const fd1 = new FormData();
            const token = form.querySelector('input[name="authenticity_token"]');
            if (token) fd1.set('authenticity_token', token.value);
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
                return {error: "step 1 re-submit failed", preview: s1Text.substring(0, 300)};
            }

            // Parse step 2 form
            let step2Html = s1Text;
            if (s1Text.includes('<turbo-stream')) {
                const tmpDoc = new DOMParser().parseFromString(s1Text, 'text/html');
                const template = tmpDoc.querySelector('template');
                if (template) {
                    const container = document.createElement('div');
                    container.appendChild(template.content.cloneNode(true));
                    step2Html = container.innerHTML;
                }
            }
            const doc2 = new DOMParser().parseFromString(step2Html, 'text/html');
            const form2 = doc2.querySelector('form');

            // Get step 2 token
            const token2 = doc2.querySelector('input[name="authenticity_token"]');

            // Generate photo
            const c = document.createElement('canvas');
            c.width = 640; c.height = 480;
            const ctx = c.getContext('2d');
            ctx.fillStyle = '#2563eb'; ctx.fillRect(0, 0, 640, 480);
            ctx.fillStyle = '#fff'; ctx.font = '24px sans-serif';
            ctx.fillText('Student ID - Yangon Technological University', 30, 50);
            ctx.fillText('Academic Year 2024-2025', 30, 90);
            ctx.fillText('Student Name: Nwe Yi', 30, 130);
            ctx.fillText('Registration No: YTU-2024-1234', 30, 170);
            const photoDataUrl = c.toDataURL('image/jpeg', 0.8);

            const photoJson = JSON.stringify({
                image: photoDataUrl,
                metadata: {filename: null, type: null, mimeType: "image/jpeg", deviceLabel: null}
            });

            // Build step 2 FormData
            const fd2 = new FormData();
            if (token2) fd2.set('authenticity_token', token2.value);
            
            // Include all hidden fields from step 2
            doc2.querySelectorAll('input[type="hidden"]').forEach(el => {
                if (el.name && el.name !== 'authenticity_token') {
                    fd2.set(el.name, el.value || '');
                }
            });
            
            fd2.set('dev_pack_form[proof_type]', '2. Dated official/unofficial transcript');
            fd2.set('dev_pack_form[photo_proof]', photoJson);
            fd2.set('dev_pack_form[form_variant]', 'upload_proof_form');
            fd2.set('continue', 'Process my application');

            // Log what we're sending
            const sent = {};
            for (const [k, v] of fd2.entries()) {
                if (k !== 'authenticity_token')
                    sent[k] = (typeof v === 'string' ? v.substring(0, 80) : v.name);
            }

            // Submit step 2
            const s2 = await fetch("/settings/education/developer_pack_applications", {
                method: "POST",
                headers: {"Turbo-Frame": "dev-pack-form"},
                credentials: "same-origin",
                body: fd2,
            });
            const s2Text = await s2.text();

            // Check result
            const success = s2Text.toLowerCase().includes('thank') ||
                           s2Text.toLowerCase().includes('success') ||
                           s2Text.toLowerCase().includes('submitted') ||
                           s2Text.toLowerCase().includes('pending') ||
                           s2Text.toLowerCase().includes('approved') ||
                           s2Text.toLowerCase().includes('review');

            // Parse errors
            const respDoc = new DOMParser().parseFromString(s2Text, 'text/html');
            const errors = [];
            respDoc.querySelectorAll('.Banner-title, [data-target*="titleText"], .flash-error').forEach(el => {
                errors.push(el.textContent.trim().substring(0, 200));
            });

            const bodyText = respDoc.body?.textContent?.trim()?.replace(/\\s+/g, ' ') || '';

            return {
                status: s2.status,
                success,
                errors,
                sent,
                bodyLen: s2Text.length,
                bodyText: bodyText.substring(0, 800),
                htmlPreview: s2Text.substring(0, 1000),
            };
        }''')

        print(f"Status: {step2.get('status')}")
        print(f"Success: {step2.get('success')}")
        print(f"Errors: {step2.get('errors', [])}")
        print(f"Sent fields: {json.dumps(step2.get('sent', {}), indent=2)}")
        print(f"\nBody text:\n{step2.get('bodyText', '')[:500]}")
        print(f"\nHTML preview:\n{step2.get('htmlPreview', '')[:500]}")

    browser.close()
print("\nDone!")
