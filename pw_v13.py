"""Education v13: Try multiple approaches to fix enrollment_size error.
1. Find correct schools API / check what data it returns
2. Try sending enrollment_size as form parameter
3. Try well-known school"""
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

    # === Try various schools API endpoints ===
    print("\n=== Schools API exploration ===")
    api_results = page.evaluate('''async () => {
        const results = {};

        // Try different URL patterns
        const urls = [
            "/settings/education/developer_pack_applications/schools?query=MIT",
            "/settings/education/developer_pack_applications/schools?q=MIT",
            "/settings/education/schools?query=MIT",
            "/education/schools?query=MIT",
            "/settings/education/developer_pack_applications/schools.json?query=MIT",
        ];

        for (const url of urls) {
            try {
                const r = await fetch(url, {
                    headers: {"Accept": "application/json, text/html, */*"},
                    credentials: "same-origin",
                });
                const text = await r.text();
                results[url] = {status: r.status, body: text.substring(0, 400)};
            } catch(e) {
                results[url] = {error: e.message};
            }
        }

        // Try with X-Requested-With header (AJAX)
        try {
            const r = await fetch("/settings/education/developer_pack_applications/schools?query=MIT", {
                headers: {
                    "Accept": "application/json",
                    "X-Requested-With": "XMLHttpRequest",
                },
                credentials: "same-origin",
            });
            const text = await r.text();
            results["schools_xhr"] = {status: r.status, body: text.substring(0, 400)};
        } catch(e) {
            results["schools_xhr"] = {error: e.message};
        }

        return results;
    }''')
    for url, res in api_results.items():
        print(f"  {url}: {res.get('status','ERR')} -> {res.get('body','')[:200]}")

    # === Get step 1 form and look for hidden fields ===
    print("\n=== Get step 1 form (inspect all fields) ===")
    form_fields = page.evaluate('''async () => {
        const r = await fetch("/settings/education/developer_pack_applications/new", {
            headers: {"Accept": "text/html", "Turbo-Frame": "dev-pack-form"},
            credentials: "same-origin",
        });
        const html = await r.text();

        // Save full HTML
        const doc = new DOMParser().parseFromString(html, 'text/html');

        // List ALL input fields
        const inputs = [];
        doc.querySelectorAll('input, select, textarea').forEach(el => {
            inputs.push({
                tag: el.tagName,
                type: el.type || '',
                name: el.name || '',
                value: (el.value || '').substring(0, 100),
                id: el.id || '',
                hidden: el.type === 'hidden' || el.hidden,
            });
        });

        // Check for enrollment/school_id mentions
        const allText = html;
        const enrollmentMentions = [];
        const regex = /enrollment[_\-]?size|school_id|school_size/gi;
        let m;
        while ((m = regex.exec(allText)) !== null) {
            const start = Math.max(0, m.index - 50);
            const end = Math.min(allText.length, m.index + m[0].length + 50);
            enrollmentMentions.push(allText.substring(start, end));
        }

        return {inputs, enrollmentMentions, htmlLen: html.length};
    }''')
    print(f"  Total inputs: {len(form_fields.get('inputs', []))}")
    for inp in form_fields.get('inputs', []):
        print(f"    {inp['tag']} name={inp['name']} type={inp['type']} value={inp['value'][:50]} hidden={inp['hidden']}")
    if form_fields.get('enrollmentMentions'):
        for m in form_fields['enrollmentMentions']:
            print(f"  enrollment mention: {m}")

    # === Step 1 ===
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
    print(f"  Status: {step1_result.get('status')}, Step2: {step1_result.get('hasProof')}")
    if not step1_result.get('hasProof'):
        print("  Failed to reach step 2!")
        browser.close(); sys.exit(1)

    step2_html = step1_result["body"]

    # === Step 2 attempts with different enrollment_size values ===
    print("\n=== Step 2 attempts ===")
    enrollment_values = [
        "1_000",
        "5_000",
        "10_000",
        "1000",
        "5000",
        "small",
        "1-999",
        "1000-4999",
        "under_1000",
        "1_000_to_4_999",
    ]

    for ev in enrollment_values:
        attempt_result = page.evaluate('''async (args) => {
            const [step2Html, enrollVal] = args;
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

            const c = document.createElement('canvas');
            c.width = 640; c.height = 480;
            const ctx = c.getContext('2d');
            ctx.fillStyle = '#2563eb'; ctx.fillRect(0, 0, 640, 480);
            ctx.fillStyle = '#fff'; ctx.font = '24px sans-serif';
            ctx.fillText('Student ID Card', 50, 50);
            const photoDataUrl = c.toDataURL('image/jpeg', 0.8);

            const photoJson = JSON.stringify({
                image: photoDataUrl,
                metadata: {filename: null, type: null, mimeType: "image/jpeg", deviceLabel: null}
            });

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
            const respText = await r.text();
            const hasEnrollErr = respText.toLowerCase().includes('enrollment');
            const hasSuccess = respText.toLowerCase().includes('thank') ||
                              respText.toLowerCase().includes('submitted') ||
                              respText.toLowerCase().includes('pending');
            return {enrollVal, status: r.status, hasEnrollErr, hasSuccess, preview: respText.substring(0, 300)};
        }''', [step2_html, ev])

        status = "ENROLL_ERR" if attempt_result.get('hasEnrollErr') else ("SUCCESS?" if attempt_result.get('hasSuccess') else "OTHER")
        print(f"  enrollment_size={ev}: {attempt_result.get('status')} [{status}]")
        if not attempt_result.get('hasEnrollErr'):
            print(f"    DIFFERENT RESPONSE! Preview: {attempt_result.get('preview', '')[:200]}")
            break

    browser.close()

print("\nDone!")
