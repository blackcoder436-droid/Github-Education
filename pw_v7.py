"""Education flow v7: Send photo_proof as Blob/File in FormData (not text string).
Hypothesis: Server expects binary file upload for photo_proof, not a data URL string."""
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
    logged_in = "login" not in page.url
    print(f"  Logged in: {logged_in}")
    if not logged_in:
        browser.close(); sys.exit(1)

    # === Navigate to parent page ===
    page.goto("https://github.com/settings/education/benefits", timeout=120000, wait_until="load")
    page.wait_for_timeout(5000)

    # === STEP 1 ===
    print("\n=== Step 1 ===")
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
        const hasProof = html.includes('proof_type');
        return {status: r2.status, hasProof, body: html};
    }''')
    print(f"  Status: {step1_result.get('status')}, Proof: {step1_result.get('hasProof')}")
    if not step1_result.get('hasProof'):
        print("  Step 2 not reached!"); browser.close(); sys.exit(1)

    step2_html = step1_result["body"]

    # === STEP 2: Multiple approaches for photo_proof ===
    print("\n=== Step 2: Testing different photo_proof approaches ===")

    approaches = [
        # Approach 1: Blob as file upload (image/jpeg)
        {
            "name": "blob_jpeg_file",
            "desc": "Canvas -> toBlob(jpeg) -> FormData as File",
            "code": '''
                const c = document.createElement('canvas'); c.width=1280; c.height=720;
                const ctx = c.getContext('2d');
                const g = ctx.createLinearGradient(0,0,1280,720);
                g.addColorStop(0,'#1a365d'); g.addColorStop(0.5,'#2563eb'); g.addColorStop(1,'#f59e0b');
                ctx.fillStyle = g; ctx.fillRect(0,0,1280,720);
                ctx.fillStyle = '#fff'; ctx.font = 'bold 48px sans-serif';
                ctx.fillText('Student Enrollment Proof', 60, 100);
                ctx.font = '32px sans-serif';
                ctx.fillText('SKT International College', 60, 160);
                ctx.fillText('Date: ' + new Date().toLocaleDateString(), 60, 210);

                const blob = await new Promise(r => c.toBlob(r, 'image/jpeg', 0.9));
                const file = new File([blob], 'photo.jpg', {type: 'image/jpeg'});
                fd.set('dev_pack_form[photo_proof]', file, 'photo.jpg');
            '''
        },
        # Approach 2: Blob without filename
        {
            "name": "blob_jpeg_noname",
            "desc": "Canvas -> toBlob(jpeg) -> FormData as Blob (no filename)",
            "code": '''
                const c = document.createElement('canvas'); c.width=1280; c.height=720;
                const ctx = c.getContext('2d');
                ctx.fillStyle = '#2563eb'; ctx.fillRect(0,0,1280,720);
                ctx.fillStyle = '#fff'; ctx.font = 'bold 48px sans-serif';
                ctx.fillText('Student Proof', 60, 100);

                const blob = await new Promise(r => c.toBlob(r, 'image/jpeg', 0.9));
                fd.set('dev_pack_form[photo_proof]', blob);
            '''
        },
        # Approach 3: Data URL string (what we've been doing)
        {
            "name": "dataurl_string",
            "desc": "Canvas -> toDataURL -> set as string",
            "code": '''
                const c = document.createElement('canvas'); c.width=1280; c.height=720;
                const ctx = c.getContext('2d');
                ctx.fillStyle = '#2563eb'; ctx.fillRect(0,0,1280,720);
                ctx.fillStyle = '#fff'; ctx.font = 'bold 48px sans-serif';
                ctx.fillText('Student Proof', 60, 100);
                const dataUrl = c.toDataURL('image/jpeg', 0.9);
                fd.set('dev_pack_form[photo_proof]', dataUrl);
            '''
        },
        # Approach 4: base64 to Blob then File
        {
            "name": "base64_to_blob_file",
            "desc": "Canvas -> toDataURL -> decode base64 -> Blob -> File",
            "code": '''
                const c = document.createElement('canvas'); c.width=1280; c.height=720;
                const ctx = c.getContext('2d');
                ctx.fillStyle = '#2563eb'; ctx.fillRect(0,0,1280,720);
                ctx.fillStyle = '#fff'; ctx.font = 'bold 48px sans-serif';
                ctx.fillText('Student Proof', 60, 100);
                const dataUrl = c.toDataURL('image/jpeg', 0.9);
                const base64 = dataUrl.split(',')[1];
                const binary = atob(base64);
                const bytes = new Uint8Array(binary.length);
                for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
                const blob = new Blob([bytes], {type: 'image/jpeg'});
                const file = new File([blob], 'webcam-photo.jpg', {type: 'image/jpeg', lastModified: Date.now()});
                fd.set('dev_pack_form[photo_proof]', file, 'webcam-photo.jpg');
            '''
        },
    ]

    results = []
    for approach in approaches:
        print(f"\n  [{approach['name']}] {approach['desc']}")
        result = page.evaluate('''async (args) => {
            const [step2Html, photoCode] = args;
            const doc = new DOMParser().parseFromString(step2Html, 'text/html');
            const form = doc.querySelector('form');
            if (!form) return {error: "no form"};

            const fd = new FormData();
            const token = form.querySelector('input[name="authenticity_token"]');
            if (token) fd.set('authenticity_token', token.value);

            fd.set('dev_pack_form[proof_type]', '2. Dated official/unofficial transcript');
            fd.set('dev_pack_form[form_variant]', 'upload_proof_form');
            fd.set('dev_pack_form[application_type]', 'student');
            fd.set('dev_pack_form[school_name]', 'SKT International College');
            fd.set('dev_pack_form[school_email]', 'thawkhant.1280@gmail.com');
            fd.set('dev_pack_form[latitude]', '16.8661');
            fd.set('dev_pack_form[longitude]', '96.1951');
            fd.set('dev_pack_form[location_shared]', 'true');
            fd.set('dev_pack_form[browser_location]', '');
            fd.set('dev_pack_form[utm_source]', '');
            fd.set('dev_pack_form[utm_content]', '');
            fd.set('submit', 'Submit Application');

            // Execute the photo code (sets fd['dev_pack_form[photo_proof]'])
            const AsyncFunction = Object.getPrototypeOf(async function(){}).constructor;
            const fn = new AsyncFunction('fd', photoCode);
            await fn(fd);

            // Check what photo_proof is in FormData
            const photoVal = fd.get('dev_pack_form[photo_proof]');
            let photoInfo = {};
            if (photoVal instanceof Blob || photoVal instanceof File) {
                photoInfo = {
                    type: 'Blob/File',
                    size: photoVal.size,
                    mimeType: photoVal.type,
                    isFile: photoVal instanceof File,
                    fileName: photoVal instanceof File ? photoVal.name : null,
                };
            } else {
                photoInfo = {type: 'string', length: (photoVal || '').length, prefix: (photoVal || '').substring(0, 40)};
            }

            // Submit
            const r = await fetch("/settings/education/developer_pack_applications", {
                method: "POST",
                headers: {"Turbo-Frame": "dev-pack-form"},
                credentials: "same-origin",
                body: fd,
            });
            const respText = await r.text();

            // Parse response
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
            respDoc.querySelectorAll('.FormControl-inlineValidation--error span:last-child, p.color-fg-danger').forEach(e => {
                const t = e.textContent.trim();
                if (t) errors.push('inline: ' + t);
            });
            const checked = [];
            respDoc.querySelectorAll('[aria-checked="true"]').forEach(e => checked.push(e.textContent.trim().substring(0, 80)));

            const bodyText = respDoc.body?.textContent?.trim() || '';
            const success = bodyText.toLowerCase().includes('thank') || bodyText.toLowerCase().includes('submitted') || bodyText.toLowerCase().includes('pending');

            return {
                status: r.status,
                photoInfo,
                success,
                errors,
                checked,
                bodyLen: respText.length,
                textPreview: bodyText.substring(0, 300),
            };
        }''', [step2_html, approach["code"]])

        print(f"    Status: {result.get('status')}")
        print(f"    Photo info: {json.dumps(result.get('photoInfo', {}))}")
        print(f"    Success: {result.get('success')}")
        print(f"    Errors: {result.get('errors')}")
        print(f"    Checked: {result.get('checked')}")
        results.append({"name": approach["name"], **result})

    print("\n\n=== Summary ===")
    for r in results:
        status = "OK" if r.get('success') else "FAIL"
        print(f"  [{r['name']}] {status}: errors={r.get('errors')}, photo={json.dumps(r.get('photoInfo', {}))}")

    browser.close()

print("\nDone!")
