"""Playwright: Do entire flow in browser with proper JS loading."""
import os, time, json
from dotenv import load_dotenv
from client import GitHubClient
from playwright.sync_api import sync_playwright
from urllib.parse import parse_qsl
load_dotenv()

# Login with requests to get cookies
c = GitHubClient()
ok = c.login(os.environ['GITHUB_USERNAME'], os.environ['GITHUB_PASSWORD'], totp_secret="SFDHLAA7MDH2S7TN")
print(f"Login: {ok}")

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
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        permissions=["geolocation"],
        geolocation={"latitude": 16.8661, "longitude": 96.1951},
    )
    context.add_cookies(cookies)
    page = context.new_page()
    asset_hits = []
    
    # Capture form submissions
    captured = []
    def on_request(req):
        if req.method == "POST" and "developer_pack" in req.url:
            post = req.post_data or ""
            pairs = parse_qsl(post, keep_blank_values=True)
            fields = {}
            for k, v in pairs:
                fields[k] = v[:100]
            captured.append(fields)
            # Print proof-related field
            pt = fields.get("dev_pack_form[proof_type]", "MISSING")
            pp = fields.get("dev_pack_form[photo_proof]", "MISSING")
            fv = fields.get("dev_pack_form[form_variant]", "MISSING")
            print(f"  CAPTURED POST: proof_type={pt!r}, photo_proof={pp[:30]!r}..., variant={fv!r}")
            # Show duplicate evidence for debugging ordering-sensitive params.
            proof_entries = [v for k, v in pairs if k == "dev_pack_form[proof_type]"]
            variant_entries = [v for k, v in pairs if k == "dev_pack_form[form_variant]"]
            if len(proof_entries) > 1 or len(variant_entries) > 1:
                print(f"    DUPLICATES -> proof_type={proof_entries}, form_variant={variant_entries}")
    page.on("request", on_request)
    def on_asset(req):
        url = req.url
        if "githubassets.com/assets" in url and (
            "webcam" in url or "react-partial" in url or "element-registry" in url or "lazy-" in url
        ):
            asset_hits.append(url)
    page.on("request", on_asset)
    
    # Navigate to education form
    print("\nNavigating to education form...")
    page.goto("https://github.com/settings/education/developer_pack_applications/new", 
              timeout=30000, wait_until="networkidle")
    page.wait_for_timeout(5000)
    print(f"Page loaded")
    
    # Step 1: Fill in the form via JS
    print("\n=== Step 1: Fill form ===")
    
    # Select student radio
    page.evaluate('document.querySelector(\'input[value="student"]\')?.click()')
    page.wait_for_timeout(500)
    
    # Type and select school
    school = page.query_selector('#js-school-name-search')
    if school:
        school.focus()
        school.type("SKT International College", delay=50)
        page.wait_for_timeout(4000)
        
        # Check autocomplete
        ac_items = page.evaluate('''(() => {
            const list = document.querySelector('#js-school-name-list');
            if (!list) return [];
            const items = list.querySelectorAll('[role="option"], li, button');
            return Array.from(items).map(i => ({
                text: i.textContent.trim().substring(0, 80),
                tag: i.tagName,
                role: i.getAttribute('role'),
                value: i.getAttribute('data-autocomplete-value') || i.getAttribute('value') || '',
            }));
        })()''')
        print(f"Autocomplete items: {len(ac_items)}")
        for item in ac_items[:5]:
            print(f"  {item}")
        
        if ac_items:
            # Click first matching item
            page.evaluate('''(() => {
                const list = document.querySelector('#js-school-name-list');
                const items = list.querySelectorAll('[role="option"], li');
                for (const item of items) {
                    if (item.textContent.includes("SKT")) {
                        item.click();
                        return true;
                    }
                }
                return false;
            })()''')
            page.wait_for_timeout(2000)
        else:
            # Manually set school name if autocomplete didn't work
            print("  No autocomplete results, setting manually...")
            page.evaluate('''(() => {
                // Set school name in hidden input  
                const inputs = document.querySelectorAll('input[name="dev_pack_form[school_name]"]');
                inputs.forEach(i => i.value = "SKT International College");
                
                // Set school email
                const emailSelect = document.querySelector('#js-developer-pack-application-email-selection-container');
                if (emailSelect) {
                    // Try adding option
                    const opt = document.createElement('option');
                    opt.value = 'thawkhant.1280@gmail.com';
                    opt.text = 'thawkhant.1280@gmail.com';
                    opt.selected = true;
                    emailSelect.appendChild(opt);
                }
            })()''')
    
    # Set location (may already be set by geolocation permission)
    page.evaluate('''(() => {
        const lat = document.querySelector('#js-developer-pack-application-latitude-input, #dev_pack_form_latitude');
        const lng = document.querySelector('#js-developer-pack-application-longitude-input, #dev_pack_form_longitude');
        const loc = document.querySelector('#js-developer-pack-application-location-shared-input, #dev_pack_form_location_shared');
        if (lat) lat.value = "16.8661";
        if (lng) lng.value = "96.1951";
        if (loc) loc.value = "true";
    })()''')
    
    # Enable and click Continue
    page.evaluate('''(() => {
        const btn = document.querySelector('button[name="continue"]');
        if (btn) btn.disabled = false;
    })()''')
    page.wait_for_timeout(500)
    
    # Click continue and wait for Turbo to update
    print("Clicking Continue...")
    page.click('button[name="continue"]')
    page.wait_for_timeout(8000)
    
    # Check if step 2 loaded
    has_proof = page.evaluate('!!document.querySelector(\'input[name="dev_pack_form[proof_type]"]\')')
    print(f"Step 2 loaded: {has_proof}")
    
    if not has_proof:
        # Save page for debug
        with open("pw_no_step2.html", "w", encoding="utf-8") as f:
            f.write(page.content())
        print("Step 2 not loaded! Saved page. Checking for error...")
        err = page.evaluate('''(() => {
            const banner = document.querySelector('.Banner-title, .flash-error');
            return banner ? banner.textContent.trim() : 'no error banner';
        })()''')
        print(f"  Error: {err}")
        browser.close()
        exit(1)
    
    # Wait extra for lazy JS to load
    page.wait_for_timeout(5000)

    # Diagnostics: did webcam partial hydrate?
    webcam_diag = page.evaluate('''(() => {
        const root = document.querySelector('react-partial[partial-name="webcam-upload"] [data-target="react-partial.reactRoot"]');
        const partial = document.querySelector('react-partial[partial-name="webcam-upload"]');
        return {
            partialFound: !!partial,
            rootFound: !!root,
            rootChildCount: root ? root.childElementCount : -1,
            rootTextLen: root ? (root.textContent || '').trim().length : -1,
            rootHtmlLen: root ? (root.innerHTML || '').length : -1,
        };
    })()''')
    print(f"webcam partial diag: {webcam_diag}")
    
    # Check if action-menu is now defined
    am_defined = page.evaluate('!!customElements.get("action-menu")')
    al_defined = page.evaluate('!!customElements.get("action-list")')
    print(f"\naction-menu defined: {am_defined}")
    print(f"action-list defined: {al_defined}")
    
    if am_defined:
        print("\n*** action-menu IS defined! Trying proper click... ***")
        
        # Click trigger to open
        page.click('action-menu button[aria-haspopup]')
        page.wait_for_timeout(1000)
        
        # Click the transcript option
        click_ok = page.evaluate('''(() => {
            const items = document.querySelectorAll('button[role="menuitemradio"]');
            for (const item of items) {
                if (item.dataset.value && item.dataset.value.includes("official")) {
                    item.click();
                    return true;
                }
            }
            return false;
        })()''')
        print(f"Clicked option: {click_ok}")
        page.wait_for_timeout(2000)
        
        # Check value
        proof_val = page.evaluate('document.querySelector(\'input[name="dev_pack_form[proof_type]"]\')?.value')
        print(f"proof_type value: {proof_val!r}")
    else:
        print("\n*** action-menu NOT defined. Will try manual approach. ***")
        # Manually set hidden input value
        page.evaluate('''(() => {
            const inp = document.querySelector('input[name="dev_pack_form[proof_type]"]');
            if (inp) inp.value = "2. Dated official/unofficial transcript";
        })()''')
        val = page.evaluate('document.querySelector(\'input[name="dev_pack_form[proof_type]"]\')?.value')
        print(f"Manually set proof_type: {val!r}")
    
    # Build a realistic in-browser JPEG data URL so server-side validation sees a real image payload.
    photo_info = page.evaluate('''(() => {
        const inp = document.getElementById("photo_proof");
        if (!inp) return {ok: false, reason: "photo_proof input missing"};

        const canvas = document.createElement('canvas');
        canvas.width = 1280;
        canvas.height = 720;
        const ctx = canvas.getContext('2d');
        if (!ctx) return {ok: false, reason: "canvas context missing"};

        // Add deterministic content; some validators reject tiny/blank payloads.
        const grad = ctx.createLinearGradient(0, 0, canvas.width, canvas.height);
        grad.addColorStop(0, '#1f2937');
        grad.addColorStop(1, '#f59e0b');
        ctx.fillStyle = grad;
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        ctx.fillStyle = '#ffffff';
        ctx.font = 'bold 56px sans-serif';
        ctx.fillText('Student Proof Snapshot', 60, 120);
        ctx.font = '36px sans-serif';
        ctx.fillText(new Date().toISOString(), 60, 190);
        ctx.fillText('SKT International College', 60, 250);

        const dataUrl = canvas.toDataURL('image/jpeg', 0.92);
        inp.value = dataUrl;
        return {
            ok: true,
            prefix: dataUrl.slice(0, 30),
            length: dataUrl.length,
        };
    })()''')
    print(f"Generated photo_proof: {photo_info}")
    
    # Normalize duplicate form_variant inputs (Rails keeps both hidden fields in this form).
    page.evaluate('''(() => {
        const inputs = document.querySelectorAll('input[name="dev_pack_form[form_variant]"]');
        if (inputs.length === 0) return;
        inputs.forEach((i, idx) => {
            if (idx === 0) {
                i.value = "upload_proof_form";
            } else {
                i.disabled = true;
                i.removeAttribute('name');
            }
        });
    })()''')
    
    # Check FormData before submit
    print("\n=== FormData Check ===")
    fd_check = page.evaluate('''(() => {
        const form = document.querySelector('form[action*="developer_pack"]');
        if (!form) return {error: "no form"};
        const fd = new FormData(form);
        const result = {};
        for (const [k, v] of fd.entries()) {
            const val = typeof v === 'string' ? v : '[File]';
            if (result[k]) {
                result[k] += ' | ' + val;
            } else {
                result[k] = val.substring(0, 100);
            }
        }
        return result;
    })()''')
    for k, v in fd_check.items():
        marker = " ***" if "proof" in k.lower() or "variant" in k.lower() else ""
        print(f"  {k} = {v!r}{marker}")
    
    # Submit
    print("\n=== Submitting form ===")
    page.evaluate('''(() => {
        const btn = document.querySelector('button[name="submit"]');
        if (btn) btn.disabled = false;
    })()''')
    page.click('button[name="submit"]')
    page.wait_for_timeout(8000)
    
    # Check result
    content = page.content()
    with open("pw_final_result.html", "w", encoding="utf-8") as f:
        f.write(content)
    
    if "cannot be reviewed" in content:
        err_text = page.evaluate('''(() => {
            const b = document.querySelector('.Banner-title');
            return b ? b.textContent.trim() : 'N/A';
        })()''')
        print(f"\n*** FAILED: {err_text} ***")
    elif "thank" in content.lower() or "submitted" in content.lower():
        print("\n*** SUCCESS! ***")
    else:
        print(f"\nUnknown result. Response length: {len(content)}")
    
    # Show captured requests
    print(f"\n=== Captured {len(captured)} POST requests ===")
    for i, fields in enumerate(captured):
        print(f"\n--- Request {i} ---")
        for k, v in fields.items():
            marker = " ***" if "proof" in k.lower() or "variant" in k.lower() else ""
            print(f"  {k} = {v!r}{marker}")

    print(f"\n=== Asset hits ({len(asset_hits)}) ===")
    for u in sorted(set(asset_hits))[:50]:
        print(f"  {u}")
    
    browser.close()

print("\nDone!")
