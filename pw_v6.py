"""v6: Try URLSearchParams (url-encoded) instead of FormData (multipart).
Also try variations of photo_proof format."""
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
    )
    page = context.new_page()

    # Login
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
    if "login" in page.url:
        browser.close(); sys.exit(1)

    page.goto("https://github.com/settings/education/benefits", timeout=120000, wait_until="load")
    page.wait_for_timeout(5000)

    # Step 1
    print("\n=== Step 1 ===")
    step1 = page.evaluate('''async () => {
        const r1 = await fetch("/settings/education/developer_pack_applications/new", {
            headers: {"Accept": "text/html", "Turbo-Frame": "dev-pack-form"},
            credentials: "same-origin",
        });
        const html = await r1.text();
        const doc = new DOMParser().parseFromString(html, 'text/html');
        const form = doc.querySelector('form');
        if (!form) return {error: "no form"};
        const token = form.querySelector('input[name="authenticity_token"]')?.value;

        // Send as url-encoded (matching Turbo default)
        const params = new URLSearchParams();
        params.set('authenticity_token', token);
        params.set('dev_pack_form[application_type]', 'student');
        params.set('dev_pack_form[school_name]', 'SKT International College');
        params.set('dev_pack_form[school_email]', 'thawkhant.1280@gmail.com');
        params.set('dev_pack_form[latitude]', '16.8661');
        params.set('dev_pack_form[longitude]', '96.1951');
        params.set('dev_pack_form[location_shared]', 'true');
        params.set('dev_pack_form[form_variant]', 'initial_form');
        params.set('dev_pack_form[browser_location]', '');
        params.set('dev_pack_form[utm_source]', '');
        params.set('dev_pack_form[utm_content]', '');
        params.set('continue', 'Continue');

        const r2 = await fetch("/settings/education/developer_pack_applications", {
            method: "POST",
            headers: {
                "Content-Type": "application/x-www-form-urlencoded",
                "Turbo-Frame": "dev-pack-form",
            },
            credentials: "same-origin",
            body: params.toString(),
        });
        const respHtml = await r2.text();
        const doc2 = new DOMParser().parseFromString(respHtml, 'text/html');
        const hasProof = !!doc2.querySelector('input[name="dev_pack_form[proof_type]"]');
        return {status: r2.status, len: respHtml.length, hasProof, body: respHtml};
    }''')
    print(f"  Status: {step1.get('status')}, Proof: {step1.get('hasProof')}")

    if not step1.get('hasProof'):
        print("  Step 2 not reached!")
        with open("pw_v6_step1.html", "w", encoding="utf-8") as f:
            f.write(step1.get("body", ""))
        browser.close(); sys.exit(1)

    # Step 2: try url-encoded with photo proof
    print("\n=== Step 2: URLSearchParams ===")
    step2 = page.evaluate('''async (step2Html) => {
        const doc = new DOMParser().parseFromString(step2Html, 'text/html');
        const form = doc.querySelector('form');
        const token = form.querySelector('input[name="authenticity_token"]')?.value;

        // Generate photo
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
        ctx.fillText('Date: ' + new Date().toLocaleDateString(), 60, 210);
        const photoJpeg = c.toDataURL('image/jpeg', 0.9);
        const photoPng = c.toDataURL('image/png');

        const results = {};

        // Try 1: JPEG data URL, url-encoded
        const params1 = new URLSearchParams();
        params1.set('authenticity_token', token);
        params1.set('dev_pack_form[proof_type]', '2. Dated official/unofficial transcript');
        params1.set('dev_pack_form[photo_proof]', photoJpeg);
        params1.set('dev_pack_form[form_variant]', 'upload_proof_form');
        params1.set('dev_pack_form[application_type]', 'student');
        params1.set('dev_pack_form[school_name]', 'SKT International College');
        params1.set('dev_pack_form[school_email]', 'thawkhant.1280@gmail.com');
        params1.set('dev_pack_form[latitude]', '16.8661');
        params1.set('dev_pack_form[longitude]', '96.1951');
        params1.set('dev_pack_form[location_shared]', 'true');
        params1.set('dev_pack_form[browser_location]', '');
        params1.set('dev_pack_form[utm_source]', '');
        params1.set('dev_pack_form[utm_content]', '');
        params1.set('submit', 'Submit Application');

        const r1 = await fetch("/settings/education/developer_pack_applications", {
            method: "POST",
            headers: {
                "Content-Type": "application/x-www-form-urlencoded",
                "Turbo-Frame": "dev-pack-form",
            },
            credentials: "same-origin",
            body: params1.toString(),
        });
        const resp1 = await r1.text();

        // Parse response (handle turbo-stream)
        function parseResp(html) {
            let d;
            if (html.includes('<turbo-stream')) {
                const tmpDoc = new DOMParser().parseFromString(html, 'text/html');
                const tmpl = tmpDoc.querySelector('template');
                if (tmpl) {
                    const container = document.createElement('div');
                    container.appendChild(tmpl.content.cloneNode(true));
                    d = new DOMParser().parseFromString(container.innerHTML, 'text/html');
                } else {
                    d = tmpDoc;
                }
            } else {
                d = new DOMParser().parseFromString(html, 'text/html');
            }
            const errors = [];
            d.querySelectorAll('.Banner-title, [data-target="x-banner.titleText"]').forEach(e => errors.push(e.textContent.trim()));
            // Check inline errors near photo_proof
            d.querySelectorAll('.color-fg-danger').forEach(e => {
                const text = e.textContent.trim();
                if (text && text.includes('required')) errors.push('inline: ' + text);
            });
            const checked = [];
            d.querySelectorAll('[aria-checked="true"]').forEach(e => checked.push(e.textContent.trim().substring(0, 50)));
            const success = d.body.textContent.toLowerCase().includes('thank') ||
                           d.body.textContent.toLowerCase().includes('pending') ||
                           d.body.textContent.toLowerCase().includes('submitted');
            // Check if photo_proof has a value in response
            const ppVal = d.querySelector('#photo_proof, input[name="dev_pack_form[photo_proof]"]')?.value || '';
            return {errors, checked, success, ppValLen: ppVal.length};
        }

        const analysis1 = parseResp(resp1);
        results['urlencoded_jpeg'] = {
            status: r1.status,
            len: resp1.length,
            photoLen: photoJpeg.length,
            bodySize: params1.toString().length,
            ...analysis1,
        };

        // If first attempt failed, get new token from response and try PNG
        if (!analysis1.success) {
            const doc3 = new DOMParser().parseFromString(resp1, 'text/html');
            let newToken = doc3.querySelector('input[name="authenticity_token"]')?.value;
            if (!newToken) {
                // Check turbo-stream
                const tmpDoc = new DOMParser().parseFromString(resp1, 'text/html');
                const tmpl = tmpDoc.querySelector('template');
                if (tmpl) {
                    const container = document.createElement('div');
                    container.appendChild(tmpl.content.cloneNode(true));
                    const innerDoc = new DOMParser().parseFromString(container.innerHTML, 'text/html');
                    newToken = innerDoc.querySelector('input[name="authenticity_token"]')?.value;
                }
            }

            if (newToken) {
                // Try 2: PNG data URL, url-encoded
                const params2 = new URLSearchParams();
                params2.set('authenticity_token', newToken);
                params2.set('dev_pack_form[proof_type]', '2. Dated official/unofficial transcript');
                params2.set('dev_pack_form[photo_proof]', photoPng);
                params2.set('dev_pack_form[form_variant]', 'upload_proof_form');
                params2.set('dev_pack_form[application_type]', 'student');
                params2.set('dev_pack_form[school_name]', 'SKT International College');
                params2.set('dev_pack_form[school_email]', 'thawkhant.1280@gmail.com');
                params2.set('dev_pack_form[latitude]', '16.8661');
                params2.set('dev_pack_form[longitude]', '96.1951');
                params2.set('dev_pack_form[location_shared]', 'true');
                params2.set('dev_pack_form[browser_location]', '');
                params2.set('dev_pack_form[utm_source]', '');
                params2.set('dev_pack_form[utm_content]', '');
                params2.set('submit', 'Submit Application');

                const r2 = await fetch("/settings/education/developer_pack_applications", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/x-www-form-urlencoded",
                        "Turbo-Frame": "dev-pack-form",
                    },
                    credentials: "same-origin",
                    body: params2.toString(),
                });
                const resp2 = await r2.text();
                results['urlencoded_png'] = {
                    status: r2.status,
                    len: resp2.length,
                    photoLen: photoPng.length,
                    bodySize: params2.toString().length,
                    ...parseResp(resp2),
                };

                // Try 3: Send with just raw base64 (no data: prefix)
                const doc4 = (() => {
                    const tmpDoc2 = new DOMParser().parseFromString(resp2, 'text/html');
                    const tmpl2 = tmpDoc2.querySelector('template');
                    if (tmpl2) {
                        const c2 = document.createElement('div');
                        c2.appendChild(tmpl2.content.cloneNode(true));
                        return new DOMParser().parseFromString(c2.innerHTML, 'text/html');
                    }
                    return tmpDoc2;
                })();
                const newToken2 = doc4.querySelector('input[name="authenticity_token"]')?.value;

                if (newToken2) {
                    const rawBase64 = photoJpeg.replace('data:image/jpeg;base64,', '');
                    const params3 = new URLSearchParams();
                    params3.set('authenticity_token', newToken2);
                    params3.set('dev_pack_form[proof_type]', '2. Dated official/unofficial transcript');
                    params3.set('dev_pack_form[photo_proof]', rawBase64);
                    params3.set('dev_pack_form[form_variant]', 'upload_proof_form');
                    params3.set('dev_pack_form[application_type]', 'student');
                    params3.set('dev_pack_form[school_name]', 'SKT International College');
                    params3.set('dev_pack_form[school_email]', 'thawkhant.1280@gmail.com');
                    params3.set('dev_pack_form[latitude]', '16.8661');
                    params3.set('dev_pack_form[longitude]', '96.1951');
                    params3.set('dev_pack_form[location_shared]', 'true');
                    params3.set('dev_pack_form[browser_location]', '');
                    params3.set('dev_pack_form[utm_source]', '');
                    params3.set('dev_pack_form[utm_content]', '');
                    params3.set('submit', 'Submit Application');

                    const r3 = await fetch("/settings/education/developer_pack_applications", {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/x-www-form-urlencoded",
                            "Turbo-Frame": "dev-pack-form",
                        },
                        credentials: "same-origin",
                        body: params3.toString(),
                    });
                    const resp3 = await r3.text();
                    results['urlencoded_rawbase64'] = {
                        status: r3.status,
                        len: resp3.length,
                        photoLen: rawBase64.length,
                        ...parseResp(resp3),
                    };
                }
            }
        }

        return results;
    }''', step1["body"])

    print(f"\nResults:")
    for name, result in step2.items():
        print(f"\n  [{name}]")
        print(f"    Status: {result.get('status')}")
        print(f"    Photo len: {result.get('photoLen')}")
        print(f"    Body size: {result.get('bodySize', '?')}")
        print(f"    Success: {result.get('success')}")
        print(f"    Errors: {result.get('errors')}")
        print(f"    Checked: {result.get('checked')}")

    browser.close()
print("\nDone!")
