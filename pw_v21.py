"""Education v21: Test various enrollment_size values in step 2 submission.
Focus on finding the right enrollment_size value format."""
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

    # === Step 1 ===
    print("\n=== Step 1 ===")
    step1 = page.evaluate('''async () => {
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
        fd.set('dev_pack_form[school_name]', 'University of Computer Studies, Yangon');
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
        const html = await r2.text();
        return {status: r2.status, hasProof: html.includes('proof_type'), html};
    }''')
    print(f"  Status: {step1.get('status')}, HasProof: {step1.get('hasProof')}")
    if not step1.get('hasProof'):
        print(f"  FAILED to reach step 2")
        browser.close()
        sys.exit(1)

    step2_html = step1['html']

    # Get token from step 2
    token_result = page.evaluate('''(html) => {
        let inner = html;
        if (html.includes('<turbo-stream')) {
            const doc = new DOMParser().parseFromString(html, 'text/html');
            const tmpl = doc.querySelector('template');
            if (tmpl) {
                const c = document.createElement('div');
                c.appendChild(tmpl.content.cloneNode(true));
                inner = c.innerHTML;
            }
        }
        const doc = new DOMParser().parseFromString(inner, 'text/html');
        return doc.querySelector('input[name="authenticity_token"]')?.value || '';
    }''', step2_html)

    # === Test enrollment_size values ===
    print("\n=== Testing enrollment_size values ===")

    # Common Rails enum patterns for school enrollment sizes
    enrollment_values = [
        # Numeric ranges
        "1_000", "5_000", "10_000", "20_000", "50_000",
        "1000", "5000", "10000", "20000", "50000",
        # String descriptions
        "small", "medium", "large", "very_large",
        # Range descriptions
        "under_1000", "1000_to_4999", "5000_to_9999", "10000_to_19999", "20000_plus",
        "1-999", "1000-4999", "5000-9999", "10000-19999", "20000+",
        # GitHub-style
        "fewer_than_1000", "1000_to_5000", "5000_to_10000", "10000_to_20000", "more_than_20000",
        # Just numbers
        "100", "500", "1000", "2000", "5000", "10000", "25000",
    ]

    for ev in enrollment_values:
        result = page.evaluate('''async (args) => {
            const [token, enrollVal] = args;

            const c = document.createElement('canvas');
            c.width = 320; c.height = 240;
            const ctx = c.getContext('2d');
            ctx.fillStyle = '#2563eb'; ctx.fillRect(0, 0, 320, 240);
            const photoJson = JSON.stringify({
                image: c.toDataURL('image/jpeg', 0.5),
                metadata: {filename: null, type: null, mimeType: "image/jpeg", deviceLabel: null}
            });

            const fd = new FormData();
            fd.set('authenticity_token', token);
            fd.set('dev_pack_form[proof_type]', '2. Dated official/unofficial transcript');
            fd.set('dev_pack_form[photo_proof]', photoJson);
            fd.set('dev_pack_form[form_variant]', 'upload_proof_form');
            fd.set('dev_pack_form[application_type]', 'student');
            fd.set('dev_pack_form[school_name]', 'University of Computer Studies, Yangon');
            fd.set('dev_pack_form[school_email]', 'thawkhant.1280@gmail.com');
            fd.set('dev_pack_form[latitude]', '16.8661');
            fd.set('dev_pack_form[longitude]', '96.1951');
            fd.set('dev_pack_form[location_shared]', 'true');
            fd.set('dev_pack_form[enrollment_size]', enrollVal);
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
            const text = await r.text();
            const hasEnroll = text.toLowerCase().includes('enrollment');
            const hasSuccess = text.toLowerCase().includes('thank') ||
                              text.toLowerCase().includes('submitted') ||
                              text.toLowerCase().includes('pending');

            // Get new token for next iteration
            let inner = text;
            if (text.includes('<turbo-stream')) {
                const doc = new DOMParser().parseFromString(text, 'text/html');
                const tmpl = doc.querySelector('template');
                if (tmpl) {
                    const c2 = document.createElement('div');
                    c2.appendChild(tmpl.content.cloneNode(true));
                    inner = c2.innerHTML;
                }
            }
            const doc = new DOMParser().parseFromString(inner, 'text/html');
            const newToken = doc.querySelector('input[name="authenticity_token"]')?.value || '';

            // Extract full error
            let error = '';
            doc.querySelectorAll('.Banner-title, [data-target="x-banner.titleText"]').forEach(e => error += e.textContent.trim());

            return {enrollVal, status: r.status, hasEnroll, hasSuccess, error: error.substring(0, 200), newToken};
        }''', [token_result, ev])

        label = "ENROLL" if result.get('hasEnroll') else ("OK!" if result.get('hasSuccess') else "DIFF")
        err = result.get('error', '')[:100]
        print(f"  {ev}: [{label}] {err}")

        # Update token for next iteration
        if result.get('newToken'):
            token_result = result['newToken']

        if result.get('hasSuccess') or not result.get('hasEnroll'):
            print(f"\n  *** DIFFERENT RESULT with enrollment_size={ev}! ***")
            print(f"  Full: {json.dumps(result, indent=2)[:300]}")
            break

    browser.close()

print("\nDone!")
