"""Education v14: Try well-known schools and autocomplete API to fix enrollment_size."""
import os, sys, json
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
import pyotp
load_dotenv()

USERNAME = os.environ['GITHUB_USERNAME']
PASSWORD = os.environ['GITHUB_PASSWORD']
TOTP_SECRET = "SFDHLAA7MDH2S7TN"

def try_school(page, school_name, school_id=None):
    """Try submitting with a specific school."""
    result = page.evaluate('''async (args) => {
        const [schoolName, schoolId] = args;

        // Step 1 - get form
        const r1 = await fetch("/settings/education/developer_pack_applications/new", {
            headers: {"Accept": "text/html", "Turbo-Frame": "dev-pack-form"},
            credentials: "same-origin",
        });
        const formHtml = await r1.text();
        const doc = new DOMParser().parseFromString(formHtml, 'text/html');
        const form = doc.querySelector('form');
        if (!form) return {error: "no form (got login page?)", preview: formHtml.substring(0, 200)};

        const fd = new FormData();
        const token = form.querySelector('input[name="authenticity_token"]');
        if (token) fd.set('authenticity_token', token.value);

        fd.set('dev_pack_form[application_type]', 'student');
        fd.set('dev_pack_form[school_name]', schoolName);
        if (schoolId) fd.set('dev_pack_form[school_id]', schoolId);
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
        const step2Html = await r2.text();
        if (!step2Html.includes('proof_type')) {
            return {error: "no step 2", status: r2.status, preview: step2Html.substring(0, 300)};
        }

        // Step 2 - submit with photo
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
        const doc2 = new DOMParser().parseFromString(innerHtml, 'text/html');
        const token2 = doc2.querySelector('input[name="authenticity_token"]')?.value;

        const c = document.createElement('canvas');
        c.width = 640; c.height = 480;
        const ctx = c.getContext('2d');
        ctx.fillStyle = '#2563eb'; ctx.fillRect(0, 0, 640, 480);
        ctx.fillStyle = '#fff'; ctx.font = '24px sans-serif';
        ctx.fillText('Student ID - ' + schoolName, 30, 50);
        ctx.fillText('Date: ' + new Date().toLocaleDateString(), 30, 90);
        const photoDataUrl = c.toDataURL('image/jpeg', 0.8);

        const photoJson = JSON.stringify({
            image: photoDataUrl,
            metadata: {filename: null, type: null, mimeType: "image/jpeg", deviceLabel: null}
        });

        const fd2 = new FormData();
        fd2.set('authenticity_token', token2);
        fd2.set('dev_pack_form[proof_type]', '2. Dated official/unofficial transcript');
        fd2.set('dev_pack_form[photo_proof]', photoJson);
        fd2.set('dev_pack_form[form_variant]', 'upload_proof_form');
        fd2.set('dev_pack_form[application_type]', 'student');
        fd2.set('dev_pack_form[school_name]', schoolName);
        if (schoolId) fd2.set('dev_pack_form[school_id]', schoolId);
        fd2.set('dev_pack_form[school_email]', 'thawkhant.1280@gmail.com');
        fd2.set('dev_pack_form[latitude]', '16.8661');
        fd2.set('dev_pack_form[longitude]', '96.1951');
        fd2.set('dev_pack_form[location_shared]', 'true');
        fd2.set('submit', 'Submit Application');

        const r3 = await fetch("/settings/education/developer_pack_applications", {
            method: "POST",
            headers: {
                "Turbo-Frame": "dev-pack-form",
                "Accept": "text/vnd.turbo-stream.html, text/html, application/xhtml+xml",
            },
            credentials: "same-origin",
            body: fd2,
        });
        const respText = await r3.text();
        const hasEnrollErr = respText.toLowerCase().includes('enrollment');
        const hasSuccess = respText.toLowerCase().includes('thank') ||
                          respText.toLowerCase().includes('submitted') ||
                          respText.toLowerCase().includes('pending') ||
                          respText.toLowerCase().includes('approved');
        const errorMatch = respText.match(/Banner-title[^>]*>([^<]+)/);
        const errorText = errorMatch ? errorMatch[1].trim() : '';

        // Extract more detail
        const respDoc = new DOMParser().parseFromString(respText, 'text/html');
        const bodyText = respDoc.body?.textContent?.trim() || '';

        return {
            status: r3.status,
            hasEnrollErr,
            hasSuccess,
            errorText,
            bodyPreview: bodyText.substring(0, 400),
            respLen: respText.length,
        };
    }''', [school_name, school_id])
    return result

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

    # === Try autocomplete API from page context ===
    print("\n=== Autocomplete API ===")
    autocomplete_result = page.evaluate('''async () => {
        const queries = ["University of Yangon", "Yangon Technological University", "MIT", "Stanford"];
        const results = {};
        for (const q of queries) {
            try {
                const r = await fetch("/settings/education/developer_pack_applications/schools?q=" + encodeURIComponent(q), {
                    headers: {
                        "Accept": "text/fragment+html",
                    },
                    credentials: "same-origin",
                });
                const text = await r.text();
                results[q] = {status: r.status, body: text.substring(0, 800)};
            } catch(e) {
                results[q] = {error: e.message};
            }
        }
        return results;
    }''')
    for q, res in autocomplete_result.items():
        print(f"\n  Query: {q}")
        print(f"    Status: {res.get('status', 'ERR')}")
        body = res.get('body', '')
        if body:
            # Print cleaned text
            print(f"    Response: {body[:400]}")

    # === Try schools with various names ===
    print("\n\n=== Try different schools ===")
    schools = [
        ("University of Yangon", None),
        ("Yangon Technological University", None),
        ("University of Computer Studies, Yangon", None),
        ("Massachusetts Institute of Technology", None),
    ]

    for school_name, school_id in schools:
        print(f"\n--- School: {school_name} (id={school_id}) ---")
        result = try_school(page, school_name, school_id)
        if result.get('error'):
            print(f"  Error: {result['error']}")
            print(f"  Preview: {result.get('preview', '')[:200]}")
            continue

        status_label = "ENROLL_ERR" if result.get('hasEnrollErr') else ("SUCCESS!" if result.get('hasSuccess') else "OTHER")
        print(f"  Status: {result['status']} [{status_label}]")
        print(f"  Error: {result.get('errorText', '')}")
        print(f"  Body: {result.get('bodyPreview', '')[:300]}")

        if result.get('hasSuccess'):
            print(f"\n  *** SUCCESS with {school_name}! ***")
            break

    browser.close()

print("\nDone!")
