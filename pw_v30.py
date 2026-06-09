"""v30: Test multiple theories about the hidden school_name input.
There are TWO inputs named dev_pack_form[school_name]:
  1. Hidden (id=dev_pack_form_school_name, class=d-none)  
  2. Visible (id=js-school-name-search)
The React component likely sets different values for each.
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

    # Test 1: Set hidden school_name to school_id, visible to school name
    # No extra school_id field - let the dual school_name carry the info
    tests = [
        {
            "label": "hidden=school_name, visible=school_name (normal, no school_id)",
            "hiddenVal": "Yangon Technological University",
            "visibleVal": "Yangon Technological University",
            "addSchoolId": False,
        },
        {
            "label": "hidden=school_id, visible=school_name",
            "hiddenVal": "102038",
            "visibleVal": "Yangon Technological University",
            "addSchoolId": False,
        },
        {
            "label": "hidden=school_name, visible=school_name + school_id field",
            "hiddenVal": "Yangon Technological University",
            "visibleVal": "Yangon Technological University",
            "addSchoolId": True,
        },
    ]

    for i, test in enumerate(tests):
        print(f"\n=== Test {i+1}: {test['label']} ===")
        
        # Need fresh CSRF token for each test - reload page
        if i > 0:
            page.goto("https://github.com/settings/education/developer_pack_applications/new", timeout=120000, wait_until="load")
            page.wait_for_timeout(3000)

        result = page.evaluate('''(params) => {
            // Set input values in DOM first
            const hidden = document.getElementById('dev_pack_form_school_name');
            const visible = document.getElementById('js-school-name-search');
            
            if (hidden) hidden.value = params.hiddenVal;
            if (visible) visible.value = params.visibleVal;

            // Set other fields
            const latInput = document.getElementById('js-developer-pack-application-latitude-input');
            const lonInput = document.getElementById('js-developer-pack-application-longitude-input');
            const locInput = document.getElementById('js-developer-pack-application-location-shared-input');
            const browserLocInput = document.getElementById('dev_pack_form_browser_location');
            const formVariant = document.getElementById('dev_pack_form_form_variant');
            
            if (latInput) latInput.value = '16.8661';
            if (lonInput) lonInput.value = '96.1951';
            if (locInput) locInput.value = 'true';
            if (browserLocInput) browserLocInput.value = '16.8661,96.1951';
            if (formVariant) formVariant.value = 'initial_form';

            // Select student radio
            const radio = document.querySelector('input[value="student"]');
            if (radio) radio.checked = true;

            // Create FormData from form (includes both school_name inputs)
            const form = document.querySelector('form[action="/settings/education/developer_pack_applications"]');
            const fd = new FormData(form);
            
            if (params.addSchoolId) {
                fd.append('dev_pack_form[school_id]', '102038');
            }

            // Log what's being sent
            const entries = [];
            for (const [k, v] of fd.entries()) {
                if (!k.includes('authenticity'))
                    entries.push(k + '=' + (typeof v === 'string' ? v : v.name).substring(0, 80));
            }

            return {entries, formAction: form.action};
        }''', test)
        print(f"  Entries: {json.dumps(result.get('entries', []), indent=4)}")

        # Now submit
        submit_result = page.evaluate('''async (params) => {
            const hidden = document.getElementById('dev_pack_form_school_name');
            const visible = document.getElementById('js-school-name-search');
            if (hidden) hidden.value = params.hiddenVal;
            if (visible) visible.value = params.visibleVal;

            const latInput = document.getElementById('js-developer-pack-application-latitude-input');
            const lonInput = document.getElementById('js-developer-pack-application-longitude-input');
            const locInput = document.getElementById('js-developer-pack-application-location-shared-input');
            const browserLocInput = document.getElementById('dev_pack_form_browser_location');
            const formVariant = document.getElementById('dev_pack_form_form_variant');
            
            if (latInput) latInput.value = '16.8661';
            if (lonInput) lonInput.value = '96.1951';
            if (locInput) locInput.value = 'true';
            if (browserLocInput) browserLocInput.value = '16.8661,96.1951';
            if (formVariant) formVariant.value = 'initial_form';

            const radio = document.querySelector('input[value="student"]');
            if (radio) radio.checked = true;

            const form = document.querySelector('form[action="/settings/education/developer_pack_applications"]');
            const fd = new FormData(form);
            
            if (params.addSchoolId) {
                fd.append('dev_pack_form[school_id]', '102038');
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
            const text = await r.text();
            
            const hasEnrollment = text.includes('Enrollment size');
            const hasProof = text.includes('proof_type') || text.includes('photo_proof');
            
            let errors = text.match(/Banner-title[^>]*>([^<]+)/g) || [];
            errors = errors.map(e => e.replace(/Banner-title[^>]*>/, '').trim());

            return {
                status: r.status,
                hasEnrollment,
                hasProof,
                errors,
                bodyLen: text.length,
                preview: text.substring(0, 500),
            };
        }''', test)

        print(f"  Status: {submit_result['status']}")
        print(f"  Enrollment: {submit_result['hasEnrollment']}, Proof: {submit_result['hasProof']}")
        print(f"  Errors: {submit_result['errors']}")
        if submit_result['hasProof']:
            print("  *** STEP 1 SUCCESS - GOT STEP 2 FORM! ***")

    browser.close()
print("\nDone!")
