"""Playwright: Focus on step 2 action-menu hidden input behavior."""
import os, time, json
from dotenv import load_dotenv
from client import GitHubClient
from playwright.sync_api import sync_playwright
load_dotenv()

# Use requests for step 1 (already working), then open step 2 in browser
c = GitHubClient()
ok = c.login(os.environ['GITHUB_USERNAME'], os.environ['GITHUB_PASSWORD'], totp_secret="SFDHLAA7MDH2S7TN")
print(f"Login: {ok}")
time.sleep(2)

# Do step 1 via requests (this works)
from bs4 import BeautifulSoup
resp0 = c.get("/settings/education/developer_pack_applications/new")
soup0 = BeautifulSoup(resp0.text, "html.parser")
frame = soup0.find("turbo-frame", id="dev-pack-form")
form0 = frame.find("form")
token0 = form0.find("input", attrs={"name": "authenticity_token"})["value"]
time.sleep(2)

step1_data = {
    "authenticity_token": token0,
    "dev_pack_form[application_type]": "student",
    "dev_pack_form[school_name]": "SKT International College",
    "dev_pack_form[school_email]": "thawkhant.1280@gmail.com",
    "dev_pack_form[latitude]": "16.8661",
    "dev_pack_form[longitude]": "96.1951",
    "dev_pack_form[location_shared]": "true",
    "dev_pack_form[form_variant]": "initial_form",
    "dev_pack_form[browser_location]": "",
    "dev_pack_form[utm_source]": "",
    "dev_pack_form[utm_content]": "",
    "continue": "Continue",
}

resp1 = c.session.post(
    "https://github.com/settings/education/developer_pack_applications",
    data=step1_data,
    headers={
        "Accept": "text/vnd.turbo-stream.html, text/html, application/xhtml+xml",
        "Turbo-Frame": "dev-pack-form",
    },
)
print(f"Step 1: {resp1.status_code}, has_proof={'proof_type' in resp1.text}")

if "proof_type" not in resp1.text:
    print("Step 1 failed. Cannot continue.")
    exit(1)

# Extract step 2 form HTML
step2_html = resp1.text
print(f"Step 2 HTML: {len(step2_html)} bytes")

