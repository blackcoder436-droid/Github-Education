"""Debug v2: Check what HTML/scripts the education page actually contains."""
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

    # Navigate with networkidle
    resp = page.goto("https://github.com/settings/education/developer_pack_applications/new", timeout=120000, wait_until="networkidle")
    print(f"URL: {page.url}")
    print(f"Status: {resp.status if resp else 'None'}")

    # Check page title
    title = page.title()
    print(f"Title: {title}")

    page.wait_for_timeout(15000)  # Extra long wait

    # Check scripts loaded
    info = page.evaluate('''() => {
        const allScripts = document.querySelectorAll('script');
        const srcs = [];
        let inlineCount = 0;
        allScripts.forEach(s => {
            if (s.src) srcs.push(s.src.split('/').pop().substring(0, 60));
            else inlineCount++;
        });
        return {
            totalScripts: allScripts.length,
            srcScripts: srcs.length,
            inlineScripts: inlineCount,
            firstFewSrcs: srcs.slice(0, 10),
            ce_rp: !!customElements.get('react-partial'),
            ce_ac: !!customElements.get('auto-complete'),
            ce_tf: !!customElements.get('turbo-frame'),
            perfCount: performance.getEntriesByType('resource').length,
            docReadyState: document.readyState,
            bodyLen: document.body?.innerHTML?.length || 0,
        };
    }''')
    print(f"Total scripts: {info['totalScripts']} (src={info['srcScripts']}, inline={info['inlineScripts']})")
    print(f"Custom elements: rp={info['ce_rp']}, ac={info['ce_ac']}, tf={info['ce_tf']}")
    print(f"Perf resources: {info['perfCount']}")
    print(f"Doc readyState: {info['docReadyState']}")
    print(f"Body length: {info['bodyLen']}")
    print(f"Script srcs: {json.dumps(info['firstFewSrcs'])}")

    # Dump first part of <head> to see if script tags are there
    head_html = page.evaluate('document.head.innerHTML.substring(0, 2000)')
    print(f"\nHEAD (first 2000 chars):")
    print(head_html)

    # Check if maybe it's a turbo-driven page with different structure
    turbo = page.evaluate('''() => {
        return {
            turboFrames: document.querySelectorAll('turbo-frame').length,
            turboFrameIds: Array.from(document.querySelectorAll('turbo-frame')).map(f => f.id).slice(0, 5),
            hasTurboRoot: !!document.querySelector('#turbo-body, [data-turbo-body]'),
        };
    }''')
    print(f"\nTurbo: {json.dumps(turbo)}")

    # Check all resource types
    resources = page.evaluate('''() => {
        return performance.getEntriesByType('resource').map(r => ({
            name: r.name.split('/').pop().substring(0, 50),
            type: r.initiatorType,
            dur: Math.round(r.duration),
        })).slice(0, 20);
    }''')
    print(f"\nResources ({len(resources)}):")
    for r in resources:
        print(f"  [{r['type']}] {r['name']} ({r['dur']}ms)")

    browser.close()
print("Done!")
