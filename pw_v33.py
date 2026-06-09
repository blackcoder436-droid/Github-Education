"""v33: Replicate EXACT v18 approach (fresh form fetch + new FormData + continue button).
If this also gets 'There was a problem' instead of 'Enrollment size', confirms rate limiting.
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

    # Navigate to form page first (establishes context)
    page.goto("https://github.com/settings/education/developer_pack_applications/new", timeout=120000, wait_until="load")
    page.wait_for_timeout(3000)

    # EXACT v18 approach: fetch fresh form, create new FormData, submit
    result = page.evaluate('''async () => {
        // Step 1: Fetch fresh form
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

        // Submit step 1
        const r2 = await fetch("/settings/education/developer_pack_applications", {
            method: "POST",
            headers: {"Turbo-Frame": "dev-pack-form"},
            credentials: "same-origin",
            body: fd,
        });
        const text = await r2.text();

        const hasEnrollment = text.includes('Enrollment size');
        const hasProof = text.includes('proof_type') || text.includes('photo_proof');
        const hasProblem = text.includes('There was a problem');
        const hasError = text.includes('error') || text.includes('Error');

        // Extract all error messages
        const respDoc = new DOMParser().parseFromString(text, 'text/html');
        const errors = [];
        respDoc.querySelectorAll('.Banner-title, [data-target*="titleText"], .flash-error, .color-fg-danger').forEach(el => {
            const t = el.textContent.trim();
            if (t && t.length > 3) errors.push(t.substring(0, 300));
        });

        // Full body text
        const bodyText = respDoc.body?.textContent?.trim() || '';

        return {
            status: r2.status,
            hasEnrollment,
            hasProof,
            hasProblem,
            hasError,
            errors,
            bodyLen: text.length,
            bodyText: bodyText.replace(/\\s+/g, ' ').substring(0, 500),
            htmlPreview: text.substring(0, 800),
        };
    }''')

    print(f"\n=== Result ===")
    print(f"Status: {result.get('status')}")
    print(f"Has enrollment: {result.get('hasEnrollment')}")
    print(f"Has proof: {result.get('hasProof')}")
    print(f"Has problem: {result.get('hasProblem')}")
    print(f"Errors: {result.get('errors')}")
    print(f"Body text: {result.get('bodyText', '')[:400]}")
    print(f"\nHTML preview:\n{result.get('htmlPreview', '')[:600]}")

    browser.close()
print("\nDone!")