# Now open FULL page in Playwright to analyze JS behavior
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
    
    # Collect JS errors
    errors = []
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    
    # Navigate to education page (loads all JS bundles)
    print("\nLoading education page in browser...")
    page.goto("https://github.com/settings/education/developer_pack_applications/new", timeout=30000)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(3000)  # Extra wait for JS initialization
    
    # Inject the step 2 form HTML into the turbo-frame
    print("Injecting step 2 form into turbo-frame...")
    # We need to inject the template content from the turbo-stream
    soup_step2 = BeautifulSoup(step2_html, "html.parser")
    template = soup_step2.find("template")
    if template:
        form_html = template.decode_contents()
    else:
        form_html = step2_html
    
    # Escape the HTML for JS injection
    import json as json_mod
    escaped_html = json_mod.dumps(form_html)
    
    page.evaluate(f'''
        const frame = document.querySelector("turbo-frame#dev-pack-form");
        if (frame) {{
            frame.innerHTML = {escaped_html};
        }}
    ''')
    page.wait_for_timeout(3000)  # Wait for custom elements to initialize
    
    # Now investigate the action-menu
    print("\n=== Action-Menu Investigation ===")
    
    info = page.evaluate('''(() => {
        const am = document.querySelector('action-menu');
        const al = document.querySelector('action-list');
        const hiddenInput = document.querySelector('input[name="dev_pack_form[proof_type]"]');
        const allProofInputs = Array.from(document.querySelectorAll('[name*="proof_type"]'));
        
        return {
            actionMenuDefined: !!customElements.get('action-menu'),
            actionListDefined: !!customElements.get('action-list'),
            actionMenuTag: am ? am.constructor.name : 'NOT FOUND',
            actionListTag: al ? al.constructor.name : 'NOT FOUND',
            hiddenInputExists: !!hiddenInput,
            hiddenInputValue: hiddenInput?.value ?? 'N/A',
            proofInputCount: allProofInputs.length,
            proofInputs: allProofInputs.map(i => ({
                tag: i.tagName, type: i.type, name: i.name, value: i.value, id: i.id,
            })),
            selectVariant: am?.getAttribute('data-select-variant') ?? 'N/A',
            menuItemCount: document.querySelectorAll('button[role="menuitemradio"]').length,
        };
    })()''')
    print(json.dumps(info, indent=2))
    
    # Try clicking the action-menu trigger
    print("\n=== Clicking trigger button ===")
    page.evaluate('''(() => {
        const trigger = document.querySelector('action-menu button[aria-haspopup]');
        if (trigger) trigger.click();
    })()''')
    page.wait_for_timeout(1000)
    
    # Check if popover opened
    popover_state = page.evaluate('''(() => {
        const ap = document.querySelector('action-menu anchored-position[popover]');
        if (!ap) return {exists: false};
        try {
            return {
                exists: true,
                popoverState: ap.getAttribute('popover'),
                isOpen: ap.matches(':popover-open'),
                display: getComputedStyle(ap).display,
            };
        } catch(e) {
            return {exists: true, error: e.message};
        }
    })()''')
    print(f"Popover: {json.dumps(popover_state, indent=2)}")
    
    # Now click the menu item
    print("\n=== Clicking menu item ===")
    click_result = page.evaluate('''(() => {
        const items = document.querySelectorAll('button[role="menuitemradio"]');
        let target = null;
        for (const item of items) {
            if (item.dataset.value && item.dataset.value.includes("official")) {
                target = item;
                break;
            }
        }
        if (!target) return {found: false};
        
        // Record value before
        const inp = document.querySelector('input[name="dev_pack_form[proof_type]"]');
        const before = inp?.value ?? 'N/A';
        
        // Click the item
        target.click();
        
        // Record value after
        const after = inp?.value ?? 'N/A';
        
        return {
            found: true,
            dataValue: target.dataset.value,
            valueBefore: before,
            valueAfter: after,
            ariaChecked: target.getAttribute('aria-checked'),
        };
    })()''')
    print(json.dumps(click_result, indent=2))
    
    # Wait and check again
    page.wait_for_timeout(2000)
    
    delayed_val = page.evaluate('''(() => {
        return document.querySelector('input[name="dev_pack_form[proof_type]"]')?.value ?? 'N/A';
    })()''')
    print(f"Delayed proof_type value: {delayed_val!r}")
    
    # Check if action-list has a selectItem method or similar
    print("\n=== Action-list API ===")
    api_info = page.evaluate('''(() => {
        const al = document.querySelector('action-list');
        if (!al) return {exists: false};
        
        // Get all methods/properties
        const proto = Object.getPrototypeOf(al);
        const ownMethods = Object.getOwnPropertyNames(proto).filter(p => typeof proto[p] === 'function');
        const ownProps = Object.getOwnPropertyNames(proto).filter(p => typeof proto[p] !== 'function');
        
        // Also check if it has internals
        const hasInternals = !!al.attachInternals;
        
        return {
            exists: true,
            constructorName: al.constructor.name,
            methods: ownMethods,
            properties: ownProps,
            hasAttachInternals: hasInternals,
        };
    })()''')
    print(json.dumps(api_info, indent=2))
    
    # Try to use action-list's own selection mechanism
    print("\n=== Trying action-list selection API ===")
    api_result = page.evaluate('''(() => {
        const al = document.querySelector('action-list');
        const am = document.querySelector('action-menu');
        if (!al) return {error: "no action-list"};
        
        // Try various selection approaches
        const results = {};
        
        // Check if selectItem exists
        if (typeof al.selectItem === 'function') {
            results.hasSelectItem = true;
        }
        
        // Check if there's a 'select' or 'change' event handler
        // Try dispatching an activation event
        const target = document.querySelector('button[data-value="2. Dated official/unofficial transcript"]');
        if (target) {
            // Dispatch activation event 
            target.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true}));
            
            const val1 = document.querySelector('input[name="dev_pack_form[proof_type]"]')?.value;
            results.afterDispatch = val1;
            
            // Try the GitHub primer specific event
            target.dispatchEvent(new CustomEvent('action-list-item-select', {
                bubbles: true,
                detail: {value: target.dataset.value},
            }));
            
            const val2 = document.querySelector('input[name="dev_pack_form[proof_type]"]')?.value;
            results.afterCustomEvent = val2;
        }
        
        // Manually set value and check FormData
        const inp = document.querySelector('input[name="dev_pack_form[proof_type]"]');
        if (inp) {
            inp.value = "2. Dated official/unofficial transcript";
            results.manuallySet = inp.value;
        }
        
        // Create FormData and check what it contains for proof_type
        const form = document.querySelector('form[action*="developer_pack"]');
        if (form) {
            const fd = new FormData(form);
            const proofValues = fd.getAll('dev_pack_form[proof_type]');
            results.formDataProofType = proofValues;
            
            // Check all entries
            const all = {};
            for (const [k, v] of fd.entries()) {
                if (k.includes('proof') || k.includes('variant')) {
                    all[k] = all[k] ? all[k] + ' | ' + v : (typeof v === 'string' ? v : '[File]');
                }
            }
            results.formDataImportant = all;
        }
        
        return results;
    })()''')
    print(json.dumps(api_result, indent=2))
    
    # JS errors
    if errors:
        print(f"\n=== JS Errors ({len(errors)}) ===")
        for e in errors[:10]:
            print(f"  {e[:200]}")
    
    browser.close()

print("\nDone!")
