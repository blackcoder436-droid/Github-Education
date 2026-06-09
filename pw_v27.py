"""v27: Try submitting step 1 with school_id via fetch(), test various field names.
Key insight: The page has no JS scripts loaded (turbo-frame-only).
We need to manually include whatever hidden field the React component would set.
"""
import os, sys, json
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
import pyotp
load_dotenv()

USERNAME = os.environ['GITHUB_USERNAME']
PASSWORD = os.environ['GITHUB_PASSWORD']
TOTP_SECRET = "SFDHLAA7MDH2S7TN"

# UCSY school info from schools API
SCHOOL_NAME = "University of Computer Studies, Yangon"
SCHOOL_ID = "7620"

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
    print(f"URL: {page.url}")

    # First, dump ALL form inputs with their names, types, values
    form_dump = page.evaluate('''() => {
        const form = document.querySelector('form[action="/settings/education/developer_pack_applications"]');
        if (!form) return {error: "no form"};
        const inputs = [];
        form.querySelectorAll('input, select, textarea').forEach(el => {
            inputs.push({
                tag: el.tagName,
                name: el.name || '',
                type: el.type || '',
                value: (el.value || '').substring(0, 100),
                id: el.id || '',
                hidden: el.type === 'hidden' || el.closest('.d-none') !== null,
                className: el.className?.substring?.(0, 50) || '',
            });
        });
        return {action: form.action, method: form.method, inputs};
    }''')
    print(f"\nForm dump:")
    print(json.dumps(form_dump, indent=2))

    # Now test: submit step 1 via fetch with school_id in various field name formats
    tests = [
        {"extra_field": "dev_pack_form[school_id]", "extra_value": SCHOOL_ID},
        {"extra_field": "dev_pack_form[selected_school_id]", "extra_value": SCHOOL_ID},
        {"extra_field": "school_id", "extra_value": SCHOOL_ID},
    ]

    for test in tests:
        result = page.evaluate('''async (params) => {
            const form = document.querySelector('form[action="/settings/education/developer_pack_applications"]');
            const fd = new FormData(form);
            
            // Set step 1 fields
            fd.set('dev_pack_form[application_type]', 'student');
            fd.set('dev_pack_form[school_name]', params.schoolName);
            fd.set('dev_pack_form[form_variant]', 'initial_form');
            fd.set('dev_pack_form[latitude]', '16.8661');
            fd.set('dev_pack_form[longitude]', '96.1951');
            fd.set('dev_pack_form[location_shared]', 'true');
            fd.set('dev_pack_form[browser_location]', '16.8661,96.1951');
            
            // Add extra test field
            fd.set(params.extraField, params.extraValue);

            const r = await fetch("/settings/education/developer_pack_applications", {
                method: "POST",
                headers: {"Turbo-Frame": "dev-pack-form"},
                credentials: "same-origin",
                body: fd,
            });
            const text = await r.text();
            
            // Check for known errors or success
            const hasEnrollment = text.includes('Enrollment size');
            const hasProof = text.includes('proof_type') || text.includes('photo_proof');
            const hasError = text.includes('Banner-title') || text.includes('error');

            // Extract error message
            let errorMsg = '';
            const match = text.match(/Banner-title[^>]*>([^<]+)/);
            if (match) errorMsg = match[1].trim();
            
            // Also try x-banner
            const match2 = text.match(/x-banner\.titleText[^>]*>([^<]+)/);
            if (match2) errorMsg += ' | ' + match2[1].trim();

            return {
                field: params.extraField,
                status: r.status,
                hasEnrollment,
                hasProof,
                errorMsg: errorMsg || 'none',
                bodyLen: text.length,
                preview: text.substring(0, 300),
            };
        }''', {
            "schoolName": SCHOOL_NAME,
            "extraField": test["extra_field"],
            "extraValue": test["extra_value"],
            "schoolId": SCHOOL_ID,
        })
        print(f"\nTest: {test['extra_field']}={test['extra_value']}")
        print(f"  Status: {result['status']}, Enrollment: {result['hasEnrollment']}, Proof: {result['hasProof']}")
        print(f"  Error: {result['errorMsg']}")
        print(f"  Preview: {result['preview'][:200]}")

        # If this test shows proof fields (step 2), we found it!
        if result['hasProof'] and not result['hasEnrollment']:
            print("  *** SUCCESS - enrollment_size error gone! ***")

    # Also try: maybe the issue is that school_name needs to be the EXACT autocomplete value
    # Let me also try sending with id-style school_name like "7620"
    result2 = page.evaluate('''async () => {
        const form = document.querySelector('form[action="/settings/education/developer_pack_applications"]');
        const fd = new FormData(form);
        fd.set('dev_pack_form[application_type]', 'student');
        fd.set('dev_pack_form[school_name]', 'University of Computer Studies, Yangon');
        fd.set('dev_pack_form[school_id]', '7620');
        fd.set('dev_pack_form[selected_school_id]', '7620');
        fd.set('dev_pack_form[form_variant]', 'initial_form');
        fd.set('dev_pack_form[latitude]', '16.8661');
        fd.set('dev_pack_form[longitude]', '96.1951');
        fd.set('dev_pack_form[location_shared]', 'true');
        fd.set('dev_pack_form[browser_location]', '16.8661,96.1951');
        fd.set('selected_school_id', '7620');
        fd.set('school_id', '7620');

        const r = await fetch("/settings/education/developer_pack_applications", {
            method: "POST",
            headers: {"Turbo-Frame": "dev-pack-form"},
            credentials: "same-origin",
            body: fd,
        });
        const text = await r.text();
        const hasEnrollment = text.includes('Enrollment size');
        const hasProof = text.includes('proof_type') || text.includes('photo_proof');
        
        let errorMsg = '';
        const match = text.match(/data-target="x-banner\.titleText"[^>]*>([^<]+)/);
        if (match) errorMsg = match[1].trim();
        if (!errorMsg) {
            const m2 = text.match(/Banner-title[^>]*>([^<]+)/);
            if (m2) errorMsg = m2[1].trim();
        }

        return {status: r.status, hasEnrollment, hasProof, errorMsg: errorMsg || 'none'};
    }''')
    print(f"\nKitchen sink test (all ID fields):")
    print(f"  Status: {result2['status']}, Enrollment: {result2['hasEnrollment']}, Proof: {result2['hasProof']}")
    print(f"  Error: {result2['errorMsg']}")

    browser.close()
print("Done!")
