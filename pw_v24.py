"""Education v24: Debug why React partial/JS framework isn't initializing."""
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

    # Capture console messages
    console_msgs = []
    page.on("console", lambda msg: console_msgs.append(f"[{msg.type}] {msg.text[:200]}"))

    # Capture page errors
    page_errors = []
    page.on("pageerror", lambda err: page_errors.append(str(err)[:200]))

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

    # Clear console for education page
    console_msgs.clear()
    page_errors.clear()

    page.goto("https://github.com/settings/education/developer_pack_applications/new", timeout=120000, wait_until="load")
    page.wait_for_timeout(15000)  # Wait extra long for JS

    # === Check JS loading ===
    print("\n=== JS Status ===")
    js_status = page.evaluate('''() => {
        const scripts = [];
        document.querySelectorAll('script[src]').forEach(s => {
            scripts.push(s.src.split('/').pop().substring(0, 60));
        });

        // Check performance entries with all types
        const perf = {
            resource: performance.getEntriesByType('resource').length,
            navigation: performance.getEntriesByType('navigation').length,
        };

        // Actually get ALL resource entries
        const jsResources = performance.getEntriesByType('resource')
            .filter(e => e.name.endsWith('.js') || e.initiatorType === 'script')
            .map(e => ({name: e.name.split('/').pop().substring(0, 50), type: e.initiatorType}));

        // Check custom elements
        const customEls = {};
        for (const name of ['react-partial', 'auto-complete', 'turbo-frame', 'action-menu', 'anchored-position']) {
            customEls[name] = !!customElements.get(name);
        }

        // Check for webpack runtime
        const hasWebpack = typeof __webpack_require__ !== 'undefined';
        const webpackChunks = window.webpackChunk?.length || 0;

        return {scriptTags: scripts.length, scripts: scripts.slice(0, 10), perf, jsResources: jsResources.slice(0, 20), customEls, hasWebpack, webpackChunks};
    }''')
    print(f"  Script tags: {js_status.get('scriptTags')}")
    for s in js_status.get('scripts', []):
        print(f"    {s}")
    print(f"  Perf entries: {js_status.get('perf')}")
    print(f"  JS resources: {js_status.get('jsResources')}")
    print(f"  Custom elements: {js_status.get('customEls')}")
    print(f"  Webpack: {js_status.get('hasWebpack')}, chunks: {js_status.get('webpackChunks')}")

    # === Console messages ===
    print(f"\n=== Console ({len(console_msgs)} messages) ===")
    for msg in console_msgs[:30]:
        print(f"  {msg}")

    print(f"\n=== Page errors ({len(page_errors)}) ===")
    for err in page_errors[:10]:
        print(f"  {err}")

    # === Check react-partial custom element definition ===
    print("\n=== react-partial element ===")
    rp_info = page.evaluate('''() => {
        const CE = customElements.get('react-partial');
        if (!CE) return {defined: false};

        const rp = document.querySelector('react-partial[partial-name="education-schools-auto-complete"]');
        const rootEl = rp?.querySelector('[data-target="react-partial.reactRoot"]');

        // Get the class prototype methods (not inherited from HTMLElement)
        const ownMethods = [];
        let proto = CE.prototype;
        while (proto && proto !== HTMLElement.prototype) {
            ownMethods.push(...Object.getOwnPropertyNames(proto).filter(n => n !== 'constructor'));
            proto = Object.getPrototypeOf(proto);
        }

        return {
            defined: true,
            className: CE.name,
            ownMethods: ownMethods.slice(0, 30),
            rootRendered: rootEl ? rootEl.innerHTML.length > 10 : null,
            rootHtml: rootEl?.innerHTML?.substring(0, 200) || '',
        };
    }''')
    print(f"  {json.dumps(rp_info, indent=2)[:500]}")

    # === If custom element IS defined, try to trace what happens when it loads ===
    if rp_info.get('defined'):
        print("\n=== Trace react-partial loading ===")
        trace = page.evaluate('''async () => {
            const rp = document.querySelector('react-partial[partial-name="education-schools-auto-complete"]');
            const results = {};

            // Check targets/actions (catalyst patterns)
            const targets = rp.querySelectorAll('[data-target]');
            results.targets = [];
            targets.forEach(t => results.targets.push({
                target: t.getAttribute('data-target'),
                tag: t.tagName,
                content: t.innerHTML?.substring(0, 100) || '',
            }));

            // Check if there's a load function
            const proto = Object.getPrototypeOf(rp);
            const allProps = [];
            for (const key of Reflect.ownKeys(proto)) {
                try {
                    const desc = Object.getOwnPropertyDescriptor(proto, key);
                    allProps.push({
                        key: String(key),
                        type: desc?.value ? typeof desc.value : desc?.get ? 'getter' : 'other',
                    });
                } catch(e) {}
            }
            results.protoProps = allProps;

            // Try to trigger render
            try {
                // Remove and re-add to DOM to trigger connectedCallback
                const parent = rp.parentNode;
                const next = rp.nextSibling;
                parent.removeChild(rp);
                await new Promise(r => setTimeout(r, 100));
                parent.insertBefore(rp, next);
                await new Promise(r => setTimeout(r, 3000));

                const rootEl = rp.querySelector('[data-target="react-partial.reactRoot"]');
                results.afterReconnect = {
                    rendered: rootEl ? rootEl.innerHTML.length > 10 : false,
                    html: rootEl?.innerHTML?.substring(0, 200) || '',
                };
            } catch(e) {
                results.afterReconnect = {error: e.message};
            }

            return results;
        }''')
        print(f"  Targets: {trace.get('targets')}")
        print(f"  Proto props: {trace.get('protoProps')}")
        print(f"  After reconnect: {trace.get('afterReconnect')}")

    # === Alternative: find element-registry and chunk mapping ===
    print("\n=== Find element-registry chunk mapping ===")
    el_registry = page.evaluate('''async () => {
        // Search through ALL script elements for education-schools registration
        const scripts = document.querySelectorAll('script:not([src])');
        let found = null;
        for (const s of scripts) {
            const code = s.textContent || '';
            if (code.includes('education-schools') || code.includes('element-registry')) {
                found = code.substring(0, 500);
                break;
            }
        }

        // Also search src scripts
        const srcScripts = document.querySelectorAll('script[src]');
        const srcResults = [];
        for (const s of srcScripts) {
            try {
                const r = await fetch(s.src);
                const code = await r.text();
                if (code.includes('education-schools-auto-complete')) {
                    const idx = code.indexOf('education-schools-auto-complete');
                    srcResults.push({
                        src: s.src.split('/').pop().substring(0, 50),
                        context: code.substring(Math.max(0, idx-200), idx+300),
                    });
                }
            } catch(e) {}
        }

        return {inlineScript: found, srcResults};
    }''')
    if el_registry.get('inlineScript'):
        print(f"  Inline: {el_registry['inlineScript'][:300]}")
    print(f"  Src results: {len(el_registry.get('srcResults', []))}")
    for sr in el_registry.get('srcResults', [])[:3]:
        print(f"    {sr['src']}: {sr['context'][:400]}")

    browser.close()

print("\nDone!")
