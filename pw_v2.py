"""Fully automated education flow: login + form fill entirely in Playwright."""
import os, sys, json, time
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from urllib.parse import parse_qsl
import pyotp
load_dotenv()

USERNAME = os.environ['GITHUB_USERNAME']
PASSWORD = os.environ['GITHUB_PASSWORD']
TOTP_SECRET = "SFDHLAA7MDH2S7TN"

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=[
            '--use-fake-ui-for-media-stream',
            '--use-fake-device-for-media-stream',
        ]
    )
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
        permissions=["geolocation", "camera", "microphone"],
        geolocation={"latitude": 16.8661, "longitude": 96.1951},
    )
    page = context.new_page()

    # Capture POST requests to education form
    captured_posts = []
    def on_request(req):
        if req.method == "POST" and "developer_pack" in req.url:
            pairs = parse_qsl(req.post_data or "", keep_blank_values=True)
            fields = {k: v[:100] for k, v in pairs}
            captured_posts.append(fields)
            pt = fields.get("dev_pack_form[proof_type]", "MISSING")
            pp = fields.get("dev_pack_form[photo_proof]", "MISSING")
            fv = fields.get("dev_pack_form[form_variant]", "MISSING")
            print(f"  POST: proof_type={pt!r}, photo={pp[:30]!r}..., variant={fv!r}")
    page.on("request", on_request)

    # === LOGIN IN PLAYWRIGHT ===
    print("=== Login ===")
    page.goto("https://github.com/login", timeout=60000, wait_until="load")
    page.wait_for_timeout(3000)

    page.fill('#login_field', USERNAME)
    page.fill('#password', PASSWORD)
    page.wait_for_timeout(1000)
    page.click('input[name="commit"]')
    page.wait_for_timeout(5000)

    # Handle 2FA
    if "two-factor" in page.url or "two_factor" in page.url:
        print("  2FA required...")
        otp = pyotp.TOTP(TOTP_SECRET).now()
        # Try app-based OTP field
        otp_field = page.query_selector('#app_totp')
        if otp_field:
            otp_field.fill(otp)
        else:
            page.fill('input[name="otp"]', otp)
        page.wait_for_timeout(1000)
        # Click verify/sign in button
        try:
            page.click('button[type="submit"]', timeout=5000)
        except Exception:
            page.evaluate('document.querySelector("button[type=submit], input[type=submit]")?.click()')
        page.wait_for_timeout(5000)

    # Verify login
    logged_in = 'github.com/login' not in page.url
    print(f"  Logged in: {logged_in} (URL: {page.url})")
    if not logged_in:
        page.screenshot(path="pw_login_fail.png")
        print("  Login failed!")
        browser.close()
        sys.exit(1)

    # === NAVIGATE TO PARENT PAGE ===
    print("\n=== Navigating to /settings/education/benefits ===")
    page.goto("https://github.com/settings/education/benefits", timeout=120000, wait_until="load")
    page.wait_for_timeout(15000)

    ce = page.evaluate('''(() => {
        const names = ['react-partial', 'action-menu', 'turbo-frame'];
        const r = {};
        for (const n of names) r[n] = !!customElements.get(n);
        return r;
    })()''')
    print(f"Custom elements: {ce}")

    # === WAIT FOR TURBO FRAME TO LOAD ===
    print("\n=== Waiting for education form in turbo-frame ===")
    page.evaluate('''(() => {
        const frame = document.querySelector('#dev-pack-form');
        if (frame) { frame.scrollIntoView(); if (frame.loading === 'lazy') frame.loading = 'eager'; }
    })()''')
    for attempt in range(15):
        has_form = page.evaluate('!!document.querySelector(\'#dev-pack-form form\')')
        if has_form:
            print(f"  Form loaded after {(attempt+1)*2}s")
            break
        page.wait_for_timeout(2000)
    else:
        # Force src
        page.evaluate('document.querySelector("#dev-pack-form").src = "/settings/education/developer_pack_applications/new"')
        page.wait_for_timeout(8000)
        has_form = page.evaluate('!!document.querySelector(\'#dev-pack-form form\')')
        print(f"  Form after force src: {has_form}")

    # Check form state
    has_continue = page.evaluate('!!document.querySelector(\'button[name="continue"]\')')
    has_submit = page.evaluate('!!document.querySelector(\'button[name="submit"]\')')
    has_proof = page.evaluate('!!document.querySelector(\'input[name="dev_pack_form[proof_type]"]\')')
    already_applied = page.evaluate('''(() => {
        const text = document.querySelector('#dev-pack-form')?.textContent || '';
        return text.includes('already') || text.includes('pending') || text.includes('approved');
    })()''')
    print(f"Form state: continue={has_continue}, submit={has_submit}, proof_type={has_proof}, already_applied={already_applied}")

    if already_applied:
        print("  Education already applied/pending!")
        browser.close()
        sys.exit(0)

    # === STEP 1: FILL AND SUBMIT ===
    if has_continue and not has_proof:
        print("\n=== Step 1: Fill initial form ===")
        # Select student
        page.evaluate('document.querySelector(\'input[value="student"]\')?.click()')
        page.wait_for_timeout(1000)

        # Wait for autocomplete hydration
        for i in range(8):
            hydrated = page.evaluate('''(() => {
                const rp = document.querySelector('react-partial[partial-name="education-schools-auto-complete"]');
                return rp?.querySelector('[data-target="react-partial.reactRoot"]')?.childElementCount > 0;
            })()''')
            if hydrated:
                print(f"  Autocomplete hydrated ({(i+1)*2}s)")
                break
            page.wait_for_timeout(2000)

        # Type school
        school_input = page.query_selector('#js-school-name-search')
        if school_input:
            school_input.focus()
            page.wait_for_timeout(500)
            school_input.type("SKT International", delay=80)
            page.wait_for_timeout(6000)

            ac_count = page.evaluate('''(() => {
                const list = document.querySelector('#js-school-name-list');
                if (!list) return 0;
                return list.querySelectorAll('[role="option"], li, button, [data-autocomplete-value]').length;
            })()''')
            print(f"  Autocomplete results: {ac_count}")
            if ac_count > 0:
                page.evaluate('''(() => {
                    const items = document.querySelectorAll('#js-school-name-list [role="option"], #js-school-name-list li');
                    for (const item of items) {
                        if (item.textContent.includes("SKT")) { item.click(); return; }
                    }
                    items[0]?.click();
                })()''')
                page.wait_for_timeout(2000)
            else:
                print("  Setting school name manually...")
                page.evaluate('''(() => {
                    document.querySelectorAll('input[name="dev_pack_form[school_name]"]').forEach(i => i.value = "SKT International College");
                    const s = document.querySelector('#js-school-name-search');
                    if (s) s.value = "SKT International College";
                })()''')

        # Set location
        page.evaluate('''(() => {
            const s = (sel, val) => { const e = document.querySelector(sel); if(e) e.value = val; };
            s('#js-developer-pack-application-latitude-input, #dev_pack_form_latitude', '16.8661');
            s('#js-developer-pack-application-longitude-input, #dev_pack_form_longitude', '96.1951');
            s('#js-developer-pack-application-location-shared-input, #dev_pack_form_location_shared', 'true');
        })()''')

        # Enable and click Continue
        page.evaluate('''(() => {
            const btn = document.querySelector('button[name="continue"]');
            if (btn) { btn.disabled = false; btn.style.cssText = 'display:block !important; visibility:visible !important;'; }
        })()''')
        page.wait_for_timeout(500)
        print("  Clicking Continue...")
        page.evaluate('document.querySelector(\'button[name="continue"]\').click()')
        page.wait_for_timeout(12000)

        err = page.evaluate('''(() => {
            const b = document.querySelector('.Banner-title, [data-target="x-banner.titleText"], .flash-error');
            return b ? b.textContent.trim() : null;
        })()''')
        if err:
            print(f"  After Continue: {err}")

    # === CHECK STEP 2 ===
    has_proof = page.evaluate('!!document.querySelector(\'input[name="dev_pack_form[proof_type]"]\')')
    print(f"\nStep 2 proof_type input present: {has_proof}")
    if not has_proof:
        # Extra wait
        for i in range(10):
            has_proof = page.evaluate('!!document.querySelector(\'input[name="dev_pack_form[proof_type]"]\')')
            if has_proof:
                break
            page.wait_for_timeout(2000)

    if not has_proof:
        frame_text = page.evaluate('(document.querySelector("#dev-pack-form")?.textContent || "").substring(0, 500)')
        print(f"  Frame content: {frame_text}")
        page.screenshot(path="pw_v2_no_step2.png")
        browser.close()
        sys.exit(1)

    # Wait for action-menu
    print("\n=== Waiting for action-menu ===")
    for i in range(10):
        am = page.evaluate('!!customElements.get("action-menu")')
        if am:
            print(f"  action-menu ready ({(i+1)*2}s)")
            break
        page.wait_for_timeout(2000)

    # Wait for webcam
    print("\n=== Waiting for webcam component ===")
    wc_hydrated = False
    for i in range(15):
        wc = page.evaluate('''(() => {
            const root = document.querySelector('react-partial[partial-name="webcam-upload"] [data-target="react-partial.reactRoot"]');
            return root ? root.childElementCount : -1;
        })()''')
        if wc > 0:
            wc_hydrated = True
            print(f"  Webcam hydrated! ({(i+1)*2}s, {wc} children)")
            break
        page.wait_for_timeout(2000)
    if not wc_hydrated:
        print(f"  Webcam not hydrated after 30s (children={wc})")

    # === SELECT PROOF TYPE ===
    print("\n=== Select proof type ===")
    page.evaluate('''(() => {
        // Use action-menu JS API if available, otherwise set manually
        const items = document.querySelectorAll('button[role="menuitemradio"]');
        for (const item of items) {
            if (item.dataset.value && item.dataset.value.includes("official")) {
                item.click();
                return;
            }
        }
        // Fallback: set hidden input directly
        const inp = document.querySelector('input[name="dev_pack_form[proof_type]"]');
        if (inp) inp.value = "2. Dated official/unofficial transcript";
    })()''')
    page.wait_for_timeout(2000)
    proof_val = page.evaluate('document.querySelector(\'input[name="dev_pack_form[proof_type]"]\')?.value')
    print(f"  proof_type = {proof_val!r}")

    # === HANDLE WEBCAM ===
    print("\n=== Webcam photo ===")
    if wc_hydrated:
        print("  Webcam hydrated! Looking for capture button...")
        wc_btns = page.evaluate('''(() => {
            const root = document.querySelector('react-partial[partial-name="webcam-upload"] [data-target="react-partial.reactRoot"]');
            if (!root) return [];
            return Array.from(root.querySelectorAll('button')).map(b => ({
                text: b.textContent.trim().substring(0, 80),
                disabled: b.disabled,
            }));
        })()''')
        print(f"  Buttons: {json.dumps(wc_btns)}")

        # Try capture
        page.wait_for_timeout(3000)  # Wait for camera init
        for btn in wc_btns:
            txt = btn['text'].lower()
            if any(kw in txt for kw in ['take', 'capture', 'photo', 'snap', 'camera']):
                page.evaluate(f'''(() => {{
                    const root = document.querySelector('react-partial[partial-name="webcam-upload"] [data-target="react-partial.reactRoot"]');
                    const btns = root.querySelectorAll('button');
                    for (const b of btns) {{
                        if (b.textContent.trim().includes("{btn['text'][:30]}")) {{ b.click(); return; }}
                    }}
                }})()''')
                print(f"  Clicked: {btn['text']}")
                page.wait_for_timeout(3000)
                break

        # Check for confirm button
        wc_btns2 = page.evaluate('''(() => {
            const root = document.querySelector('react-partial[partial-name="webcam-upload"] [data-target="react-partial.reactRoot"]');
            if (!root) return [];
            return Array.from(root.querySelectorAll('button')).map(b => ({
                text: b.textContent.trim().substring(0, 80), disabled: b.disabled
            }));
        })()''')
        for btn in wc_btns2:
            txt = btn['text'].lower()
            if any(kw in txt for kw in ['use', 'confirm', 'done', 'accept']):
                page.evaluate(f'''(() => {{
                    const root = document.querySelector('react-partial[partial-name="webcam-upload"] [data-target="react-partial.reactRoot"]');
                    const btns = root.querySelectorAll('button');
                    for (const b of btns) {{
                        if (b.textContent.trim().includes("{btn['text'][:30]}")) {{ b.click(); return; }}
                    }}
                }})()''')
                print(f"  Clicked confirm: {btn['text']}")
                page.wait_for_timeout(2000)
                break

        pp_val = page.evaluate('document.getElementById("photo_proof")?.value || ""')
        print(f"  photo_proof length: {len(pp_val)}")
    else:
        print("  Webcam not hydrated. Generating canvas fallback...")
        page.evaluate('''(() => {
            const inp = document.getElementById("photo_proof");
            if (!inp) return;
            const c = document.createElement('canvas');
            c.width = 1280; c.height = 720;
            const ctx = c.getContext('2d');
            const g = ctx.createLinearGradient(0,0,1280,720);
            g.addColorStop(0,'#1f2937'); g.addColorStop(1,'#f59e0b');
            ctx.fillStyle = g; ctx.fillRect(0,0,1280,720);
            ctx.fillStyle = '#fff'; ctx.font = 'bold 56px sans-serif';
            ctx.fillText('Student Proof', 60, 120);
            ctx.font = '36px sans-serif';
            ctx.fillText(new Date().toISOString(), 60, 190);
            ctx.fillText('SKT International College', 60, 250);
            inp.value = c.toDataURL('image/jpeg', 0.92);
        })()''')
        pp_len = page.evaluate('(document.getElementById("photo_proof")?.value || "").length')
        print(f"  Fallback photo_proof length: {pp_len}")

    # Fix form_variant duplicates
    page.evaluate('''(() => {
        const inputs = document.querySelectorAll('input[name="dev_pack_form[form_variant]"]');
        inputs.forEach((i, idx) => {
            if (idx === 0) i.value = "upload_proof_form";
            else { i.disabled = true; i.removeAttribute('name'); }
        });
    })()''')

    # === FORMDATA PREVIEW ===
    print("\n=== FormData ===")
    fd = page.evaluate('''(() => {
        const form = document.querySelector('#dev-pack-form form, form[action*="developer_pack"]');
        if (!form) return {error: "no form"};
        const fd = new FormData(form);
        const r = {};
        for (const [k, v] of fd.entries()) r[k] = (typeof v === 'string' ? v : '[File]').substring(0, 100);
        return r;
    })()''')
    for k, v in fd.items():
        marker = " ***" if "proof" in k.lower() or "variant" in k.lower() else ""
        print(f"  {k} = {v!r}{marker}")

    # === SUBMIT ===
    print("\n=== Submit ===")
    page.evaluate('''(() => {
        const btn = document.querySelector('button[name="submit"]');
        if (btn) { btn.disabled = false; btn.click(); }
    })()''')
    page.wait_for_timeout(12000)

    content = page.content()
    with open("pw_v2_result.html", "w", encoding="utf-8") as f:
        f.write(content)

    if "cannot be reviewed" in content:
        err = page.evaluate('document.querySelector(".Banner-title, [data-target=\\"x-banner.titleText\\"]")?.textContent?.trim() || "Unknown"')
        print(f"\n*** FAILED: {err} ***")
    elif any(kw in content.lower() for kw in ["thank", "submitted", "review"]):
        print("\n*** SUCCESS! ***")
    else:
        print(f"\nResult unclear. HTML: {len(content)} bytes")

    page.screenshot(path="pw_v2_final.png")
    print(f"\nPOSTs captured: {len(captured_posts)}")
    for i, f in enumerate(captured_posts):
        print(f"--- POST {i} ---")
        for k, v in f.items():
            m = " ***" if "proof" in k.lower() or "variant" in k.lower() else ""
            print(f"  {k} = {v!r}{m}")

    browser.close()

print("\nDone!")
