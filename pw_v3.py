"""Education flow: Playwright login + fetch()-based form submission.
No turbo-frame or custom element hydration needed."""
import os, sys, json, time
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
                print("  2FA...")
                otp = pyotp.TOTP(TOTP_SECRET).now()
                for sel in ['#app_totp', 'input[name="app_otp"]', 'input[name="otp"]']:
                    f = page.query_selector(sel)
                    if f:
                        f.fill(otp)
                        break
                page.wait_for_timeout(500)
                try:
                    page.click('button[type="submit"]', timeout=5000)
                except Exception:
                    pass
                page.wait_for_load_state("load", timeout=30000)
                page.wait_for_timeout(3000)
    logged_in = "login" not in page.url
    print(f"  Logged in: {logged_in} ({page.url})")
    if not logged_in:
        print("  FAILED!")
        browser.close()
        sys.exit(1)

    # === Navigate to parent page (for full JS env + cookies) ===
    print("\n=== Navigate to /settings/education/benefits ===")
    page.goto("https://github.com/settings/education/benefits", timeout=120000, wait_until="load")
    page.wait_for_timeout(5000)
    print(f"  Page loaded: {page.url}")

    # === STEP 1: Fetch form, extract token, POST ===
    print("\n=== Step 1: Fetch form ===")
    form_html = page.evaluate('''async () => {
        const r = await fetch("/settings/education/developer_pack_applications/new", {
            headers: {"Accept": "text/html", "Turbo-Frame": "dev-pack-form"},
            credentials: "same-origin",
        });
        return await r.text();
    }''')
    print(f"  Form HTML length: {len(form_html)}")

    # Parse form data from HTML - extract token and select values
    form_data = page.evaluate('''(html) => {
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');
        const form = doc.querySelector('form');
        if (!form) return {error: "no form in HTML"};
        const data = {};
        form.querySelectorAll('input[name]').forEach(i => {
            if (i.type === 'radio' && !i.checked) return;
            // Skip duplicate school_name if already set
            if (data[i.name] && i.name.includes('school_name')) return;
            data[i.name] = i.value || '';
        });
        // Get select values
        form.querySelectorAll('select[name]').forEach(s => {
            data[s.name] = s.value || '';
        });
        return {action: form.action, data: data};
    }''', form_html)
    print(f"  Form action: {form_data.get('action', 'MISSING')}")
    print(f"  Fields: {list(form_data.get('data', {}).keys())}")

    # Set step 1 fields
    step1_data = form_data.get("data", {})
    step1_data["dev_pack_form[application_type]"] = "student"
    step1_data["dev_pack_form[school_name]"] = "SKT International College"
    step1_data["dev_pack_form[school_email]"] = "thawkhant.1280@gmail.com"
    step1_data["dev_pack_form[form_variant]"] = "initial_form"
    step1_data["continue"] = "Continue"
    # Remove submit if present
    step1_data.pop("submit", None)

    # Location
    step1_data["dev_pack_form[latitude]"] = "16.8661"
    step1_data["dev_pack_form[longitude]"] = "96.1951"
    step1_data["dev_pack_form[location_shared]"] = "true"

    print(f"\n  Step 1 POST data:")
    for k, v in step1_data.items():
        if "token" not in k.lower():
            print(f"    {k} = {v!r}")

    # Submit step 1 via fetch
    print("\n=== Step 1: Submit ===")
    step1_result = page.evaluate('''async (formData) => {
        const body = new URLSearchParams(formData).toString();
        const r = await fetch("/settings/education/developer_pack_applications", {
            method: "POST",
            headers: {
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "text/html",
                "Turbo-Frame": "dev-pack-form",
            },
            credentials: "same-origin",
            body: body,
        });
        const text = await r.text();
        return {status: r.status, url: r.url, bodyLen: text.length, body: text};
    }''', step1_data)
    print(f"  Status: {step1_result['status']}")
    print(f"  Response length: {step1_result['bodyLen']}")

    resp_html = step1_result["body"]

    # Check for errors
    error_check = page.evaluate('''(html) => {
        const doc = new DOMParser().parseFromString(html, 'text/html');
        const banner = doc.querySelector('.Banner-title, .flash-error, [data-target="x-banner.titleText"]');
        return banner ? banner.textContent.trim() : null;
    }''', resp_html)
    if error_check:
        print(f"  Error banner: {error_check}")

    # Check what we got back
    resp_analysis = page.evaluate('''(html) => {
        const doc = new DOMParser().parseFromString(html, 'text/html');
        const form = doc.querySelector('form');
        if (!form) return {hasForm: false, preview: html.substring(0, 500)};
        const inputs = {};
        form.querySelectorAll('input[name]').forEach(i => {
            if (i.type !== 'radio' || i.checked) inputs[i.name] = i.value?.substring(0, 100) || '';
        });
        const hasProofType = !!form.querySelector('input[name="dev_pack_form[proof_type]"]');
        const hasPhotoProof = !!form.querySelector('#photo_proof, input[name="dev_pack_form[photo_proof]"]');
        const hasSubmit = !!form.querySelector('button[name="submit"]');
        const hasContinue = !!form.querySelector('button[name="continue"]');
        const variant = form.querySelector('input[name="dev_pack_form[form_variant]"]')?.value;
        // Check for school info questions
        const labels = Array.from(form.querySelectorAll('label')).map(l => l.textContent.trim()).filter(t => t.length > 5);
        return {hasForm: true, hasProofType, hasPhotoProof, hasSubmit, hasContinue, variant, inputNames: Object.keys(inputs), labels: labels.slice(0, 10)};
    }''', resp_html)
    print(f"\n  Response analysis:")
    print(f"    Has form: {resp_analysis.get('hasForm')}")
    print(f"    Has proof_type: {resp_analysis.get('hasProofType')}")
    print(f"    Has photo_proof: {resp_analysis.get('hasPhotoProof')}")
    print(f"    Has submit: {resp_analysis.get('hasSubmit')}")
    print(f"    Has continue: {resp_analysis.get('hasContinue')}")
    print(f"    Variant: {resp_analysis.get('variant')}")
    print(f"    Labels: {resp_analysis.get('labels')}")

    # === IF STEP 2 (has proof_type) ===
    if resp_analysis.get("hasProofType"):
        print("\n=== Step 2: Analyze proof options ===")

        # First, inspect the proof_type field and action-menu items
        proof_info = page.evaluate('''(html) => {
            const doc = new DOMParser().parseFromString(html, 'text/html');
            const form = doc.querySelector('form');
            // Get proof_type input details
            const ptInput = form.querySelector('input[name="dev_pack_form[proof_type]"]');
            const ptInfo = ptInput ? {
                type: ptInput.type,
                value: ptInput.value,
                id: ptInput.id,
            } : null;
            // Get action-menu items
            const menuItems = Array.from(form.querySelectorAll('[role="menuitemradio"], [data-value]')).map(i => ({
                text: i.textContent.trim().substring(0, 100),
                value: i.dataset?.value || i.getAttribute('data-value') || '',
                ariaChecked: i.getAttribute('aria-checked'),
                tagName: i.tagName,
            }));
            // Get all option-like elements
            const actionList = form.querySelector('action-list, [data-action-list-target]');
            const listItems = actionList ?
                Array.from(actionList.querySelectorAll('[role="option"], [role="menuitemradio"], li')).map(i => ({
                    text: i.textContent.trim().substring(0, 100),
                    value: i.dataset?.value || '',
                })) : [];
            // Check for select element
            const selects = Array.from(form.querySelectorAll('select')).map(s => ({
                name: s.name,
                options: Array.from(s.options).map(o => ({value: o.value, text: o.textContent.trim()})),
            }));
            // Also get the action-menu raw HTML
            const am = form.querySelector('action-menu');
            return {
                ptInput: ptInfo,
                menuItems,
                listItems,
                selects,
                actionMenuHTML: am ? am.outerHTML.substring(0, 2000) : 'NO ACTION-MENU',
            };
        }''', resp_html)

        print(f"  proof_type input: {proof_info.get('ptInput')}")
        print(f"  Menu items ({len(proof_info.get('menuItems', []))}):")
        for item in proof_info.get('menuItems', []):
            print(f"    text={item['text']!r}, value={item['value']!r}, checked={item['ariaChecked']}")
        print(f"  List items ({len(proof_info.get('listItems', []))}):")
        for item in proof_info.get('listItems', []):
            print(f"    text={item['text']!r}, value={item['value']!r}")
        print(f"  Selects ({len(proof_info.get('selects', []))}):")
        for s in proof_info.get('selects', []):
            print(f"    {s['name']}: {[o['text'] for o in s['options']]}")
        print(f"\n  action-menu HTML:\n{proof_info.get('actionMenuHTML', '')}")

        print("\n=== Step 2: Fill proof and submit ===")

        # Extract step 2 form data
        step2_data = page.evaluate('''(html) => {
            const doc = new DOMParser().parseFromString(html, 'text/html');
            const form = doc.querySelector('form');
            const data = {};
            form.querySelectorAll('input[name]').forEach(i => {
                if (i.type === 'radio' && !i.checked) return;
                if (!data[i.name]) data[i.name] = i.value || '';
            });
            return data;
        }''', resp_html)

        # Set proof fields
        step2_data["dev_pack_form[proof_type]"] = "2. Dated official/unofficial transcript"
        step2_data["dev_pack_form[form_variant]"] = "upload_proof_form"
        step2_data["submit"] = "Submit Application"
        step2_data.pop("continue", None)

        # Generate base64 JPEG photo proof
        photo_proof = page.evaluate('''(() => {
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
            ctx.fillText('Academic Year: 2024-2025', 60, 310);
            return c.toDataURL('image/jpeg', 0.9);
        })()''')
        step2_data["dev_pack_form[photo_proof]"] = photo_proof
        print(f"  photo_proof length: {len(photo_proof)}")

        print(f"\n  Step 2 POST data:")
        for k, v in step2_data.items():
            if "token" not in k.lower() and "photo_proof" not in k:
                print(f"    {k} = {v!r}")
            elif "photo_proof" in k:
                print(f"    {k} = [base64 JPEG, {len(v)} chars]")

        # Submit step 2
        print("\n=== Step 2: Submit ===")
        step2_result = page.evaluate('''async (formData) => {
            const body = new URLSearchParams(formData).toString();
            const r = await fetch("/settings/education/developer_pack_applications", {
                method: "POST",
                headers: {
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept": "text/html",
                    "Turbo-Frame": "dev-pack-form",
                },
                credentials: "same-origin",
                body: body,
            });
            const text = await r.text();
            return {status: r.status, url: r.url, bodyLen: text.length, body: text.substring(0, 3000)};
        }''', step2_data)
        print(f"  Status: {step2_result['status']}")
        print(f"  Response length: {step2_result['bodyLen']}")

        # Check result
        result_analysis = page.evaluate('''(html) => {
            const doc = new DOMParser().parseFromString(html, 'text/html');
            const text = doc.body?.textContent || '';
            const banner = doc.querySelector('.Banner-title, .flash-error, [data-target="x-banner.titleText"]');
            const success = text.toLowerCase().includes('thank') || text.toLowerCase().includes('submitted') || text.toLowerCase().includes('review');
            const errors = [];
            doc.querySelectorAll('.flash-error, .Banner--error, [data-target="x-banner.titleText"]').forEach(e => errors.push(e.textContent.trim()));
            // Check for "this field is required" type errors
            doc.querySelectorAll('.FormControl-inlineValidation--error, .invalid-feedback').forEach(e => errors.push(e.textContent.trim()));
            return {success, errors, textPreview: text.trim().substring(0, 500)};
        }''', step2_result["body"])

        print(f"\n  Result:")
        print(f"    Success indicators: {result_analysis.get('success')}")
        print(f"    Errors: {result_analysis.get('errors')}")
        print(f"    Text preview: {result_analysis.get('textPreview', '')[:300]}")

        with open("pw_v3_step2_resp.html", "w", encoding="utf-8") as f:
            f.write(step2_result["body"])

    elif resp_analysis.get("hasContinue") and resp_analysis.get("labels"):
        # Got extra school questions instead of step 2
        print("\n=== Got school info form (unknown school) ===")
        print(f"  Labels: {resp_analysis.get('labels')}")
        print("  Need to fill additional school info...")

        # Extract all fields
        extra_fields = page.evaluate('''(html) => {
            const doc = new DOMParser().parseFromString(html, 'text/html');
            const form = doc.querySelector('form');
            const fields = {};
            form.querySelectorAll('input[name], select[name], textarea[name]').forEach(el => {
                if (el.type === 'radio' && !el.checked) return;
                fields[el.name] = {
                    tag: el.tagName,
                    type: el.type || '',
                    value: el.value || '',
                    id: el.id,
                    required: el.required,
                    options: el.tagName === 'SELECT' ?
                        Array.from(el.options).map(o => ({value: o.value, text: o.textContent.trim()})) : [],
                };
            });
            return fields;
        }''', resp_html)
        print(f"\n  Extra fields:")
        for name, info in extra_fields.items():
            if "token" not in name.lower():
                print(f"    {name}: type={info['type']}, value={info['value']!r}, required={info['required']}")
                if info['options']:
                    print(f"      Options: {[o['text'] for o in info['options'][:5]]}")

        with open("pw_v3_step1_resp.html", "w", encoding="utf-8") as f:
            f.write(resp_html)
    else:
        print("\n=== Unexpected response ===")
        print(f"  Preview: {resp_html[:500]}")
        with open("pw_v3_unexpected.html", "w", encoding="utf-8") as f:
            f.write(resp_html)

    page.screenshot(path="pw_v3_final.png")
    browser.close()

print("\nDone!")
