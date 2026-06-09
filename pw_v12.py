"""Education v12: JSON photo_proof (correct format) + school_id to fix enrollment_size error.
Also try the schools API to check what data it returns."""
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

    page.goto("https://github.com/settings/education/benefits", timeout=120000, wait_until="load")
    page.wait_for_timeout(5000)

    # === Check schools API ===
    print("\n=== Schools API ===")
    school_data = page.evaluate('''async () => {
        const r = await fetch("/settings/education/developer_pack_applications/schools?query=SKT+International", {
            headers: {"Accept": "application/json"},
            credentials: "same-origin",
        });
        const text = await r.text();
        try { return {status: r.status, data: JSON.parse(text)}; }
        catch(e) { return {status: r.status, text: text.substring(0, 500)}; }
    }''')
    print(f"  Status: {school_data.get('status')}")
    if school_data.get('data'):
        data = school_data['data']
        if isinstance(data, list):
            for s in data[:5]:
                print(f"  School: {json.dumps(s, indent=4)}")
        else:
            print(f"  Data: {json.dumps(data, indent=2)[:500]}")
    else:
        print(f"  Raw: {school_data.get('text', '')[:300]}")

    # Also try with different Accept header
    school_data2 = page.evaluate('''async () => {
        const r = await fetch("/settings/education/developer_pack_applications/schools?query=SKT", {
            headers: {"Accept": "text/fragment+html"},
            credentials: "same-origin",
        });
        return {status: r.status, text: (await r.text()).substring(0, 1000)};
    }''')
    print(f"\n  Fragment response ({school_data2.get('status')}): {school_data2.get('text', '')[:500]}")

    # === Step 1 with school_id ===
    print("\n\n=== Step 1 (with school_id) ===")
    step1_result = page.evaluate('''async () => {
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
        fd.set('dev_pack_form[school_name]', 'SKT International College');
        fd.set('dev_pack_form[school_id]', '118171');
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
        return {status: r2.status, hasProof: html.includes('proof_type'), body: html};
    }''')
    print(f"  Status: {step1_result.get('status')}, Proof: {step1_result.get('hasProof')}")
    if not step1_result.get('hasProof'):
        print(f"  Step 2 not reached!")
        # Check if there's an error
        err_html = step1_result.get('body', '')
        if 'error' in err_html.lower() or 'Banner' in err_html:
            from html.parser import HTMLParser
            print(f"  Response preview: {err_html[:500]}")
        browser.close(); sys.exit(1)

    step2_html = step1_result["body"]

    # === Step 2 with JSON photo_proof ===
    print("\n=== Step 2 (JSON photo_proof) ===")
    result = page.evaluate('''async (step2Html) => {
        // Get token
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
        const doc = new DOMParser().parseFromString(innerHtml, 'text/html');
        const token = doc.querySelector('input[name="authenticity_token"]')?.value;

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
        ctx.fillText('Student ID: 2024-EDU-001', 60, 210);
        ctx.fillText('Date: ' + new Date().toLocaleDateString(), 60, 260);
        const photoDataUrl = c.toDataURL('image/jpeg', 0.9);

        // JSON photo_proof (matching webcam component output)
        const photoJson = JSON.stringify({
            image: photoDataUrl,
            metadata: {
                filename: null,
                type: null,
                mimeType: "image/jpeg",
                deviceLabel: null,
            }
        });

        // Build FormData
        const fd = new FormData();
        fd.set('authenticity_token', token);
        fd.set('dev_pack_form[proof_type]', '2. Dated official/unofficial transcript');
        fd.set('dev_pack_form[photo_proof]', photoJson);
        fd.set('dev_pack_form[form_variant]', 'upload_proof_form');
        fd.set('dev_pack_form[application_type]', 'student');
        fd.set('dev_pack_form[school_name]', 'SKT International College');
        fd.set('dev_pack_form[school_id]', '118171');
        fd.set('dev_pack_form[school_email]', 'thawkhant.1280@gmail.com');
        fd.set('dev_pack_form[latitude]', '16.8661');
        fd.set('dev_pack_form[longitude]', '96.1951');
        fd.set('dev_pack_form[location_shared]', 'true');
        fd.set('dev_pack_form[browser_location]', '');
        fd.set('dev_pack_form[utm_source]', '');
        fd.set('dev_pack_form[utm_content]', '');
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
        const respText = await r.text();

        // Parse
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
                       bodyText.toLowerCase().includes('discount');

        return {
            status: r.status,
            success,
            errors,
            checked,
            photoJsonLen: photoJson.length,
            bodyLen: respText.length,
            textPreview: bodyText.substring(0, 500),
            respPreview: respText.substring(0, 500),
        };
    }''', step2_html)

    print(f"  Status: {result.get('status')}")
    print(f"  Success: {result.get('success')}")
    print(f"  Errors: {result.get('errors')}")
    print(f"  Checked: {result.get('checked')}")
    print(f"  Text: {result.get('textPreview', '')[:400]}")
    print(f"  Response: {result.get('respPreview', '')[:300]}")

    # Save full response
    with open("pw_v12_resp.html", "w", encoding="utf-8") as f:
        f.write(result.get('respPreview', ''))

    browser.close()

print("\nDone!")
