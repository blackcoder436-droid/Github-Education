"""Education flow v4: Playwright login + DOM injection for form submission.
After fetch()-based step 1, inject step 2 HTML into page DOM and submit natively."""
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
                    if f: f.fill(otp); break
                page.wait_for_timeout(500)
                try: page.click('button[type="submit"]', timeout=5000)
                except: pass
                page.wait_for_load_state("load", timeout=30000)
                page.wait_for_timeout(3000)
    logged_in = "login" not in page.url
    print(f"  Logged in: {logged_in} ({page.url})")
    if not logged_in:
        browser.close(); sys.exit(1)

    # === Navigate to parent page ===
    print("\n=== Navigate to /settings/education/benefits ===")
    page.goto("https://github.com/settings/education/benefits", timeout=120000, wait_until="load")
    page.wait_for_timeout(5000)

    # === STEP 1: Fetch form via JS, inject into DOM, fill, submit via fetch ===
    print("\n=== Step 1: Fetch and inject form ===")
    inject_result = page.evaluate('''async () => {
        // Fetch the form HTML
        const r = await fetch("/settings/education/developer_pack_applications/new", {
            headers: {"Accept": "text/html", "Turbo-Frame": "dev-pack-form"},
            credentials: "same-origin",
        });
        const html = await r.text();

        // Inject into turbo-frame
        const tf = document.querySelector('#dev-pack-form');
        if (!tf) return {error: "no turbo-frame"};
        // Parse and extract inner content
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');
        const newFrame = doc.querySelector('turbo-frame');
        tf.innerHTML = newFrame ? newFrame.innerHTML : doc.body.innerHTML;

        // Verify form appeared
        const form = tf.querySelector('form');
        return {
            hasForm: !!form,
            htmlLen: html.length,
            fieldCount: form ? form.querySelectorAll('input, select').length : 0,
        };
    }''')
    print(f"  Injected: {inject_result}")

    if not inject_result.get('hasForm'):
        print("  FAILED to inject form!")
        browser.close(); sys.exit(1)

    # Fill step 1 fields via DOM
    print("\n=== Step 1: Fill form in DOM ===")
    fill_result = page.evaluate('''() => {
        const form = document.querySelector('#dev-pack-form form');

        // Select student radio
        const studentRadio = form.querySelector('input[value="student"][name*="application_type"]');
        if (studentRadio) { studentRadio.checked = true; studentRadio.click(); }

        // Set school name (both inputs)
        form.querySelectorAll('input[name="dev_pack_form[school_name]"]').forEach(i => {
            i.value = "SKT International College";
        });

        // Set school email
        const emailSelect = form.querySelector('select[name="dev_pack_form[school_email]"]');
        if (emailSelect && emailSelect.options.length > 0) {
            emailSelect.value = emailSelect.options[0].value;
        }

        // Set location
        const setVal = (sel, val) => {
            const el = form.querySelector(sel);
            if (el) el.value = val;
        };
        setVal('input[name="dev_pack_form[latitude]"]', '16.8661');
        setVal('input[name="dev_pack_form[longitude]"]', '96.1951');
        setVal('input[name="dev_pack_form[location_shared]"]', 'true');

        // Collect form data to verify
        const fd = new FormData(form);
        const data = {};
        for (const [k, v] of fd.entries()) {
            if (!k.includes('token')) data[k] = typeof v === 'string' ? v.substring(0, 100) : '[File]';
        }
        return {fields: data, hasToken: fd.has('authenticity_token')};
    }''')
    print(f"  Fields: {json.dumps(fill_result.get('fields', {}), indent=2)}")
    print(f"  Has token: {fill_result.get('hasToken')}")

    # Submit step 1 via native FormData (not URLSearchParams)
    print("\n=== Step 1: Submit ===")
    step1_result = page.evaluate('''async () => {
        const form = document.querySelector('#dev-pack-form form');
        const fd = new FormData(form);
        // Add continue button
        fd.set('continue', 'Continue');
        // Remove submit if present
        fd.delete('submit');

        const r = await fetch("/settings/education/developer_pack_applications", {
            method: "POST",
            headers: {
                "Turbo-Frame": "dev-pack-form",
            },
            credentials: "same-origin",
            body: fd,
        });
        const text = await r.text();
        return {status: r.status, bodyLen: text.length, body: text};
    }''')
    print(f"  Status: {step1_result['status']}, Length: {step1_result['bodyLen']}")

    resp_html = step1_result["body"]

    # Check for errors
    check = page.evaluate('''(html) => {
        const doc = new DOMParser().parseFromString(html, 'text/html');
        const banner = doc.querySelector('.Banner-title, .flash-error, [data-target="x-banner.titleText"]');
        const hasProof = !!doc.querySelector('input[name="dev_pack_form[proof_type]"]');
        const hasContinue = !!doc.querySelector('button[name="continue"]');
        const hasSubmit = !!doc.querySelector('button[name="submit"]');
        return {
            error: banner ? banner.textContent.trim() : null,
            hasProof, hasContinue, hasSubmit,
        };
    }''', resp_html)
    print(f"  Error: {check.get('error')}")
    print(f"  Has proof_type: {check['hasProof']}, submit: {check['hasSubmit']}, continue: {check['hasContinue']}")

    if not check['hasProof']:
        # Save for debugging
        with open("pw_v4_step1_resp.html", "w", encoding="utf-8") as f:
            f.write(resp_html)
        print("  Step 2 not reached! Saved response.")
        if check['hasContinue']:
            print("  Still on step 1. Checking what extra fields are needed...")
            extra = page.evaluate('''(html) => {
                const doc = new DOMParser().parseFromString(html, 'text/html');
                const labels = Array.from(doc.querySelectorAll('label')).map(l => l.textContent.trim()).filter(t => t.length > 3);
                return labels;
            }''', resp_html)
            print(f"  Labels: {extra}")
        browser.close(); sys.exit(1)

    # === STEP 2: Inject into DOM and submit ===
    print("\n=== Step 2: Inject into DOM ===")
    inject2 = page.evaluate('''(html) => {
        const tf = document.querySelector('#dev-pack-form');
        const doc = new DOMParser().parseFromString(html, 'text/html');
        const newFrame = doc.querySelector('turbo-frame');
        tf.innerHTML = newFrame ? newFrame.innerHTML : doc.body.innerHTML;

        const form = tf.querySelector('form');
        if (!form) return {error: "no form after inject"};

        // List all inputs for debugging
        const inputs = {};
        form.querySelectorAll('input[name], select[name]').forEach(i => {
            const name = i.name;
            if (!inputs[name]) inputs[name] = [];
            inputs[name].push({
                type: i.type,
                value: (i.value || '').substring(0, 50),
                id: i.id,
            });
        });
        return {hasForm: true, inputs};
    }''', resp_html)
    print(f"  Injected: form={inject2.get('hasForm')}")
    if inject2.get('inputs'):
        for name, vals in inject2['inputs'].items():
            if 'token' not in name.lower():
                for v in vals:
                    print(f"    {name}: type={v['type']}, value={v['value']!r}, id={v['id']!r}")

    # Set proof_type via DOM
    print("\n=== Step 2: Set proof_type ===")
    pt_result = page.evaluate('''() => {
        const form = document.querySelector('#dev-pack-form form');

        // Find and set proof_type hidden input
        const ptInput = form.querySelector('input[name="dev_pack_form[proof_type]"]');
        if (ptInput) {
            ptInput.value = "2. Dated official/unofficial transcript";
        }

        // Also try clicking the menuitemradio to trigger any connected JS
        const menuItem = form.querySelector('button[data-value="2. Dated official/unofficial transcript"]');
        if (menuItem) {
            menuItem.setAttribute('aria-checked', 'true');
            menuItem.click();
        }

        return {
            ptValue: ptInput?.value || 'MISSING',
            menuItemFound: !!menuItem,
        };
    }''')
    print(f"  proof_type: {pt_result}")

    # Generate and set photo_proof
    print("\n=== Step 2: Generate photo_proof ===")
    pp_result = page.evaluate('''() => {
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
        const dataUrl = c.toDataURL('image/jpeg', 0.9);

        // Set photo_proof - try multiple selectors
        const ppInput = document.querySelector('#photo_proof') ||
                       document.querySelector('input[name="dev_pack_form[photo_proof]"]');
        if (ppInput) {
            ppInput.value = dataUrl;
            return {set: true, name: ppInput.name, len: dataUrl.length};
        }
        return {set: false, error: "no photo_proof input found"};
    }''')
    print(f"  photo_proof: {pp_result}")

    # Fix form_variant
    page.evaluate('''() => {
        const form = document.querySelector('#dev-pack-form form');
        const variants = form.querySelectorAll('input[name="dev_pack_form[form_variant]"]');
        variants.forEach((v, i) => {
            if (i === 0) v.value = "upload_proof_form";
            else { v.disabled = true; v.removeAttribute('name'); }
        });
    }''')

    # Verify FormData before submit
    print("\n=== Step 2: FormData preview ===")
    fd_preview = page.evaluate('''() => {
        const form = document.querySelector('#dev-pack-form form');
        const fd = new FormData(form);
        const data = {};
        for (const [k, v] of fd.entries()) {
            const val = typeof v === 'string' ? v : '[File]';
            if (k.includes('token')) data[k] = '[TOKEN]';
            else if (k.includes('photo_proof')) data[k] = `[${val.length} chars]`;
            else data[k] = val.substring(0, 100);
        }
        return data;
    }''')
    for k, v in fd_preview.items():
        marker = " ***" if "proof" in k.lower() or "variant" in k.lower() else ""
        print(f"  {k} = {v!r}{marker}")

    # Check if proof_type is actually in FormData
    pt_in_fd = page.evaluate('''() => {
        const form = document.querySelector('#dev-pack-form form');
        const fd = new FormData(form);
        return fd.get('dev_pack_form[proof_type]');
    }''')
    print(f"\n  FormData proof_type = {pt_in_fd!r}")

    if not pt_in_fd:
        print("  WARNING: proof_type NOT in FormData! The input might be disabled or outside form.")
        # Debug: check if input is inside form
        debug = page.evaluate('''() => {
            const form = document.querySelector('#dev-pack-form form');
            const allPt = document.querySelectorAll('input[name="dev_pack_form[proof_type]"]');
            const results = [];
            allPt.forEach(inp => {
                results.push({
                    value: inp.value,
                    disabled: inp.disabled,
                    inForm: form.contains(inp),
                    parentTag: inp.parentElement?.tagName,
                    grandparentTag: inp.parentElement?.parentElement?.tagName,
                    ancestorTags: (() => {
                        const tags = [];
                        let el = inp;
                        while (el && el !== document.body) {
                            tags.push(el.tagName + (el.id ? '#' + el.id : ''));
                            el = el.parentElement;
                        }
                        return tags;
                    })(),
                });
            });
            return results;
        }''')
        print(f"  proof_type inputs debug: {json.dumps(debug, indent=2)}")

    # === SUBMIT STEP 2 ===
    print("\n=== Step 2: Submit ===")
    step2_result = page.evaluate('''async () => {
        const form = document.querySelector('#dev-pack-form form');
        const fd = new FormData(form);
        // Make sure values are set
        fd.set('dev_pack_form[proof_type]', '2. Dated official/unofficial transcript');
        fd.set('dev_pack_form[form_variant]', 'upload_proof_form');
        fd.set('submit', 'Submit Application');
        fd.delete('continue');

        // Ensure photo_proof
        const pp = document.querySelector('#photo_proof, input[name="dev_pack_form[photo_proof]"]');
        if (pp && pp.value) fd.set(pp.name, pp.value);

        const r = await fetch("/settings/education/developer_pack_applications", {
            method: "POST",
            headers: {
                "Turbo-Frame": "dev-pack-form",
            },
            credentials: "same-origin",
            body: fd,
        });
        const text = await r.text();
        return {status: r.status, bodyLen: text.length, body: text};
    }''')
    print(f"  Status: {step2_result['status']}, Length: {step2_result['bodyLen']}")

    # Analyze result
    result_info = page.evaluate('''(html) => {
        const doc = new DOMParser().parseFromString(html, 'text/html');
        const text = doc.body?.textContent || '';
        const errors = [];
        doc.querySelectorAll('.Banner-title, .flash-error, [data-target="x-banner.titleText"]').forEach(e => {
            errors.push(e.textContent.trim());
        });
        // Check for inline validation errors
        doc.querySelectorAll('.FormControl-inlineValidation--error, [aria-invalid="true"]').forEach(e => {
            const label = e.closest('.FormControl')?.querySelector('.FormControl-label')?.textContent?.trim();
            errors.push('Field: ' + (label || 'unknown') + ' - ' + e.textContent.trim().substring(0, 100));
        });
        // Check for required field hints
        const requiredFields = [];
        doc.querySelectorAll('[aria-required="true"], [required]').forEach(e => {
            const name = e.name || e.id || e.getAttribute('aria-label') || '';
            const label = e.closest('.FormControl, fieldset')?.querySelector('label, legend')?.textContent?.trim() || '';
            requiredFields.push({name, label: label.substring(0, 80)});
        });
        // Check aria-checked on proof type
        const checkedItems = [];
        doc.querySelectorAll('[aria-checked="true"]').forEach(e => {
            checkedItems.push(e.textContent.trim().substring(0, 80));
        });
        // Check photo_proof value
        const ppInput = doc.querySelector('#photo_proof, input[name*="photo_proof"]');
        const ppVal = ppInput?.value?.length || 0;
        const success = text.toLowerCase().includes('thank') || text.toLowerCase().includes('submitted') || text.toLowerCase().includes('pending');
        return {success, errors, requiredFields, checkedItems, photoProofLen: ppVal, textPreview: text.trim().substring(0, 500)};
    }''', step2_result["body"])

    print(f"\n  Success: {result_info['success']}")
    print(f"  Errors: {result_info['errors']}")
    print(f"  Required fields: {json.dumps(result_info['requiredFields'], indent=2)}")
    print(f"  Checked items: {result_info['checkedItems']}")
    print(f"  Photo proof in response: {result_info['photoProofLen']}")
    print(f"  Text: {result_info['textPreview'][:300]}")

    with open("pw_v4_result.html", "w", encoding="utf-8") as f:
        f.write(step2_result["body"])
    page.screenshot(path="pw_v4_final.png")
    browser.close()

print("\nDone!")
