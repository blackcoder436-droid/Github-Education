"""Playwright: Deep investigation of action-menu component."""
import os, time, json
from dotenv import load_dotenv
from client import GitHubClient
from playwright.sync_api import sync_playwright
load_dotenv()

# Login with requests
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
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
    )
    context.add_cookies(cookies)
    page = context.new_page()
    
    # Collect console messages for JS errors
    console_msgs = []
    def on_console(msg):
        if msg.type in ("error", "warning"):
            console_msgs.append(f"[{msg.type}] {msg.text}")
    page.on("console", on_console)
    
    # Navigate
    print("Navigating...")
    page.goto("https://github.com/settings/education/developer_pack_applications/new", timeout=30000)
    page.wait_for_load_state("networkidle")
    print(f"Page loaded. Console errors: {len([m for m in console_msgs if 'error' in m.lower()])}")
    
    # Step 1: Fill form
    page.evaluate('''
        // Select student
        const radio = document.querySelector('input[value="student"]');
        if (radio) { radio.click(); radio.checked = true; }
        
        // Set location
        const lat = document.querySelector('#js-developer-pack-application-latitude-input');
        const lng = document.querySelector('#js-developer-pack-application-longitude-input');
        const loc = document.querySelector('#js-developer-pack-application-location-shared-input');
        if (lat) lat.value = "16.8661";
        if (lng) lng.value = "96.1951";
        if (loc) loc.value = "true";
    ''')
    
    # Type school name
    school = page.query_selector('#js-school-name-search')
    if school:
        school.click()
        school.fill("SKT International")
        page.wait_for_timeout(3000)
        
        # Try to find and click autocomplete result
        results = page.query_selector_all('[role="option"], .autocomplete-item, #js-school-name-list li')
        print(f"Autocomplete results: {len(results)}")
        for r in results:
            text = r.inner_text()
            print(f"  Result: {text[:60]}")
            if "SKT" in text.upper():
                r.click()
                page.wait_for_timeout(2000)
                break
        
        if not results:
            # Try getting the autocomplete list HTML
            list_html = page.evaluate('document.querySelector("#js-school-name-list")?.innerHTML || "NOT FOUND"')
            print(f"List HTML: {list_html[:200]}")
            
            # Maybe the autocomplete uses a different structure
            all_options = page.evaluate('''
                const items = document.querySelectorAll('[data-autocomplete-value], [data-value]');
                return Array.from(items).map(i => ({
                    tag: i.tagName,
                    text: i.textContent.trim().substring(0, 80),
                    value: i.dataset.autocompleteValue || i.dataset.value || '',
                }));
            ''')
            print(f"Data-value elements: {json.dumps(all_options[:5], indent=2)}")
    
    # Submit step 1
    page.evaluate('document.querySelector(\'button[name="continue"]\').disabled = false')
    page.wait_for_timeout(500)
    page.click('button[name="continue"]')
    page.wait_for_timeout(5000)
    
    # Check step 2
    has_step2 = page.evaluate('!!document.querySelector(\'input[name="dev_pack_form[proof_type]"]\')')
    print(f"\nStep 2 present: {has_step2}")
    
    if has_step2:
        # === DEEP INVESTIGATION OF ACTION-MENU ===
        print("\n=== Action-Menu Investigation ===")
        
        # Check if action-menu custom element is defined
        am_info = page.evaluate('''
            const am = document.querySelector('action-menu');
            const al = document.querySelector('action-list');
            return {
                actionMenuDefined: !!customElements.get('action-menu'),
                actionListDefined: !!customElements.get('action-list'),
                actionMenuExists: !!am,
                actionListExists: !!al,
                actionMenuConstructor: am?.constructor?.name || 'N/A',
                actionListConstructor: al?.constructor?.name || 'N/A',
                focusGroupDefined: !!customElements.get('focus-group'),
                proofTypeValue: document.querySelector('input[name="dev_pack_form[proof_type]"]')?.value || '',
                hiddenInputParent: document.querySelector('input[name="dev_pack_form[proof_type]"]')?.parentElement?.tagName || 'N/A',
                selectVariant: am?.getAttribute('data-select-variant') || 'N/A',
            };
        ''')
        print(f"  {json.dumps(am_info, indent=2)}")
        
        # Try clicking through the action-menu properly
        print("\nClicking action-menu trigger...")
        trigger = page.query_selector('action-menu button[aria-haspopup]')
        if trigger:
            trigger.click()
            page.wait_for_timeout(1000)
            
            # Check if overlay/popover is visible
            overlay_visible = page.evaluate('''
                const overlay = document.querySelector('action-menu anchored-position');
                const style = overlay ? window.getComputedStyle(overlay) : null;
                return {
                    exists: !!overlay,
                    display: style?.display || 'N/A',
                    visibility: style?.visibility || 'N/A',
                    popover: overlay?.getAttribute('popover') || 'N/A',
                    matches_open: overlay?.matches(':popover-open') || false,
                };
            ''')
            print(f"  Overlay: {json.dumps(overlay_visible, indent=2)}")
        
        # Try to select item using action-list's own API
        print("\nTrying to select via JS API...")
        select_result = page.evaluate('''
            // Method 1: Direct API
            const al = document.querySelector('action-list');
            const items = document.querySelectorAll('action-menu button[role="menuitemradio"]');
            const target = Array.from(items).find(b => b.dataset.value?.includes("official"));
            
            if (target) {
                // Try clicking with proper event dispatch
                target.click();
                
                // Check if value was set
                const val1 = document.querySelector('input[name="dev_pack_form[proof_type]"]')?.value;
                
                // Try setting aria-checked
                items.forEach(i => i.setAttribute('aria-checked', 'false'));
                target.setAttribute('aria-checked', 'true');
                
                // Try dispatching change event
                const hiddenInput = document.querySelector('[data-list-inputs] input, input[name="dev_pack_form[proof_type]"]');
                if (hiddenInput) {
                    hiddenInput.value = target.dataset.value;
                    hiddenInput.dispatchEvent(new Event('change', { bubbles: true }));
                    hiddenInput.dispatchEvent(new Event('input', { bubbles: true }));
                }
                
                const val2 = document.querySelector('input[name="dev_pack_form[proof_type]"]')?.value;
                
                return {
                    targetFound: true,
                    targetValue: target.dataset.value,
                    valueAfterClick: val1,
                    valueAfterManualSet: val2,
                    hiddenInputName: hiddenInput?.name || 'N/A',
                    allProofInputs: Array.from(document.querySelectorAll('[name*="proof_type"]')).map(i => ({
                        tag: i.tagName,
                        type: i.type,
                        name: i.name,
                        value: i.value,
                    })),
                };
            }
            return { targetFound: false };
        ''')
        print(f"  Select result: {json.dumps(select_result, indent=2)}")
        
        # Now check - does manually setting the value persist?
        proof_final = page.evaluate('document.querySelector(\'input[name="dev_pack_form[proof_type]"]\')?.value')
        print(f"\nFinal proof_type value: {proof_final!r}")
        
        # Let's also check the FormData that would be created
        print("\n=== FormData test ===")
        fd_result = page.evaluate('''
            const form = document.querySelector('form[action*="developer_pack"]');
            if (!form) return {error: "no form found"};
            
            const fd = new FormData(form);
            const entries = {};
            for (const [key, value] of fd.entries()) {
                if (key.includes("proof") || key.includes("variant") || key.includes("submit")) {
                    entries[key] = typeof value === 'string' ? value : `[File: ${value.name}]`;
                }
            }
            
            // Also list ALL entries
            const allEntries = {};
            for (const [key, value] of fd.entries()) {
                const v = typeof value === 'string' ? value : `[File: ${value.name}]`;
                if (allEntries[key]) {
                    allEntries[key] += ' | ' + v;
                } else {
                    allEntries[key] = v;
                }
            }
            
            return { important: entries, all: allEntries };
        ''')
        print(f"  FormData: {json.dumps(fd_result, indent=2)}")
    
    # Print console errors
    if console_msgs:
        print(f"\n=== Console errors/warnings ({len(console_msgs)}) ===")
        for msg in console_msgs[:20]:
            print(f"  {msg[:200]}")
    
    browser.close()

print("\nDone!")
