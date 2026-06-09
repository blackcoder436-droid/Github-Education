"""Check why zero JS loads in Playwright."""
import os, re
from dotenv import load_dotenv
from client import GitHubClient
from playwright.sync_api import sync_playwright
load_dotenv()

c = GitHubClient()
ok = c.login(os.environ['GITHUB_USERNAME'], os.environ['GITHUB_PASSWORD'], totp_secret="SFDHLAA7MDH2S7TN")
print(f"Login: {ok}")

cookies = []
for cookie in c.session.cookies:
    cookies.append({
        "name": cookie.name,
        "value": cookie.value,
        "domain": cookie.domain or ".github.com",
        "path": cookie.path or "/",
        "secure": cookie.secure,
    })

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        permissions=["geolocation", "camera"],
        geolocation={"latitude": 16.8661, "longitude": 96.1951},
    )
    context.add_cookies(cookies)
    page = context.new_page()

    all_responses = []
    def on_resp(resp):
        all_responses.append({"url": resp.url[:150], "status": resp.status, "type": resp.request.resource_type})
    page.on("response", on_resp)

    page.goto(
        "https://github.com/settings/education/developer_pack_applications/new",
        timeout=60000, wait_until="networkidle",
    )
    page.wait_for_timeout(5000)

    html = page.content()

    # Check script tags
    print(f"=== Page HTML length: {len(html)} ===")
    print(f"URL: {page.url}")

    scripts = re.findall(r'<script[^>]*src="([^"]*)"[^>]*>', html)
    print(f"\nScript tags with src: {len(scripts)}")
    for s in scripts[:15]:
        print(f"  {s[:120]}")

    inline_scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
    print(f"\nInline scripts: {len(inline_scripts)}")
    for i, s in enumerate(inline_scripts[:5]):
        print(f"  [{i}] {len(s)} chars: {s[:100].strip()}...")

    # Check all network responses
    print(f"\n=== All responses: {len(all_responses)} ===")
    by_type = {}
    for r in all_responses:
        t = r['type']
        by_type[t] = by_type.get(t, 0) + 1
    for t, cnt in sorted(by_type.items()):
        print(f"  {t}: {cnt}")

    # Show JS/script responses specifically
    js_resps = [r for r in all_responses if r['type'] in ('script', 'xhr', 'fetch')]
    print(f"\nScript/XHR/Fetch responses: {len(js_resps)}")
    for r in js_resps[:20]:
        print(f"  [{r['status']}] {r['type']}: {r['url'][:120]}")

    # Check if it redirected to login
    if '/login' in page.url:
        print("\n*** REDIRECTED TO LOGIN! ***")

    browser.close()

print("\nDone!")
