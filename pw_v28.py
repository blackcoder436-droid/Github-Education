"""v28: Single clean step 1 submission with dev_pack_form[school_id].
Previous test showed enrollment_size error disappears with school_id=7620.
Now do one clean request and capture full error details.
"""
import os, sys, json
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
import pyotp
load_dotenv()

USERNAME = os.environ['GITHUB_USERNAME']
PASSWORD = os.environ['GITHUB_PASSWORD']
TOTP_SECRET = "SFDHLAA7MDH2S7TN"

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

    # Single clean submission
    result = page.evaluate('''async () => {
        const form = document.querySelector('form[action="/settings/education/developer_pack_applications"]');
        if (!form) return {error: "no form"};

        const fd = new FormData(form);

        // Set required fields
        fd.set('dev_pack_form[application_type]', 'student');
        fd.set('dev_pack_form[school_name]', 'University of Computer Studies, Yangon');
        fd.set('dev_pack_form[school_id]', '7620');
        fd.set('dev_pack_form[form_variant]', 'initial_form');
        fd.set('dev_pack_form[latitude]', '16.8661');
        fd.set('dev_pack_form[longitude]', '96.1951');
        fd.set('dev_pack_form[location_shared]', 'true');
        fd.set('dev_pack_form[browser_location]', '16.8661,96.1951');

        // Log what we're sending
        const sent = {};
        for (const [k, v] of fd.entries()) {
            if (!k.includes('authenticity_token'))
                sent[k] = typeof v === 'string' ? v.substring(0, 100) : v.name;
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

        // Parse response
        const hasEnrollment = text.includes('Enrollment size');
        const hasProof = text.includes('proof_type') || text.includes('photo_proof');
        const hasCamera = text.includes('camera') || text.includes('webcam');
        
        // Extract error messages
        const doc = new DOMParser().parseFromString(text, 'text/html');
        const errors = [];
        doc.querySelectorAll('[data-target*="titleText"], .Banner-title, .flash-error, .Flash-body').forEach(el => {
            errors.push(el.textContent.trim().substring(0, 200));
        });

        // Check for form fields (step 2)
        const step2Fields = [];
        doc.querySelectorAll('input, select, textarea').forEach(el => {
            if (el.name && !el.name.includes('authenticity'))
                step2Fields.push(el.name + '=' + (el.value || '').substring(0, 50));
        });

        return {
            sent,
            status: r.status,
            hasEnrollment,
            hasProof,
            hasCamera,
            errors,
            step2Fields,
            bodyLen: text.length,
            fullText: text.substring(0, 1500),
        };
    }''')

    print(f"\nSent: {json.dumps(result.get('sent', {}), indent=2)}")
    print(f"\nResult:")
    print(f"  Status: {result['status']}")
    print(f"  hasEnrollment: {result['hasEnrollment']}")
    print(f"  hasProof: {result['hasProof']}")
    print(f"  hasCamera: {result['hasCamera']}")
    print(f"  Errors: {result['errors']}")
    print(f"  Step2 fields: {result.get('step2Fields', [])[:10]}")
    print(f"  Body length: {result['bodyLen']}")
    print(f"\nFull response (first 1500):")
    print(result.get('fullText', '')[:1500])

    browser.close()
print("\nDone!")
