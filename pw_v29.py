"""v29: Try with YTU (no email requirement) + school_id field.
UCSY had email requirement error. YTU only had enrollment_size error.
With school_id fixing enrollment, YTU should work.
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

    # Navigate to education form
    page.goto("https://github.com/settings/education/developer_pack_applications/new", timeout=120000, wait_until="load")
    page.wait_for_timeout(3000)

    # First, check school attributes for YTU via the schools API
    school_info = page.evaluate('''async () => {
        const r = await fetch("/settings/education/developer_pack_applications/schools?q=Yangon+Technological", {
            headers: {"Accept": "text/fragment+html"}
        });
        const text = await r.text();
        return text.substring(0, 2000);
    }''')
    print(f"YTU school info:\n{school_info[:500]}")

    # Extract attributes from school HTMLimport re
    # Check if YTU requires email or has specific attributes

    # Submit step 1 with YTU
    result = page.evaluate('''async () => {
        const form = document.querySelector('form[action="/settings/education/developer_pack_applications"]');
        if (!form) return {error: "no form"};

        const fd = new FormData(form);
        fd.set('dev_pack_form[application_type]', 'student');
        fd.set('dev_pack_form[school_name]', 'Yangon Technological University');
        fd.set('dev_pack_form[school_id]', '102038');
        fd.set('dev_pack_form[form_variant]', 'initial_form');
        fd.set('dev_pack_form[latitude]', '16.8661');
        fd.set('dev_pack_form[longitude]', '96.1951');
        fd.set('dev_pack_form[location_shared]', 'true');
        fd.set('dev_pack_form[browser_location]', '16.8661,96.1951');

        const r = await fetch("/settings/education/developer_pack_applications", {
            method: "POST",
            headers: {
                "Turbo-Frame": "dev-pack-form",
                "Accept": "text/vnd.turbo-stream.html, text/html, application/xhtml+xml",
            },
            credentials: "same-origin",
            body: fd,
        });
        const text = await r.text();
        const hasEnrollment = text.includes('Enrollment size');
        const hasProof = text.includes('proof_type') || text.includes('photo_proof');
        
        // Parse errors
        const doc = new DOMParser().parseFromString(text, 'text/html');
        const errors = [];
        doc.querySelectorAll('.Banner-title, [data-target*="titleText"]').forEach(el => {
            errors.push(el.textContent.trim().substring(0, 300));
        });

        // Check if step 2 form fields exist
        const step2Fields = [];
        doc.querySelectorAll('input, select, textarea').forEach(el => {
            if (el.name && !el.name.includes('authenticity'))
                step2Fields.push({name: el.name, value: (el.value || '').substring(0, 50)});
        });

        return {
            status: r.status,
            hasEnrollment,
            hasProof,
            errors,
            step2Fields: step2Fields.slice(0, 15),
            bodyLen: text.length,
            fullText: text.substring(0, 2000),
        };
    }''')

    print(f"\n=== YTU Step 1 Result ===")
    print(f"Status: {result['status']}")
    print(f"Enrollment error: {result['hasEnrollment']}")
    print(f"Has proof fields: {result['hasProof']}")
    print(f"Errors: {result['errors']}")
    print(f"Step2 fields: {json.dumps(result.get('step2Fields', []), indent=2)}")
    print(f"\nResponse:\n{result.get('fullText', '')[:1500]}")

    # If step 1 succeeded (has proof fields), proceed to step 2
    if result['hasProof']:
        print("\n\n=== Step 2: Submit photo proof ===")
        step2 = page.evaluate('''async () => {
            // Generate photo
            const c = document.createElement('canvas');
            c.width = 640; c.height = 480;
            const ctx = c.getContext('2d');
            ctx.fillStyle = '#2563eb'; ctx.fillRect(0, 0, 640, 480);
            ctx.fillStyle = '#fff'; ctx.font = '24px sans-serif';
            ctx.fillText('Student ID - YTU', 30, 50);
            ctx.fillText('Academic Year 2024-2025', 30, 90);
            const photoDataUrl = c.toDataURL('image/jpeg', 0.8);

            const photoJson = JSON.stringify({
                image: photoDataUrl,
                metadata: {filename: null, type: null, mimeType: "image/jpeg", deviceLabel: null}
            });

            // Get step 2 form from the response we got
            // Actually we need to set it on the current page's form
            const form = document.querySelector('form[action="/settings/education/developer_pack_applications"]');
            if (!form) return {error: "no form for step 2"};

            const fd = new FormData(form);
            fd.set('dev_pack_form[photo_proof]', photoJson);
            fd.set('dev_pack_form[proof_type]', '2. Dated official/unofficial transcript');
            fd.set('dev_pack_form[form_variant]', 'upload_proof_form');

            const r = await fetch("/settings/education/developer_pack_applications", {
                method: "POST",
                headers: {
                    "Turbo-Frame": "dev-pack-form",
                    "Accept": "text/vnd.turbo-stream.html, text/html, application/xhtml+xml",
                },
                credentials: "same-origin",
                body: fd,
            });
            const text = await r.text();
            const success = text.toLowerCase().includes('thank') ||
                           text.toLowerCase().includes('submitted') ||
                           text.toLowerCase().includes('pending') ||
                           text.toLowerCase().includes('approved');

            const doc = new DOMParser().parseFromString(text, 'text/html');
            const errors = [];
            doc.querySelectorAll('.Banner-title, [data-target*="titleText"]').forEach(el => {
                errors.push(el.textContent.trim().substring(0, 300));
            });

            return {
                status: r.status,
                success,
                errors,
                bodyLen: text.length,
                preview: text.substring(0, 1000),
            };
        }''')
        print(f"Step 2 result: {json.dumps(step2, indent=2)[:800]}")

    browser.close()
print("\nDone!")
