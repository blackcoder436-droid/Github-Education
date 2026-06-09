"""Debug login - check if session is actually authenticated."""
import os, re
from dotenv import load_dotenv
from client import GitHubClient
from bs4 import BeautifulSoup
load_dotenv()

c = GitHubClient()

print(f"Username: {os.environ.get('GITHUB_USERNAME')}")
print(f"Password length: {len(os.environ.get('GITHUB_PASSWORD', ''))}")

# Manual login with full debug
resp = c.session.get(f"{c.BASE}/login")
print(f"\nGET /login: {resp.status_code}")
token = c.extract_token(resp.text)
print(f"Token: {token[:20]}..." if token else "No token!")

data = {
    "authenticity_token": token,
    "login": os.environ['GITHUB_USERNAME'],
    "password": os.environ['GITHUB_PASSWORD'],
    "commit": "Sign in",
}

resp = c.session.post(f"{c.BASE}/session", data=data, allow_redirects=False)
print(f"\nPOST /session: {resp.status_code}")
print(f"Location: {resp.headers.get('Location', 'none')}")

# Show cookies
for cookie in c.session.cookies:
    print(f"Cookie: {cookie.name} = {cookie.value[:30]}..." if len(cookie.value) > 30 else f"Cookie: {cookie.name} = {cookie.value}")

# Follow redirect manually
if resp.status_code in (301, 302, 303):
    loc = resp.headers['Location']
    resp2 = c.session.get(loc, allow_redirects=False)
    print(f"\nFollowed to {loc}: {resp2.status_code}")
    if resp2.status_code in (301, 302, 303):
        loc2 = resp2.headers.get('Location', '')
        print(f"  -> {loc2}")
        resp3 = c.session.get(loc2 if loc2.startswith('http') else f"{c.BASE}{loc2}", allow_redirects=False)
        print(f"  -> {resp3.status_code}")
    elif resp2.status_code == 200:
        soup = BeautifulSoup(resp2.text, "html.parser")
        title = soup.title.string.strip() if soup.title else ""
        print(f"  Title: {title}")
        # Check for error messages
        flash = soup.find(class_=re.compile(r"flash.*error|error.*flash"))
        if flash:
            print(f"  Flash error: {flash.text.strip()}")
        # Look for "two-factor" or "verify"
        if "two-factor" in resp2.text or "two_factor" in resp2.text:
            print("  -> 2FA verification needed!")
        if "verify" in title.lower() or "device" in title.lower():
            print(f"  -> Device verification needed!")
        # Check for captcha
        if "captcha" in resp2.text.lower() or "hcaptcha" in resp2.text.lower():
            print("  -> CAPTCHA detected!")
elif resp.status_code == 200:
    soup = BeautifulSoup(resp.text, "html.parser")
    title = soup.title.string.strip() if soup.title else ""
    print(f"  Title: {title}")
    flash = soup.find(class_=re.compile(r"flash"))
    if flash:
        print(f"  Flash: {flash.text.strip()}")
    if "Incorrect" in resp.text or "invalid" in resp.text.lower():
        print("  -> Login FAILED (incorrect credentials)")
    with open("login_debug.html", "w", encoding="utf-8") as f:
        f.write(resp.text)
    print("  Saved login_debug.html")
