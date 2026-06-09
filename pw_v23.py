"""Education v23: Find and load the React chunk for education-schools-auto-complete.
Then see what it does with school selection."""
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
    page.wait_for_timeout(10000)  # Wait longer for JS to init

    # === Find element registry entries ===
    print("\n=== Element Registry ===")
    registry = page.evaluate('''() => {
        const results = {};

        // Search all loaded JS for education-schools patterns
        const scripts = document.querySelectorAll('script[src]');
        for (const s of scripts) {
            results.scriptCount = (results.scriptCount || 0) + 1;
        }

        // Check window for custom element registries
        const allElements = {};
        if (window.customElements) {
            // Can't enumerate custom elements, but check specific ones
            const toCheck = ['react-partial', 'auto-complete', 'turbo-frame'];
            for (const name of toCheck) {
                allElements[name] = !!customElements.get(name);
            }
        }
        results.customElements = allElements;

        // Check if react-partial is defined and its internals
        const rp = document.querySelector('react-partial[partial-name="education-schools-auto-complete"]');
        if (rp) {
            results.reactPartial = {
                tagName: rp.tagName,
                childCount: rp.children.length,
                reactRoot: rp.querySelector('[data-target="react-partial.reactRoot"]')?.innerHTML?.substring(0, 500) || 'empty',
                allProps: Object.getOwnPropertyNames(rp).slice(0, 30),
                // Check stimulus-like controllers
                controllers: rp.getAttribute('data-controller') || 'none',
            };

            // Try to access internal React state
            try {
                const fiber = Object.keys(rp).find(k => k.startsWith('__react'));
                results.reactPartial.fiberKey = fiber || 'none';
            } catch(e) {}
        }

        // Check for react-partial's load method
        const rpProto = rp ? Object.getOwnPropertyNames(Object.getPrototypeOf(rp)) : [];
        results.protoMethods = rpProto;

        return results;
    }''')
    print(f"  Scripts: {registry.get('scriptCount')}")
    print(f"  Custom elements: {registry.get('customElements')}")
    print(f"  React partial: {json.dumps(registry.get('reactPartial', {}), indent=2)[:500]}")
    print(f"  Proto methods: {registry.get('protoMethods')}")

    # === Search for element-registry loader in page scripts ===
    print("\n=== Search for education-schools chunk ID ===")
    chunk_info = page.evaluate('''async () => {
        const scripts = document.querySelectorAll('script[src]');
        const results = [];

        for (const s of scripts) {
            try {
                const r = await fetch(s.src);
                const code = await r.text();

                // Look for education-schools-auto-complete registration
                if (code.includes('education-schools-auto-complete') || code.includes('education-schools')) {
                    // Find the surrounding context
                    const idx = code.indexOf('education-schools');
                    if (idx >= 0) {
                        const start = Math.max(0, idx - 300);
                        const end = Math.min(code.length, idx + 500);
                        results.push({
                            src: s.src.split('/').pop().substring(0, 50),
                            context: code.substring(start, end),
                        });
                    }
                }

                // Also look for element-registry patterns
                if (code.includes('element-registry') && code.includes('education')) {
                    const idx = code.indexOf('education');
                    const start = Math.max(0, idx - 200);
                    const end = Math.min(code.length, idx + 400);
                    results.push({
                        src: s.src.split('/').pop().substring(0, 50) + ' (registry)',
                        context: code.substring(start, end),
                    });
                }
            } catch(e) {}
        }
        return results;
    }''')
    print(f"  Found {len(chunk_info)} matches")
    for ci in chunk_info[:5]:
        print(f"\n  File: {ci['src']}")
        print(f"  Context: {ci['context'][:600]}")

    # === Check if react-partial element has a loadComponent/render method ===
    print("\n=== Try to manually load React component ===")
    load_result = page.evaluate('''async () => {
        const rp = document.querySelector('react-partial[partial-name="education-schools-auto-complete"]');
        if (!rp) return {error: "no react-partial"};

        const proto = Object.getPrototypeOf(rp);
        const methods = Object.getOwnPropertyNames(proto);

        // Try calling connectedCallback
        try {
            if (proto.connectedCallback) {
                rp.connectedCallback();
                await new Promise(r => setTimeout(r, 2000));
            }
        } catch(e) {}

        // Check if React rendered after reconnect
        const root = rp.querySelector('[data-target="react-partial.reactRoot"]');
        const rendered = root?.innerHTML?.length > 10;

        return {methods, rendered, rootHtml: root?.innerHTML?.substring(0, 300) || ''};
    }''')
    print(f"  Methods: {load_result.get('methods')}")
    print(f"  Rendered: {load_result.get('rendered')}")
    print(f"  Root HTML: {load_result.get('rootHtml', '')[:200]}")

    # Wait more and check again
    page.wait_for_timeout(5000)
    check2 = page.evaluate('''() => {
        const rp = document.querySelector('react-partial[partial-name="education-schools-auto-complete"]');
        const root = rp?.querySelector('[data-target="react-partial.reactRoot"]');
        return {rendered: (root?.innerHTML?.length || 0) > 10, html: root?.innerHTML?.substring(0, 300) || ''};
    }''')
    print(f"  After 5s wait: rendered={check2.get('rendered')}, html={check2.get('html', '')[:200]}")

    # === Direct approach: search ALL webpack chunks for school_id/selectedSchoolId ===
    print("\n=== Search ALL loaded chunks ===")
    all_js = page.evaluate('''async () => {
        // Get all performance entries that loaded JS
        const entries = performance.getEntriesByType('resource').filter(e =>
            e.name.includes('.js') && e.name.includes('github')
        );
        const results = [];
        const searched = new Set();

        for (const entry of entries) {
            if (searched.has(entry.name)) continue;
            searched.add(entry.name);

            try {
                const r = await fetch(entry.name);
                const code = await r.text();

                const patterns = ['selectedSchoolId', 'selected_school_id', 'data-selected-school-id', 'schoolId', 'school_id', 'enrollment'];
                for (const pat of patterns) {
                    if (code.includes(pat)) {
                        const idx = code.indexOf(pat);
                        const context = code.substring(Math.max(0, idx - 150), Math.min(code.length, idx + 300));
                        results.push({
                            url: entry.name.split('/').pop().substring(0, 50),
                            pattern: pat,
                            context,
                        });
                    }
                }
            } catch(e) {}
        }
        return {totalEntries: entries.length, results};
    }''')
    print(f"  Total JS entries: {all_js.get('totalEntries')}")
    for r in all_js.get('results', [])[:15]:
        print(f"\n  [{r['url']}] pattern: {r['pattern']}")
        print(f"  Context: {r['context'][:300]}")

    browser.close()

print("\nDone!")
