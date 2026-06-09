"""v31: Check application state and try minimal submission.
Previous tests may have created pending applications or hit rate limiting.
"""
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

    # Check education status page first
    page.goto("https://github.com/settings/education", timeout=60000, wait_until="load")
    page.wait_for_timeout(3000)
    edu_text = page.evaluate('document.body?.textContent?.trim()?.substring(0, 2000) || ""')
    print(f"\n=== Education page text ===")
    print(edu_text[:800])

    # Check for existing applications
    edu_links = page.evaluate('''() => {
        const links = [];
        document.querySelectorAll('a').forEach(el => {
            if (el.href && el.href.includes('education'))
                links.push({href: el.href, text: el.textContent.trim().substring(0, 100)});
        });
        return links;
    }''')
    print(f"\nEducation links: {json.dumps(edu_links, indent=2)[:500]}")

    # Now check the application form page
    page.goto("https://github.com/settings/education/developer_pack_applications/new", timeout=120000, wait_until="load")
    page.wait_for_timeout(3000)
    print(f"\nForm page URL: {page.url}")

    # Check if there's a notice about existing application
    page_text = page.evaluate('document.body?.textContent?.trim()?.substring(0, 1000) || ""')
    print(f"Page text (first 400):\n{page_text[:400]}")

    # Check for any banners/notices
    banners = page.evaluate('''() => {
        const items = [];
        document.querySelectorAll('.Banner, .flash, .Flash, [role="alert"], [role="status"]').forEach(el => {
            items.push(el.textContent.trim().substring(0, 200));
        });
        return items;
    }''')
    print(f"\nBanners: {banners}")

    # Now try a MINIMAL submission with fd.set() only (single school_name)
    result = page.evaluate('''async () => {
        const form = document.querySelector('form[action="/settings/education/developer_pack_applications"]');
        if (!form) return {error: "no form"};

        const fd = new FormData(form);
        
        // Use fd.set to replace duplicate school_name with single value
        fd.set('dev_pack_form[application_type]', 'student');
        fd.set('dev_pack_form[school_name]', 'Yangon Technological University');
        fd.set('dev_pack_form[form_variant]', 'initial_form');
        fd.set('dev_pack_form[latitude]', '16.8661');
        fd.set('dev_pack_form[longitude]', '96.1951');
        fd.set('dev_pack_form[location_shared]', 'true');
        fd.set('dev_pack_form[browser_location]', '16.8661,96.1951');
        // NO school_id - this is the baseline test matching v18 approach

        const entries = [];
        for (const [k, v] of fd.entries()) {
            if (!k.includes('authenticity'))
                entries.push(k + '=' + (typeof v === 'string' ? v : '').substring(0, 80));
        }

        const r = await fetch("/settings/education/developer_pack_applications", {
            method: "POST",
            headers: {
                "Turbo-Frame": "dev-pack-form",
                "Accept": "text/vnd.turbo-stream.html, text/html, application/xhtml+xml",
            },
            credentials: "same-origin",
            body: fd,
        });
        const text = await r.text();
        
        return {
            status: r.status,
            entries,
            hasEnrollment: text.includes('Enrollment size'),
            hasProof: text.includes('proof_type') || text.includes('photo_proof'),
            bodyPreview: text.substring(0, 800),
        };
    }''')

    print(f"\n=== Baseline submission (no school_id, fd.set) ===")
    print(f"Status: {result['status']}")
    print(f"Entries: {json.dumps(result.get('entries', []))}")
    print(f"Enrollment: {result['hasEnrollment']}, Proof: {result['hasProof']}")
    print(f"Response:\n{result.get('bodyPreview', '')[:500]}")

    browser.close()
print("\nDone!")
