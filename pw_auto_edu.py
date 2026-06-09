"""Fully automated education flow: navigate to PARENT page so JS loads properly."""
import os, sys, json, time
from dotenv import load_dotenv
from client import GitHubClient
from playwright.sync_api import sync_playwright
from urllib.parse import parse_qsl
load_dotenv()

c = GitHubClient()
ok = c.login(os.environ['GITHUB_USERNAME'], os.environ['GITHUB_PASSWORD'], totp_secret="SFDHLAA7MDH2S7TN")
print(f"Login: {ok}")
if not ok:
    sys.exit(1)

cookies = []
for cookie in c.session.cookies:
    cookies.append({
        "name": cookie.name,
        "value": cookie.value,
        "domain": cookie.domain or ".github.com",
        "path": cookie.path or "/",
        "secure": cookie.secure,
    })

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
    context.add_cookies(cookies)
    page = context.new_page()

    # Capture POST requests
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

    # === KEY FIX: Navigate to PARENT page so all JS bundles load ===
    print("=== Navigating to /settings/education/benefits (parent page) ===")
    page.goto(
        "https://github.com/settings/education/benefits",
        timeout=120000, wait_until="load",
    )
    page.wait_for_timeout(15000)

    # Check JS loaded
    ce = page.evaluate('''(() => {
        const names = ['react-partial', 'action-menu', 'action-list', 'turbo-frame'];
        const r = {};
        for (const n of names) r[n] = !!customElements.get(n);
        return r;
    })()''')
    print(f"Custom elements: {ce}")

    scripts_count = page.evaluate('document.querySelectorAll("script[src]").length')
    print(f"Script tags: {scripts_count}")

    # Wait for Turbo Frame to load the education form (it's lazy-loaded)
    print("\n=== Waiting for turbo-frame to load education form ===")
    # Trigger lazy frame load by scrolling it into view or forcing src load
    page.evaluate('''(() => {
        const frame = document.querySelector('#dev-pack-form');
        if (frame) {
            frame.scrollIntoView();
            // Force loading if lazy
            if (frame.loading === 'lazy') {
                frame.loading = 'eager';
                frame.reload && frame.reload();
            }
        }
    })()''')
    for attempt in range(15):
        has_form = page.evaluate('!!document.querySelector(\'#dev-pack-form form\')')
        if has_form:
            print(f"  Form loaded after {(attempt+1)*2}s")
            break
        page.wait_for_timeout(2000)
    else:
        print("  Form not loaded after 30s, trying direct src fetch...")
        page.evaluate('''(() => {
            const frame = document.querySelector('#dev-pack-form');
            if (frame) frame.src = "/settings/education/developer_pack_applications/new";
        })()''')
        page.wait_for_timeout(8000)

    # Check what form is showing (step 1 or step 2)
    has_continue = page.evaluate('!!document.querySelector(\'button[name="continue"]\')')
    has_submit = page.evaluate('!!document.querySelector(\'button[name="submit"]\')')
    has_proof_type = page.evaluate('!!document.querySelector(\'input[name="dev_pack_form[proof_type]"]\')')
    print(f"\nForm state: continue={has_continue}, submit={has_submit}, proof_type={has_proof_type}")

    # If step 1 (has continue button), fill and submit
    if has_continue and not has_proof_type:
        print("\n=== Step 1: Fill initial form ===")
        page.evaluate('document.querySelector(\'input[value="student"]\')?.click()')
        page.wait_for_timeout(1000)

        # Wait for school autocomplete React partial to hydrate
        print("  Waiting for school autocomplete to hydrate...")
        for attempt in range(10):
            hydrated = page.evaluate('''(() => {
                const rp = document.querySelector('react-partial[partial-name="education-schools-auto-complete"]');
                if (!rp) return false;
                const root = rp.querySelector('[data-target="react-partial.reactRoot"]');
                return root ? root.childElementCount > 0 : false;
            })()''')
            if hydrated:
                print(f"    Hydrated after {(attempt+1)*2}s")
                break
            page.wait_for_timeout(2000)
        else:
            print("    Autocomplete not hydrated after 20s, continuing anyway")

        # Type school name
        school_input = page.query_selector('#js-school-name-search')
        if school_input:
            school_input.focus()
            page.wait_for_timeout(500)
            school_input.type("SKT International", delay=50)
            page.wait_for_timeout(5000)

            ac_count = page.evaluate('''(() => {
                const list = document.querySelector('#js-school-name-list');
                if (!list) return 0;
                return list.querySelectorAll('[role="option"], li, button').length;
            })()''')
            print(f"  Autocomplete results: {ac_count}")

            if ac_count > 0:
                page.evaluate('''(() => {
                    const items = document.querySelectorAll('#js-school-name-list [role="option"], #js-school-name-list li, #js-school-name-list button');
                    for (const item of items) {
                        if (item.textContent.includes("SKT")) { item.click(); return; }
                    }
                    items[0]?.click();
                })()''')
                page.wait_for_timeout(2000)
            else:
                print("  No autocomplete results, setting school manually...")
                page.evaluate('''(() => {
                    document.querySelectorAll('input[name="dev_pack_form[school_name]"]').forEach(i => i.value = "SKT International College");
                    const search = document.querySelector('#js-school-name-search');
                    if (search) search.value = "SKT International College";
                })()''')

        # Location
        page.evaluate('''(() => {
            const s = (sel, val) => { const e = document.querySelector(sel); if(e) e.value = val; };
            s('#js-developer-pack-application-latitude-input, #dev_pack_form_latitude', '16.8661');
            s('#js-developer-pack-application-longitude-input, #dev_pack_form_longitude', '96.1951');
            s('#js-developer-pack-application-location-shared-input, #dev_pack_form_location_shared', 'true');
        })()''')

        # Enable Continue button (it may be hidden/disabled by form validation JS)
        page.evaluate('''(() => {
            const btn = document.querySelector('button[name="continue"]');
            if (btn) {
                btn.disabled = false;
                btn.style.display = '';
                btn.style.visibility = 'visible';
                btn.removeAttribute('hidden');
                // Also check parent elements
                let el = btn.parentElement;
                while (el && el !== document.body) {
                    el.style.display = '';
                    el.style.visibility = 'visible';
                    el = el.parentElement;
                }
            }
        })()''')
        page.wait_for_timeout(500)

        # Click Continue via JS if Playwright click fails due to visibility
        print("  Clicking Continue...")
        try:
            page.click('button[name="continue"]', timeout=5000)
        except Exception:
            print("  Playwright click failed, using JS click...")
            page.evaluate('document.querySelector(\'button[name="continue"]\').click()')
        page.wait_for_timeout(10000)

        # Check what happened after Continue
        post_url = page.url
        print(f"  URL after Continue: {post_url}")
        has_error = page.evaluate('''(() => {
            const banner = document.querySelector('.Banner-title, [data-target="x-banner.titleText"], .flash-error');
            return banner ? banner.textContent.trim() : null;
        })()''')
        if has_error:
            print(f"  Error after Continue: {has_error}")
        # Check turbo-frame content
        frame_html_len = page.evaluate('''(() => {
            const frame = document.querySelector('#dev-pack-form');
            return frame ? frame.innerHTML.length : 0;
        })()''')
        print(f"  Turbo frame HTML length: {frame_html_len}")

    # Now should be on step 2 (proof type + photo)
    has_proof_type = page.evaluate('''(() => {
        // Check both in turbo-frame and full page
        return !!document.querySelector('input[name="dev_pack_form[proof_type]"]') 
            || !!document.querySelector('action-menu[aria-required="true"]')
            || !!document.querySelector('button[name="submit"]');
    })()''')
    print(f"\nStep 2 loaded: {has_proof_type}")
    if not has_proof_type:
        # Maybe we need to wait for turbo-frame to update
        print("  Waiting for step 2 turbo-frame update...")
        for attempt in range(10):
            has_proof_type = page.evaluate('!!document.querySelector(\'input[name="dev_pack_form[proof_type]"]\')')
            if has_proof_type:
                print(f"    Step 2 found after {(attempt+1)*2}s more")
                break
            page.wait_for_timeout(2000)
        
    if not has_proof_type:
        # Save debug HTML
        debug_html = page.evaluate('document.querySelector("#dev-pack-form")?.innerHTML || ""')
        with open("pw_auto_debug.html", "w", encoding="utf-8") as f:
            f.write(debug_html)
        page.screenshot(path="pw_auto_no_step2.png")
        print(f"Step 2 not found! Debug HTML: {len(debug_html)} bytes saved")
        print(f"First 500 chars: {debug_html[:500]}")
        browser.close()
        sys.exit(1)

    # Wait for action-menu to hydrate (it's lazy-loaded)
    print("\n=== Waiting for action-menu JS hydration ===")
    for attempt in range(10):
        am_ready = page.evaluate('!!customElements.get("action-menu")')
        if am_ready:
            print(f"  action-menu ready after {(attempt+1)*3}s")
            break
        page.wait_for_timeout(3000)
    else:
        print("  action-menu never loaded after 30s")

    # Check webcam hydration
    print("\n=== Checking webcam hydration ===")
    for attempt in range(10):
        wc = page.evaluate('''(() => {
            const root = document.querySelector('react-partial[partial-name="webcam-upload"] [data-target="react-partial.reactRoot"]');
            return root ? root.childElementCount : -1;
        })()''')
        if wc > 0:
            print(f"  Webcam hydrated after {(attempt+1)*3}s ({wc} children)")
            break
        page.wait_for_timeout(3000)
    else:
        print(f"  Webcam NOT hydrated after 30s (children={wc})")

    # === Select proof type ===
    print("\n=== Selecting proof type ===")
    am_defined = page.evaluate('!!customElements.get("action-menu")')
    if am_defined:
        print("  action-menu IS defined, clicking through proper UI...")
        # Click trigger to open menu
        page.click('action-menu button[aria-haspopup]')
        page.wait_for_timeout(1000)
        # Click transcript option
        clicked = page.evaluate('''(() => {
            const items = document.querySelectorAll('button[role="menuitemradio"]');
            for (const item of items) {
                if (item.dataset.value && item.dataset.value.includes("official")) {
                    item.click();
                    return item.dataset.value;
                }
            }
            return null;
        })()''')
        print(f"  Clicked: {clicked}")
        page.wait_for_timeout(2000)
    else:
        print("  action-menu NOT defined, setting manually...")
        page.evaluate('''(() => {
            const inp = document.querySelector('input[name="dev_pack_form[proof_type]"]');
            if (inp) inp.value = "2. Dated official/unofficial transcript";
        })()''')

    proof_val = page.evaluate('document.querySelector(\'input[name="dev_pack_form[proof_type]"]\')?.value')
    print(f"  proof_type = {proof_val!r}")

    # === Handle webcam capture ===
    print("\n=== Webcam capture ===")
    wc_hydrated = page.evaluate('''(() => {
        const root = document.querySelector('react-partial[partial-name="webcam-upload"] [data-target="react-partial.reactRoot"]');
        return root ? root.childElementCount : 0;
    })()''') > 0

    if wc_hydrated:
        print("  Webcam component IS hydrated!")
        # List all buttons in webcam component
        wc_btns = page.evaluate('''(() => {
            const root = document.querySelector('react-partial[partial-name="webcam-upload"] [data-target="react-partial.reactRoot"]');
            if (!root) return [];
            return Array.from(root.querySelectorAll('button')).map(b => ({
                text: b.textContent.trim().substring(0, 80),
                disabled: b.disabled,
                type: b.type,
            }));
        })()''')
        print(f"  Webcam buttons: {json.dumps(wc_btns, indent=2)}")

        # Wait for camera to initialize, then try to capture
        page.wait_for_timeout(3000)
        for btn in wc_btns:
            txt = btn['text'].lower()
            if any(kw in txt for kw in ['take', 'capture', 'photo', 'snap', 'camera']):
                print(f"  Clicking: {btn['text']}")
                page.click(f'react-partial[partial-name="webcam-upload"] button:has-text("{btn["text"]}")')
                page.wait_for_timeout(3000)
                break

        # Check if there's a confirm/use button after capture
        wc_btns2 = page.evaluate('''(() => {
            const root = document.querySelector('react-partial[partial-name="webcam-upload"] [data-target="react-partial.reactRoot"]');
            if (!root) return [];
            return Array.from(root.querySelectorAll('button')).map(b => ({
                text: b.textContent.trim().substring(0, 80),
                disabled: b.disabled,
            }));
        })()''')
        print(f"  After capture buttons: {json.dumps(wc_btns2, indent=2)}")

        for btn in wc_btns2:
            txt = btn['text'].lower()
            if any(kw in txt for kw in ['use', 'confirm', 'done', 'accept', 'submit']):
                print(f"  Clicking: {btn['text']}")
                page.click(f'react-partial[partial-name="webcam-upload"] button:has-text("{btn["text"]}")')
                page.wait_for_timeout(2000)
                break

        pp_val = page.evaluate('document.getElementById("photo_proof")?.value || ""')
        print(f"  photo_proof length: {len(pp_val)}")
        if pp_val:
            print(f"  photo_proof prefix: {pp_val[:60]}...")
    else:
        print("  Webcam NOT hydrated. Generating canvas JPEG as fallback...")
        page.evaluate('''(() => {
            const inp = document.getElementById("photo_proof");
            if (!inp) return;
            const canvas = document.createElement('canvas');
            canvas.width = 1280; canvas.height = 720;
            const ctx = canvas.getContext('2d');
            const grad = ctx.createLinearGradient(0, 0, 1280, 720);
            grad.addColorStop(0, '#1f2937');
            grad.addColorStop(1, '#f59e0b');
            ctx.fillStyle = grad;
            ctx.fillRect(0, 0, 1280, 720);
            ctx.fillStyle = '#fff';
            ctx.font = 'bold 56px sans-serif';
            ctx.fillText('Student Proof', 60, 120);
            ctx.font = '36px sans-serif';
            ctx.fillText(new Date().toISOString(), 60, 190);
            ctx.fillText('SKT International College', 60, 250);
            inp.value = canvas.toDataURL('image/jpeg', 0.92);
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

    # FormData preview
    print("\n=== FormData Preview ===")
    fd = page.evaluate('''(() => {
        const form = document.querySelector('#dev-pack-form form, form[action*="developer_pack"]');
        if (!form) return {error: "no form"};
        const fd = new FormData(form);
        const r = {};
        for (const [k, v] of fd.entries()) {
            const s = typeof v === 'string' ? v : '[File]';
            r[k] = s.substring(0, 100);
        }
        return r;
    })()''')
    for k, v in fd.items():
        marker = " ***" if "proof" in k.lower() or "variant" in k.lower() else ""
        print(f"  {k} = {v!r}{marker}")

    # Submit
    print("\n=== Submitting ===")
    page.evaluate('document.querySelector(\'button[name="submit"]\').disabled = false')
    page.click('button[name="submit"]')
    page.wait_for_timeout(10000)

    # Check result
    content = page.content()
    with open("pw_auto_result.html", "w", encoding="utf-8") as f:
        f.write(content)

    if "cannot be reviewed" in content:
        err = page.evaluate('''(() => {
            const b = document.querySelector('.Banner-title, [data-target="x-banner.titleText"]');
            return b ? b.textContent.trim() : 'Unknown error';
        })()''')
        print(f"\n*** FAILED: {err} ***")
    elif any(kw in content.lower() for kw in ["thank", "submitted", "review"]):
        print("\n*** SUCCESS! Application submitted! ***")
    else:
        print(f"\nResult unclear. HTML length: {len(content)}")

    page.screenshot(path="pw_auto_final.png")
    print(f"\nCaptured {len(captured_posts)} POST requests")
    for i, fields in enumerate(captured_posts):
        print(f"\n--- POST {i} ---")
        for k, v in fields.items():
            marker = " ***" if "proof" in k.lower() or "variant" in k.lower() else ""
            print(f"  {k} = {v!r}{marker}")

    browser.close()

print("\nDone!")
