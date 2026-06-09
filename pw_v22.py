"""Education v22: Trigger the React autocomplete selection properly.
The React component reads data-selected-school-id when a result is clicked.
We need to trigger the proper event chain so the school_id gets stored."""
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

    page.goto("https://github.com/settings/education/developer_pack_applications/new", timeout=120000, wait_until="load")
    page.wait_for_timeout(8000)

    # === Step 1: Find what React does with school selection ===
    print("\n=== Investigate React component ===")
    react_info = page.evaluate('''async () => {
        const results = {};

        // Check if React partial rendered
        const partials = document.querySelectorAll('react-partial');
        results.partials = [];
        partials.forEach(p => {
            results.partials.push({
                name: p.getAttribute('partial-name'),
                ssr: p.getAttribute('data-ssr'),
                childCount: p.children.length,
                html: p.innerHTML.substring(0, 200),
            });
        });

        // Check for global state management
        results.hasReactRoot = !!document.querySelector('[data-reactroot]');

        // Look for any __NEXT_DATA__ or __INITIAL_STATE__
        results.globalKeys = Object.keys(window).filter(k =>
            k.includes('REACT') || k.includes('NEXT') || k.includes('INITIAL') ||
            k.includes('__app') || k.includes('school')
        ).slice(0, 20);

        // Fetch schools and inject into autocomplete
        const r = await fetch("/settings/education/developer_pack_applications/schools?q=University+of+Computer+Studies", {
            headers: {"Accept": "text/fragment+html"},
            credentials: "same-origin",
        });
        const schoolsHtml = await r.text();

        // Inject schools into dropdown
        const container = document.getElementById('js-school-name-list');
        if (container) {
            container.innerHTML = schoolsHtml;
            // Try to show the popover
            try { container.showPopover(); } catch(e) {}
        }

        // NOW try different event mechanisms to trigger React
        const searchInput = document.getElementById('js-school-name-search');
        const ucsy = container?.querySelector('[data-selected-school-id="7620"]');

        if (!ucsy) return {...results, error: "UCSY not found in dropdown"};

        // Method 1: Click the item (triggers js-school-autocomplete-result-selection class handler)
        results.clickAttempt = {};

        // Before clicking, monitor what happens
        const formBefore = {};
        document.querySelectorAll('input').forEach(el => {
            if (el.name && el.name.includes('school')) formBefore[el.name] = el.value;
        });
        results.clickAttempt.formBefore = formBefore;

        // Click the UCSY item
        ucsy.click();

        // Wait a bit
        await new Promise(r => setTimeout(r, 1000));

        const formAfter1 = {};
        document.querySelectorAll('input').forEach(el => {
            if (el.name && (el.name.includes('school') || el.name.includes('enrollment'))) formAfter1[el.name] = el.value;
        });
        results.clickAttempt.formAfterClick = formAfter1;

        // Method 2: Trigger auto-complete-change event
        const autoComplete = document.getElementById('js-school-name-search-container');
        if (autoComplete) {
            const event = new CustomEvent('auto-complete-change', {
                bubbles: true,
                detail: {relatedTarget: ucsy}
            });
            autoComplete.dispatchEvent(event);
            await new Promise(r => setTimeout(r, 500));

            const formAfter2 = {};
            document.querySelectorAll('input').forEach(el => {
                if (el.name && (el.name.includes('school') || el.name.includes('enrollment'))) formAfter2[el.name] = el.value;
            });
            results.clickAttempt.formAfterAutoComplete = formAfter2;
        }

        // Method 3: Set the autocomplete value attribute and trigger commit
        if (autoComplete) {
            // The auto-complete element uses 'value' attribute
            autoComplete.value = "University of Computer Studies, Yangon";
            const commitEvent = new CustomEvent('auto-complete-change', {bubbles: true});
            autoComplete.dispatchEvent(commitEvent);
            await new Promise(r => setTimeout(r, 500));
        }

        // Check for any new hidden inputs that got created
        const allInputs = [];
        document.querySelectorAll('input').forEach(el => {
            if (el.name) allInputs.push({name: el.name, value: (el.value || '').substring(0, 100), type: el.type});
        });
        results.allInputsAfter = allInputs;

        // Check if Continue button is enabled now
        const continueBtn = document.querySelector('button[name="continue"]');
        results.continueBtnEnabled = continueBtn ? !continueBtn.disabled : null;

        return results;
    }''')
    print(f"  Partials: {react_info.get('partials')}")
    print(f"  Global keys: {react_info.get('globalKeys')}")
    print(f"  Click attempt: {json.dumps(react_info.get('clickAttempt', {}), indent=2)[:500]}")
    print(f"  Continue enabled: {react_info.get('continueBtnEnabled')}")
    print(f"  All inputs after:")
    for inp in react_info.get('allInputsAfter', []):
        if 'school' in inp['name'] or 'enrollment' in inp['name'] or 'token' not in inp['name']:
            print(f"    {inp['name']} = {inp['value'][:80]} ({inp['type']})")

    # === Now try searching the JS bundles for school_id handling ===
    print("\n=== Search JS for school_id handling ===")
    js_search = page.evaluate('''async () => {
        const scripts = document.querySelectorAll('script[src]');
        const results = [];

        for (const script of scripts) {
            if (!script.src || !script.src.includes('github')) continue;

            try {
                const r = await fetch(script.src);
                const code = await r.text();

                // Search for school_id, selected-school-id, enrollment patterns
                const patterns = [
                    /selected.school.id/gi,
                    /school.?id/gi,
                    /enrollment.?size/gi,
                    /schoolId/gi,
                    /school_id/gi,
                ];

                for (const pat of patterns) {
                    const matches = code.match(pat);
                    if (matches) {
                        // Find context around first match
                        const idx = code.search(pat);
                        const context = code.substring(Math.max(0, idx - 100), idx + 200);
                        results.push({
                            src: script.src.split('/').pop(),
                            pattern: pat.source,
                            matchCount: matches.length,
                            context: context,
                        });
                    }
                }
            } catch(e) {
                // Skip failed requests
            }
        }
        return results;
    }''')
    print(f"  Found {len(js_search)} matches in JS bundles")
    for match in js_search[:10]:
        print(f"\n  File: {match['src']}")
        print(f"  Pattern: {match['pattern']} ({match['matchCount']} matches)")
        print(f"  Context: {match['context'][:200]}")

    browser.close()

print("\nDone!")
