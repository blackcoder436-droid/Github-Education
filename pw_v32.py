"""v32: Check existing applications, try to delete/reset them, then submit fresh."""
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

    # Check the applications index page
    page.goto("https://github.com/settings/education/developer_pack_applications", timeout=60000, wait_until="load")
    page.wait_for_timeout(3000)
    print(f"\n=== Applications index ===")
    print(f"URL: {page.url}")
    apps_text = page.evaluate('document.body?.textContent?.trim()?.substring(0, 2000) || ""')
    # Clean whitespace
    import re
    apps_text = re.sub(r'\s+', ' ', apps_text)
    print(f"Text: {apps_text[:1000]}")

    # Check for application links, buttons
    app_links = page.evaluate('''() => {
        const items = [];
        document.querySelectorAll('a, button').forEach(el => {
            const text = el.textContent.trim();
            if (text && (text.includes('applic') || text.includes('delete') || 
                text.includes('cancel') || text.includes('edit') || 
                text.includes('pack') || text.includes('education') ||
                text.includes('pending') || text.includes('approved') ||
                text.includes('rejected') || text.includes('status')))
                items.push({
                    tag: el.tagName,
                    text: text.substring(0, 100),
                    href: el.href || '',
                    action: el.closest('form')?.action || '',
                });
        });
        return items;
    }''')
    print(f"\nRelevant buttons/links: {json.dumps(app_links, indent=2)[:800]}")

    # Check education main page for status
    page.goto("https://github.com/settings/education", timeout=60000, wait_until="load")
    page.wait_for_timeout(3000)
    print(f"\n=== Education main page ===")
    print(f"URL: {page.url}")
    edu_body = page.evaluate('''() => {
        const text = document.body?.textContent?.trim() || '';
        // Clean up whitespace
        return text.replace(/\\s+/g, ' ').substring(0, 2000);
    }''')
    edu_body = re.sub(r'\s+', ' ', edu_body)
    print(f"Text: {edu_body[:1000]}")

    # Check for forms (delete forms etc.)
    forms = page.evaluate('''() => {
        const items = [];
        document.querySelectorAll('form').forEach(el => {
            items.push({
                action: el.action,
                method: el.method,
                buttonText: el.querySelector('button,input[type="submit"]')?.textContent?.trim()?.substring(0, 50) || '',
            });
        });
        return items;
    }''')
    print(f"\nForms: {json.dumps(forms, indent=2)[:500]}")

    # Now go to the new form page and check full banner
    page.goto("https://github.com/settings/education/developer_pack_applications/new", timeout=120000, wait_until="load")
    page.wait_for_timeout(3000)
    banner_full = page.evaluate('''() => {
        const items = [];
        document.querySelectorAll('.Banner, .flash, .Flash, [role="alert"], [role="status"]').forEach(el => {
            items.push({
                html: el.outerHTML.substring(0, 500),
                text: el.textContent.trim().substring(0, 300),
            });
        });
        return items;
    }''')
    print(f"\n=== Form page banners ===")
    for b in banner_full:
        print(f"Text: {b['text'][:300]}")
        print(f"HTML: {b['html'][:400]}")
        print()

    browser.close()
print("Done!")
