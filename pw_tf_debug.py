"""Debug turbo-frame loading specifically."""
import os, sys, json, time
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
    )
    page = context.new_page()

    # Capture ALL network requests/responses
    net_log = []
    def on_response(resp):
        entry = {
            "url": resp.url[:200],
            "status": resp.status,
            "headers": {k: v for k, v in resp.headers.items() if k.lower() in ['content-type', 'turbo-frame', 'x-turbo-frame']},
        }
        if "developer_pack" in resp.url or "education" in resp.url:
            try:
                body = resp.text()
                entry["body_len"] = len(body)
                entry["body_preview"] = body[:500]
            except:
                entry["body_error"] = "couldn't read body"
        net_log.append(entry)
    page.on("response", on_response)

    def on_request_failed(req):
        if "developer_pack" in req.url or "education" in req.url:
            print(f"  REQUEST FAILED: {req.url[:200]} failure={req.failure}")
    page.on("requestfailed", on_request_failed)

    # Login
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
                print(f"  2FA page: {cur}")
                otp = pyotp.TOTP(TOTP_SECRET).now()
                # Try multiple selectors
                for sel in ['#app_totp', 'input[name="app_otp"]', 'input[name="otp"]']:
                    f = page.query_selector(sel)
                    if f:
                        f.fill(otp)
                        print(f"  Filled OTP in {sel}")
                        break
                page.wait_for_timeout(500)
                try:
                    page.click('button[type="submit"]', timeout=5000)
                except:
                    page.evaluate('document.querySelector("button[type=submit]")?.click()')
                page.wait_for_load_state("load", timeout=30000)
                page.wait_for_timeout(3000)
        else:
            print(f"  No login field! Page title: {page.title()}")
    print(f"  Final: {page.url}")

    # Navigate
    print("\n=== Navigate to /settings/education/benefits ===")
    net_log.clear()
    page.goto("https://github.com/settings/education/benefits", timeout=120000, wait_until="load")
    page.wait_for_timeout(5000)
    print(f"  URL: {page.url}")

    # Check turbo-frame before any waiting
    tf = page.evaluate('''(() => {
        const tf = document.querySelector('#dev-pack-form');
        if (!tf) return null;
        return {
            tagName: tf.tagName,
            src: tf.getAttribute('src'),
            loading: tf.getAttribute('loading'),
            childCount: tf.childElementCount,
            htmlLen: tf.innerHTML.length,
        };
    })()''')
    print(f"  Turbo-frame at 5s: {json.dumps(tf)}")

    # Check network for education/developer_pack requests
    edu_reqs = [n for n in net_log if "developer_pack" in n["url"] or "education" in n["url"]]
    print(f"  Education network requests: {len(edu_reqs)}")
    for r in edu_reqs:
        print(f"    {r['url']} status={r['status']} body_len={r.get('body_len', '?')}")
        if r.get("body_preview"):
            print(f"    Preview: {r['body_preview'][:200]!r}")

    # Wait more and scroll
    page.evaluate('''(() => {
        const tf = document.querySelector('#dev-pack-form');
        if (tf) tf.scrollIntoView({block: 'center'});
    })()''')
    page.wait_for_timeout(15000)

    # Check again
    tf2 = page.evaluate('''(() => {
        const tf = document.querySelector('#dev-pack-form');
        if (!tf) return null;
        return {
            childCount: tf.childElementCount,
            htmlLen: tf.innerHTML.length,
            hasForm: !!tf.querySelector('form'),
            text: tf.textContent?.trim()?.substring(0, 200) || '',
        };
    })()''')
    print(f"\n  Turbo-frame at 20s: {json.dumps(tf2)}")

    edu_reqs2 = [n for n in net_log if "developer_pack" in n["url"] or "education" in n["url"]]
    print(f"  Total education requests: {len(edu_reqs2)}")
    for r in edu_reqs2:
        print(f"    {r['url']} status={r['status']} body={r.get('body_len', '?')}")
        if r.get("body_preview"):
            print(f"    Preview: {r['body_preview'][:300]!r}")

    # Try forcing the src reload manually
    print("\n=== Forcing manual turbo-frame reload ===")
    page.evaluate('''(() => {
        const tf = document.querySelector('#dev-pack-form');
        if (tf && tf.src) {
            // Try using reload method if available
            if (typeof tf.reload === 'function') { tf.reload(); return 'reload'; }
            // Remove and re-add src
            const src = tf.src;
            tf.removeAttribute('src');
            tf.setAttribute('src', src);
            return 'reset-src';
        }
        return 'no-tf';
    })()''')
    page.wait_for_timeout(10000)

    tf3 = page.evaluate('''(() => {
        const tf = document.querySelector('#dev-pack-form');
        if (!tf) return null;
        return {
            childCount: tf.childElementCount,
            htmlLen: tf.innerHTML.length,
            hasForm: !!tf.querySelector('form'),
            text: tf.textContent?.trim()?.substring(0, 200) || '',
        };
    })()''')
    print(f"  After force: {json.dumps(tf3)}")

    edu_reqs3 = [n for n in net_log if ("developer_pack" in n["url"] or "education" in n["url"]) and n not in edu_reqs2]
    print(f"  New education requests: {len(edu_reqs3)}")
    for r in edu_reqs3:
        print(f"    {r['url']} status={r['status']} body={r.get('body_len', '?')}")
        if r.get("body_preview"):
            print(f"    Preview: {r['body_preview'][:300]!r}")

    # Try fetching the form URL directly via page.goto in same tab
    if not (tf3 and tf3.get('hasForm')):
        print("\n=== Direct fetch of form URL ===")
        resp_text = page.evaluate('''async () => {
            const resp = await fetch("/settings/education/developer_pack_applications/new", {
                headers: {
                    "Accept": "text/html",
                    "Turbo-Frame": "dev-pack-form",
                },
                credentials: "same-origin",
            });
            return {
                status: resp.status,
                statusText: resp.statusText,
                headers: Object.fromEntries([...resp.headers.entries()].filter(([k]) => ['content-type','turbo-frame'].includes(k.toLowerCase()))),
                body: (await resp.text()).substring(0, 1000),
            };
        }''')
        print(f"  Fetch status: {resp_text.get('status')} {resp_text.get('statusText')}")
        print(f"  Headers: {resp_text.get('headers')}")
        print(f"  Body preview: {resp_text.get('body', '')[:500]}")

        # Try injecting the HTML directly
        body = resp_text.get("body", "")
        if "<form" in body.lower():
            print("\n  Form found in fetch! Injecting into turbo-frame...")
            # The turbo-frame should handle this automatically - let's set innerHTML
            page.evaluate(f'''(() => {{
                const tf = document.querySelector('#dev-pack-form');
                const parser = new DOMParser();
                const doc = parser.parseFromString(`{body.replace('`', '\\`')}`, 'text/html');
                const newFrame = doc.querySelector('turbo-frame') || doc.body;
                tf.innerHTML = newFrame.innerHTML;
            }})()''')
            page.wait_for_timeout(3000)
            has_form = page.evaluate('!!document.querySelector("#dev-pack-form form")')
            print(f"  Form after injection: {has_form}")

    page.screenshot(path="pw_tf_debug.png")
    browser.close()
print("\nDone!")
