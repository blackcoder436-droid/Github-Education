"""Diagnose why GitHub JS doesn't hydrate in Playwright, then attempt full auto flow."""
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

    # Collect diagnostics
    console_msgs = []
    page.on("console", lambda msg: console_msgs.append(f"[{msg.type}] {msg.text[:300]}"))

    js_loaded = []
    js_failed = []
    def on_response(resp):
        url = resp.url
        if url.endswith('.js') and 'githubassets' in url:
            name = url.split('/')[-1][:80]
            if resp.status == 200:
                js_loaded.append(name)
            else:
                js_failed.append(f"[{resp.status}] {name}")
    page.on("response", on_response)

    # Navigate
    print("\n=== Step 0: Navigate to education page ===")
    page.goto(
        "https://github.com/settings/education/developer_pack_applications/new",
        timeout=60000, wait_until="networkidle",
    )
    # Wait generously for JS to execute
    page.wait_for_timeout(20000)

    # --- DIAGNOSTICS ---
    print(f"\nJS bundles loaded: {len(js_loaded)}")
    for name in js_loaded[:5]:
        print(f"  {name}")
    if len(js_loaded) > 5:
        print(f"  ... +{len(js_loaded)-5} more")
    if js_failed:
        print(f"JS bundles FAILED: {len(js_failed)}")
        for f in js_failed:
            print(f"  {f}")

    # Custom element check
    ce_check = page.evaluate('''(() => {
        const names = [
            'react-partial', 'action-menu', 'action-list',
            'turbo-frame', 'focus-group', 'file-attachment',
            'anchored-position', 'tool-tip',
        ];
        const result = {};
        for (const n of names) result[n] = !!customElements.get(n);
        return result;
    })()''')
    print("\nCustom elements:")
    for k, v in ce_check.items():
        print(f"  {k}: {'YES' if v else 'NO'}")

    # React partials
    rp_check = page.evaluate('''(() => {
        const partials = document.querySelectorAll('react-partial');
        return Array.from(partials).map(p => ({
            name: p.getAttribute('partial-name'),
            children: p.querySelector('[data-target="react-partial.reactRoot"]')?.childElementCount || 0,
        }));
    })()''')
    print("\nReact partials on page:")
    for rp in rp_check:
        status = 'HYDRATED' if rp['children'] > 0 else 'empty'
        print(f"  {rp['name']}: {status} ({rp['children']} children)")

    # Console errors
    errors = [m for m in console_msgs if m.startswith('[error')]
    if errors:
        print(f"\nConsole errors ({len(errors)}):")
        for e in errors[:15]:
            print(f"  {e[:200]}")
    else:
        print(f"\nNo console errors (total msgs: {len(console_msgs)})")

    # Turbo frame check
    tf_check = page.evaluate('''(() => {
        const frames = document.querySelectorAll('turbo-frame');
        return Array.from(frames).map(f => ({
            id: f.id,
            src: f.getAttribute('src') || '',
            loaded: f.getAttribute('complete') || f.getAttribute('busy') || 'unknown',
            childCount: f.childElementCount,
        }));
    })()''')
    print(f"\nTurbo frames: {len(tf_check)}")
    for tf in tf_check:
        print(f"  #{tf['id']}: children={tf['childCount']}")

    # === STEP 1: Fill and submit ===
    print("\n\n=== Step 1: Fill initial form ===")

    # Check if school autocomplete works (react-partial hydrated?)
    school_input = page.query_selector('#js-school-name-search')
    if school_input:
        school_input.focus()
        school_input.type("SKT International College", delay=30)
        page.wait_for_timeout(5000)

        ac_count = page.evaluate('''(() => {
            const list = document.querySelector('#js-school-name-list');
            if (!list) return 0;
            return list.querySelectorAll('[role="option"], li').length;
        })()''')
        print(f"Autocomplete results: {ac_count}")

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
            # Manual fallback
            page.evaluate('''(() => {
                document.querySelectorAll('input[name="dev_pack_form[school_name]"]').forEach(i => i.value = "SKT International College");
            })()''')
    else:
        print("School input not found, setting manually")
        page.evaluate('document.querySelectorAll(\'input[name="dev_pack_form[school_name]"]\').forEach(i => i.value = "SKT International College")')

    # Student radio
    page.evaluate('document.querySelector(\'input[value="student"]\')?.click()')
    page.wait_for_timeout(500)

    # Location
    page.evaluate('''(() => {
        const s = (sel, val) => { const e = document.querySelector(sel); if(e) e.value = val; };
        s('#js-developer-pack-application-latitude-input, #dev_pack_form_latitude', '16.8661');
        s('#js-developer-pack-application-longitude-input, #dev_pack_form_longitude', '96.1951');
        s('#js-developer-pack-application-location-shared-input, #dev_pack_form_location_shared', 'true');
    })()''')

    # Enable + click Continue
    page.evaluate('document.querySelector(\'button[name="continue"]\').disabled = false')
    page.wait_for_timeout(500)
    print("Clicking Continue...")
    page.click('button[name="continue"]')
    page.wait_for_timeout(10000)

    # Check step 2 loaded
    has_step2 = page.evaluate('!!document.querySelector(\'input[name="dev_pack_form[proof_type]"]\')')
    print(f"Step 2 loaded: {has_step2}")
    if not has_step2:
        page.screenshot(path="pw_diag_no_step2.png")
        print("Step 2 not found! Screenshot saved.")
        browser.close()
        sys.exit(1)

    # Wait EXTRA long for lazy JS to load after Turbo frame update
    print("Waiting 30s for JS hydration after step 2...")
    for i in range(6):
        page.wait_for_timeout(5000)
        am = page.evaluate('!!customElements.get("action-menu")')
        rp_wc = page.evaluate('''(() => {
            const root = document.querySelector('react-partial[partial-name="webcam-upload"] [data-target="react-partial.reactRoot"]');
            return root ? root.childElementCount : -1;
        })()''')
        if am and rp_wc > 0:
            print(f"  [{(i+1)*5}s] action-menu: YES, webcam hydrated: {rp_wc} children -> READY!")
            break
        print(f"  [{(i+1)*5}s] action-menu: {am}, webcam children: {rp_wc}")

    # Final diagnostic
    am_defined = page.evaluate('!!customElements.get("action-menu")')
    rp_defined = page.evaluate('!!customElements.get("react-partial")')
    wc_children = page.evaluate('''(() => {
        const root = document.querySelector('react-partial[partial-name="webcam-upload"] [data-target="react-partial.reactRoot"]');
        return root ? root.childElementCount : -1;
    })()''')
    print(f"\nFinal state: react-partial={rp_defined}, action-menu={am_defined}, webcam_children={wc_children}")

    if wc_children > 0:
        print("\n=== Webcam component HYDRATED! Attempting capture... ===")
        # Look for capture/take photo button inside the webcam component
        wc_buttons = page.evaluate('''(() => {
            const root = document.querySelector('react-partial[partial-name="webcam-upload"] [data-target="react-partial.reactRoot"]');
            if (!root) return [];
            const btns = root.querySelectorAll('button');
            return Array.from(btns).map(b => ({
                text: b.textContent.trim().substring(0, 80),
                class: b.className.substring(0, 80),
                disabled: b.disabled,
            }));
        })()''')
        print(f"Webcam buttons: {json.dumps(wc_buttons, indent=2)}")
        # Try clicking capture
        for btn in wc_buttons:
            if any(kw in btn['text'].lower() for kw in ['take', 'capture', 'photo', 'snap']):
                page.click(f'text="{btn["text"]}"')
                print(f"Clicked: {btn['text']}")
                page.wait_for_timeout(3000)
                break

        # Check if photo_proof was set
        pp_val = page.evaluate('document.getElementById("photo_proof")?.value')
        pp_len = len(pp_val) if pp_val else 0
        print(f"photo_proof value length: {pp_len}")
        if pp_len > 100:
            print(f"photo_proof prefix: {pp_val[:60]}...")
    else:
        print("\n=== Webcam NOT hydrated. Checking what JS loaded post-step2... ===")
        print(f"Total JS bundles now: {len(js_loaded)}")
        # Check for lazy-loaded chunks after step 2
        lazy_chunks = [n for n in js_loaded if 'lazy' in n.lower() or 'webcam' in n.lower() or 'react-partial' in n.lower()]
        print(f"Lazy/webcam chunks: {lazy_chunks}")

        # Check all custom elements again
        ce2 = page.evaluate('''(() => {
            const names = ['react-partial', 'action-menu', 'action-list', 'turbo-frame'];
            const result = {};
            for (const n of names) result[n] = !!customElements.get(n);
            return result;
        })()''')
        print(f"Custom elements now: {ce2}")

        # NEW: Check all react-partials hydration state
        rp2 = page.evaluate('''(() => {
            const partials = document.querySelectorAll('react-partial');
            return Array.from(partials).map(p => ({
                name: p.getAttribute('partial-name'),
                children: p.querySelector('[data-target="react-partial.reactRoot"]')?.childElementCount || 0,
            }));
        })()''')
        print(f"React partials now:")
        for rp in rp2:
            print(f"  {rp['name']}: {rp['children']} children")

    # New console errors after step 2?
    late_errors = [m for m in console_msgs if m.startswith('[error')]
    if len(late_errors) > len(errors):
        print(f"\nNew console errors after step 2:")
        for e in late_errors[len(errors):]:
            print(f"  {e[:200]}")

    page.screenshot(path="pw_diag_final.png")
    with open("pw_diag_page.html", "w", encoding="utf-8") as f:
        f.write(page.content())
    print("\nScreenshot and HTML saved.")
    browser.close()

print("\nDone!")
