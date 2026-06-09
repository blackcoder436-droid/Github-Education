"""Debug: Check why JS isn't loading on the education form page."""
import os, sys, json
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
import pyotp
load_dotenv()

USERNAME = os.environ['GITHUB_USERNAME']
PASSWORD = os.environ['GITHUB_PASSWORD']
TOTP_SECRET = "SFDHLAA7MDH2S7TN"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
    )
    page = context.new_page()

    # Collect console + errors
    logs = []
    page.on("console", lambda m: logs.append(f"[{m.type}] {m.text[:200]}"))
    page.on("pageerror", lambda e: logs.append(f"[ERROR] {str(e)[:200]}"))

    # Login
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
    print(f"Logged in: {'login' not in page.url}")

    # Go to education form
    logs.clear()
    page.goto("https://github.com/settings/education/developer_pack_applications/new", timeout=120000, wait_until="networkidle")
    page.wait_for_timeout(10000)

    # Check JS status
    info = page.evaluate('''() => {
        return {
            scriptTags: document.querySelectorAll('script[src]').length,
            moduleScripts: document.querySelectorAll('script[type="module"]').length,
            inlineScripts: document.querySelectorAll('script:not([src])').length,
            customElements: {
                reactPartial: !!customElements.get('react-partial'),
                autoComplete: !!customElements.get('auto-complete'),
                turboFrame: !!customElements.get('turbo-frame'),
            },
            perfResources: performance.getEntriesByType('resource').length,
            jsFiles: performance.getEntriesByType('resource')
                .filter(e => e.name.endsWith('.js'))
                .map(e => e.name.split('/').pop()).slice(0, 5),
            allResourceTypes: [...new Set(performance.getEntriesByType('resource').map(e => e.initiatorType))],
        };
    }''')
    print(f"Scripts: {info['scriptTags']} src, {info['moduleScripts']} module, {info['inlineScripts']} inline")
    print(f"Custom elements: {info['customElements']}")
    print(f"Perf resources: {info['perfResources']}")
    print(f"JS files: {info['jsFiles']}")
    print(f"Resource types: {info['allResourceTypes']}")

    # Show first few script src attributes
    srcs = page.evaluate('''() => {
        const s = [];
        document.querySelectorAll('script[src]').forEach(el => s.push(el.src));
        return s.slice(0, 5);
    }''')
    print(f"Script srcs: {json.dumps(srcs, indent=2)[:500]}")

    # Console logs
    print(f"\nConsole ({len(logs)}):")
    for l in logs[:20]:
        print(f"  {l}")

    # Try manually loading a script
    print(f"\nManual script load test:")
    test = page.evaluate('''async () => {
        // Check if a random github JS loads
        const scripts = document.querySelectorAll('script[src*="github"]');
        if (scripts.length === 0) return "no github scripts found";

        const testSrc = scripts[0].src;
        try {
            const r = await fetch(testSrc);
            return {src: testSrc.split('/').pop(), status: r.status, len: (await r.text()).length};
        } catch(e) {
            return {error: e.message};
        }
    }''')
    print(f"  {test}")

    browser.close()
print("Done!")
