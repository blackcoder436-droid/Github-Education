"""Find and inspect the webcam-upload JS bundle."""
import os, sys, json
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
import pyotp
load_dotenv()

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    page = context.new_page()

    # Login
    page.goto("https://github.com/login", timeout=60000, wait_until="load")
    page.wait_for_timeout(3000)
    if "login" in page.url:
        f = page.query_selector('#login_field')
        if f:
            f.fill(os.environ['GITHUB_USERNAME'])
            page.fill('#password', os.environ['GITHUB_PASSWORD'])
            page.wait_for_timeout(500)
            page.click('input[name="commit"]')
            page.wait_for_timeout(5000)
            if "two-factor" in page.url or "sessions" in page.url:
                otp = pyotp.TOTP("SFDHLAA7MDH2S7TN").now()
                for sel in ['#app_totp', 'input[name="otp"]']:
                    el = page.query_selector(sel)
                    if el: el.fill(otp); break
                page.wait_for_timeout(500)
                try: page.click('button[type="submit"]', timeout=5000)
                except: pass
                page.wait_for_load_state("load", timeout=30000)
                page.wait_for_timeout(3000)
    print(f"Logged in: {'login' not in page.url}")

    page.goto("https://github.com/settings/education/benefits", timeout=120000, wait_until="load")
    page.wait_for_timeout(5000)

    # Find all script tags and look for webcam-related ones
    print("\n=== Script tags ===")
    scripts = page.evaluate('''() => {
        return Array.from(document.querySelectorAll('script[src]')).map(s => s.src).filter(s =>
            s.includes('webcam') || s.includes('education') || s.includes('partial') || s.includes('react')
        );
    }''')
    for s in scripts:
        print(f"  {s}")

    # Also check all script srcs for anything interesting
    all_scripts = page.evaluate('''() => {
        return Array.from(document.querySelectorAll('script[src]')).map(s => s.src);
    }''')
    print(f"\nAll scripts ({len(all_scripts)}):")
    for s in all_scripts:
        name = s.split('/')[-1] if '/' in s else s
        print(f"  {name}")

    # Fetch the webcam upload JS chunk if we can find it
    # Look for any chunk that contains "webcam" or "photo_proof"
    print("\n=== Searching for webcam JS code ===")
    for script_url in all_scripts:
        # Download and check for webcam-related code
        try:
            resp = page.evaluate(f'''async () => {{
                const r = await fetch("{script_url}");
                const text = await r.text();
                const lower = text.toLowerCase();
                if (lower.includes('webcam') || lower.includes('photo_proof') || lower.includes('photoproof') ||
                    lower.includes('capture') || lower.includes('formfieldid')) {{
                    // Find relevant snippets
                    const snippets = [];
                    const searches = ['photo_proof', 'photoProof', 'formFieldId', 'webcam', 'canvas.toDataURL',
                                     'toDataURL', 'captureImage', 'takePhoto', 'getImageData',
                                     'formData', 'photo_proof_url', 'upload'];
                    for (const term of searches) {{
                        let idx = text.indexOf(term);
                        while (idx !== -1 && snippets.length < 20) {{
                            snippets.push({{term, context: text.substring(Math.max(0, idx - 80), idx + 120)}});
                            idx = text.indexOf(term, idx + 1);
                        }}
                    }}
                    return {{url: "{script_url.split('/')[-1]}", found: true, size: text.length, snippets}};
                }}
                return null;
            }}''')
            if resp:
                print(f"\n  Found in: {resp['url']} ({resp['size']} bytes)")
                for s in resp.get('snippets', [])[:15]:
                    print(f"    [{s['term']}]: ...{s['context']}...")
        except Exception as e:
            pass

    browser.close()
print("\nDone!")
