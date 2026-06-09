"""Education v15: Navigate to education page, check status, try autocomplete via DOM."""
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
    print(f"  URL: {page.url}")

    # === Go to education benefits page ===
    print("\n=== Education Benefits Page ===")
    page.goto("https://github.com/settings/education/benefits", timeout=120000, wait_until="load")
    page.wait_for_timeout(5000)
    print(f"  URL: {page.url}")

    # Check if there's already a pending/approved application
    page_text = page.evaluate('document.body?.textContent?.trim() || ""')
    for keyword in ['pending', 'approved', 'rejected', 'expired', 'developer pack', 'student', 'apply', 'benefits']:
        if keyword in page_text.lower():
            idx = page_text.lower().index(keyword)
            snippet = page_text[max(0,idx-50):idx+100].strip()
            print(f"  Found '{keyword}': ...{snippet}...")

    # Check for any existing application status
    existing_app = page.evaluate('''() => {
        const body = document.body;
        const statusEls = body.querySelectorAll('[data-test-selector], .Banner, .flash');
        const results = [];
        statusEls.forEach(el => results.push({
            selector: el.getAttribute('data-test-selector') || el.className,
            text: el.textContent.trim().substring(0, 200)
        }));

        // Check for "Get student benefits" or similar buttons/links
        const links = [];
        body.querySelectorAll('a, button').forEach(el => {
            const t = el.textContent.trim();
            if (t.length > 0 && t.length < 100 && (
                t.toLowerCase().includes('student') ||
                t.toLowerCase().includes('apply') ||
                t.toLowerCase().includes('benefits') ||
                t.toLowerCase().includes('education')
            )) links.push({text: t, href: el.href || ''});
        });

        return {statusElements: results, links};
    }''')
    if existing_app.get('statusElements'):
        for el in existing_app['statusElements'][:5]:
            print(f"  Status element: {el}")
    if existing_app.get('links'):
        for link in existing_app['links'][:10]:
            print(f"  Link: {link['text'][:60]} -> {link['href']}")

    # === Navigate to the actual application form page ===
    print("\n=== Application Form Page ===")
    page.goto("https://github.com/settings/education/developer_pack_applications/new", timeout=120000, wait_until="load")
    page.wait_for_timeout(5000)
    print(f"  URL: {page.url}")

    # Check page content
    form_info = page.evaluate('''() => {
        const body = document.body;
        const inputs = [];
        body.querySelectorAll('input, select, textarea').forEach(el => {
            const name = el.name || el.id || '';
            if (name && !name.startsWith('authenticity') && name !== 'commit') {
                inputs.push({name, type: el.type || el.tagName, value: (el.value||'').substring(0, 50)});
            }
        });

        // Check for turbo-frame
        const turboFrames = [];
        body.querySelectorAll('turbo-frame').forEach(el => {
            turboFrames.push({id: el.id, src: el.src || '', loaded: el.getAttribute('complete') !== null});
        });

        // Check for autocomplete
        const autoCompletes = [];
        body.querySelectorAll('auto-complete').forEach(el => {
            autoCompletes.push({id: el.id, src: el.getAttribute('src') || ''});
        });

        // Title and headings
        const headings = [];
        body.querySelectorAll('h1, h2, h3').forEach(el => headings.push(el.textContent.trim().substring(0, 100)));

        return {
            inputs: inputs.slice(0, 20),
            turboFrames,
            autoCompletes,
            headings: headings.slice(0, 10),
            bodyText: body.textContent.trim().substring(0, 500),
        };
    }''')
    print(f"  Headings: {form_info.get('headings')}")
    print(f"  Turbo frames: {form_info.get('turboFrames')}")
    print(f"  Auto-completes: {form_info.get('autoCompletes')}")
    print(f"  Inputs: {form_info.get('inputs')}")
    print(f"  Body text: {form_info.get('bodyText', '')[:300]}")

    # === Try autocomplete from page context (type in search box) ===
    print("\n=== Try autocomplete interaction ===")
    school_input = page.query_selector('#js-school-name-search')
    if school_input:
        print("  Found school search input!")

        # Listen for network requests
        requests_log = []
        def log_request(request):
            if 'school' in request.url.lower():
                requests_log.append({
                    'url': request.url,
                    'method': request.method,
                    'headers': dict(request.headers),
                })
        page.on("request", log_request)

        responses_log = []
        def log_response(response):
            if 'school' in response.url.lower():
                try:
                    body = response.text()
                except:
                    body = "<could not read>"
                responses_log.append({
                    'url': response.url,
                    'status': response.status,
                    'body': body[:1000] if body else '',
                })
        page.on("response", log_response)

        # Type in the search box
        school_input.click()
        page.wait_for_timeout(500)
        school_input.fill("University of Yangon")
        page.wait_for_timeout(3000)

        print(f"  Requests: {len(requests_log)}")
        for req in requests_log:
            print(f"    {req['method']} {req['url']}")
        print(f"  Responses: {len(responses_log)}")
        for resp in responses_log:
            print(f"    {resp['status']} {resp['url']}")
            print(f"    Body: {resp['body'][:300]}")

        # Check autocomplete results
        results_html = page.evaluate('''() => {
            const list = document.getElementById('js-school-name-list');
            if (!list) return "no list element";
            return {html: list.innerHTML.substring(0, 1000), text: list.textContent.trim().substring(0, 500)};
        }''')
        print(f"  Results: {results_html}")
    else:
        print("  No school search input found!")
        # Maybe the page didn't load the form properly
        # Check if it's a turbo-frame that needs to load
        turbo_content = page.evaluate('''() => {
            const frame = document.querySelector('turbo-frame#dev-pack-form');
            if (frame) return {found: true, html: frame.innerHTML.substring(0, 500)};
            return {found: false};
        }''')
        print(f"  Turbo frame: {turbo_content}")

    browser.close()

print("\nDone!")
