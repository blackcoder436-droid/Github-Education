"""Education v25: Wait for JS to fully load, then interact with autocomplete properly."""
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
        geolocation={"latitude": 16.8661, "longitude": 96.1951},
    )
    page = context.new_page()

    # === LOGIN ===
    print("=== Login ===")
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
    print(f"  Logged in: {'login' not in page.url}")

    # === Navigate and wait for full JS init ===
    print("\n=== Navigate to form ===")
    page.goto("https://github.com/settings/education/developer_pack_applications/new", timeout=120000, wait_until="networkidle")
    page.wait_for_timeout(10000)

    # Verify custom elements loaded
    ce_ok = page.evaluate('!!customElements.get("react-partial") && !!customElements.get("auto-complete")')
    print(f"  Custom elements ready: {ce_ok}")

    # Check if React partial has rendered
    rp_rendered = page.evaluate('''() => {
        const rp = document.querySelector('react-partial[partial-name="education-schools-auto-complete"]');
        if (!rp) return "not found";
        const root = rp.querySelector('[data-target="react-partial.reactRoot"]');
        return {
            innerHTML: root?.innerHTML?.substring(0, 300) || 'empty',
            childCount: root?.children?.length || 0,
        };
    }''')
    print(f"  React partial rendered: {rp_rendered}")

    # === Click Student ===
    print("\n=== Step 1: Select student ===")
    page.evaluate('''() => {
        const radio = document.querySelector('input[value="student"]');
        if (radio) {
            radio.click();
            radio.dispatchEvent(new Event('change', {bubbles: true}));
        }
    }''')
    page.wait_for_timeout(1000)

    # === Interact with autocomplete ===
    print("\n=== Autocomplete interaction ===")

    # Listen for network
    school_responses = []
    def on_resp(response):
        if 'school' in response.url:
            try: body = response.text()
            except: body = ''
            school_responses.append({'url': response.url, 'status': response.status, 'body': body[:1000]})
    page.on("response", on_resp)

    # Click on the search input and type
    search_input = page.wait_for_selector('#js-school-name-search', timeout=5000)
    search_input.click()
    page.wait_for_timeout(500)

    # Type slowly
    page.keyboard.type("University of Computer", delay=80)
    page.wait_for_timeout(3000)

    print(f"  Network responses: {len(school_responses)}")
    for r in school_responses:
        print(f"    {r['status']} {r['url'][:100]}")
        if r['body']:
            print(f"    Body: {r['body'][:200]}")

    # Check dropdown
    dropdown = page.evaluate('''() => {
        const list = document.getElementById('js-school-name-list');
        if (!list) return "no list";
        const items = list.querySelectorAll('[data-autocomplete-value]');
        const results = [];
        items.forEach(item => {
            results.push({
                name: item.getAttribute('data-school-name') || '',
                value: item.getAttribute('data-autocomplete-value') || '',
                schoolId: item.getAttribute('data-selected-school-id') || '',
            });
        });
        return {count: items.length, items: results.slice(0, 5), visible: list.matches(':popover-open')};
    }''')
    print(f"  Dropdown: {json.dumps(dropdown, indent=2)[:400]}")

    # If dropdown has items, click on UCSY
    if isinstance(dropdown, dict) and dropdown.get('count', 0) > 0:
        print("\n  Clicking UCSY from dropdown...")

        # Check state BEFORE clicking
        before = page.evaluate('''() => {
            const inputs = {};
            document.querySelectorAll('input').forEach(el => {
                if (el.name && (el.name.includes('school') || el.name.includes('enrollment')))
                    inputs[el.name + ' (' + el.type + ')'] = el.value.substring(0, 100);
            });
            return inputs;
        }''')
        print(f"  Before: {json.dumps(before, indent=2)}")

        # Click the UCSY item
        clicked = page.evaluate('''() => {
            const list = document.getElementById('js-school-name-list');
            const ucsy = list.querySelector('[data-selected-school-id="7620"]');
            if (!ucsy) {
                // Try first item
                const first = list.querySelector('[data-autocomplete-value]');
                if (first) {
                    first.click();
                    return {clicked: first.getAttribute('data-school-name'), id: first.getAttribute('data-selected-school-id')};
                }
                return {error: "no items"};
            }
            ucsy.click();
            return {clicked: "UCSY", id: "7620"};
        }''')
        print(f"  Clicked: {clicked}")
        page.wait_for_timeout(2000)

        # Check state AFTER clicking
        after = page.evaluate('''() => {
            const inputs = {};
            document.querySelectorAll('input').forEach(el => {
                if (el.name && (el.name.includes('school') || el.name.includes('enrollment') || el.name.includes('selected')))
                    inputs[el.name + ' (' + el.type + ')'] = el.value.substring(0, 100);
            });
            const btn = document.querySelector('button[name="continue"]');
            return {inputs, btnEnabled: btn ? !btn.disabled : null};
        }''')
        print(f"  After: {json.dumps(after, indent=2)}")

        # Check Continue button
        if after.get('btnEnabled'):
            print("\n  Continue button is ENABLED! Clicking...")
            page.click('button[name="continue"]')
            page.wait_for_timeout(8000)

            # Check what page we're on now
            page_state = page.evaluate('''() => {
                const hasProof = !!document.querySelector('[name="dev_pack_form[proof_type]"]');
                const hasPhoto = !!document.querySelector('[name="dev_pack_form[photo_proof]"]');
                const allHidden = {};
                document.querySelectorAll('input[type="hidden"]').forEach(el => {
                    if (el.name && !el.name.includes('authenticity'))
                        allHidden[el.name] = (el.value || '').substring(0, 100);
                });
                return {hasProof, hasPhoto, hidden: allHidden, text: document.body?.textContent?.trim()?.substring(0, 300) || ''};
            }''')
            print(f"  On step 2: proof={page_state.get('hasProof')}, photo={page_state.get('hasPhoto')}")
            print(f"  Hidden fields: {json.dumps(page_state.get('hidden', {}), indent=2)}")
            print(f"  Text: {page_state.get('text', '')[:200]}")

            if page_state.get('hasProof'):
                # Now submit step 2 with photo proof
                print("\n=== Step 2: Submit photo ===")
                step2_result = page.evaluate('''async () => {
                    const form = document.querySelector('form[action="/settings/education/developer_pack_applications"]');
                    if (!form) return {error: "no form"};

                    // Generate photo
                    const c = document.createElement('canvas');
                    c.width = 640; c.height = 480;
                    const ctx = c.getContext('2d');
                    ctx.fillStyle = '#2563eb'; ctx.fillRect(0, 0, 640, 480);
                    ctx.fillStyle = '#fff'; ctx.font = '24px sans-serif';
                    ctx.fillText('Student ID - UCSY', 30, 50);
                    ctx.fillText('Academic Year 2024-2025', 30, 90);
                    const photoDataUrl = c.toDataURL('image/jpeg', 0.8);

                    const photoJson = JSON.stringify({
                        image: photoDataUrl,
                        metadata: {filename: null, type: null, mimeType: "image/jpeg", deviceLabel: null}
                    });

                    // Set values on the actual form
                    const photoInput = form.querySelector('[name="dev_pack_form[photo_proof]"]');
                    if (photoInput) photoInput.value = photoJson;

                    // Set proof_type
                    const proofInput = form.querySelector('[name="dev_pack_form[proof_type]"]');
                    if (proofInput) proofInput.value = '2. Dated official/unofficial transcript';

                    // Set form_variant to upload_proof_form
                    form.querySelectorAll('[name="dev_pack_form[form_variant]"]').forEach(el => {
                        el.value = 'upload_proof_form';
                    });

                    // Collect form data
                    const fd = new FormData(form);
                    const sent = {};
                    for (const [k, v] of fd.entries()) {
                        if (k !== 'authenticity_token') sent[k] = (typeof v === 'string' ? v : v.name).substring(0, 100);
                    }

                    // Submit via fetch
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

                    // Parse response
                    let respDoc;
                    if (respText.includes('<turbo-stream')) {
                        const tmpDoc = new DOMParser().parseFromString(respText, 'text/html');
                        const tmpl = tmpDoc.querySelector('template');
                        if (tmpl) {
                            const c2 = document.createElement('div');
                            c2.appendChild(tmpl.content.cloneNode(true));
                            respDoc = new DOMParser().parseFromString(c2.innerHTML, 'text/html');
                        } else respDoc = tmpDoc;
                    } else {
                        respDoc = new DOMParser().parseFromString(respText, 'text/html');
                    }

                    const errors = [];
                    respDoc.querySelectorAll('.Banner-title, [data-target="x-banner.titleText"]').forEach(e => errors.push(e.textContent.trim()));
                    const bodyText = respDoc.body?.textContent?.trim() || '';
                    const success = bodyText.toLowerCase().includes('thank') ||
                                   bodyText.toLowerCase().includes('submitted') ||
                                   bodyText.toLowerCase().includes('pending') ||
                                   bodyText.toLowerCase().includes('approved');

                    return {status: r.status, success, errors, sent, bodyPreview: bodyText.substring(0, 500)};
                }''')
                print(f"  Result: {json.dumps(step2_result, indent=2)[:800]}")
        else:
            print("  Continue button still disabled!")
            # Print ALL form data
            form_data = page.evaluate('''() => {
                const form = document.querySelector('form');
                if (!form) return "no form";
                const fd = new FormData(form);
                const data = {};
                for (const [k,v] of fd.entries()) {
                    if (k !== 'authenticity_token') data[k] = (typeof v === 'string' ? v : v.name).substring(0, 100);
                }
                return data;
            }''')
            print(f"  Form data: {json.dumps(form_data, indent=2)}")
    else:
        print("  No dropdown items! Autocomplete not working.")
        # Maybe need different typing approach
        # Try pressing Enter or Tab to trigger
        page.keyboard.press('Backspace')
        page.wait_for_timeout(500)
        page.keyboard.type("s", delay=100)
        page.wait_for_timeout(2000)
        print(f"  After re-type - responses: {len(school_responses)}")

    browser.close()

print("\nDone!")
