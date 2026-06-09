"""Research 2FA - handle sudo mode for security pages."""
import os, re, json
from dotenv import load_dotenv
from client import GitHubClient
from bs4 import BeautifulSoup
load_dotenv()

c = GitHubClient()
c.login(os.environ['GITHUB_USERNAME'], os.environ['GITHUB_PASSWORD'])
print("Logged in as:", c.username)

# First check: is the session valid?
resp = c.get("/settings/profile")
print(f"Profile page: {resp.status_code} -> {resp.url}")

# Try security page - might need sudo
resp = c.get("/settings/security", allow_redirects=False)
print(f"\n/settings/security (no redirect): {resp.status_code}")
if resp.status_code in (301, 302, 303):
    location = resp.headers.get('Location', '')
    print(f"  Redirect to: {location}")

# Follow redirects
resp = c.get("/settings/security")
print(f"\n/settings/security (follow): {resp.status_code} -> {resp.url}")

# Check if it's a sudo password page
soup = BeautifulSoup(resp.text, "html.parser")
title = soup.title.string.strip() if soup.title else ""
print(f"  Title: {title}")

# Look for sudo password form
sudo_form = soup.find("form", {"action": re.compile(r"sudo|confirm|password")})
if sudo_form:
    print(f"  Found sudo form: {sudo_form.get('action')}")
    
# Look for any password input
pwd_inputs = soup.find_all("input", {"type": "password"})
if pwd_inputs:
    print(f"  Found {len(pwd_inputs)} password input(s)")
    for pi in pwd_inputs:
        print(f"    name={pi.get('name')} id={pi.get('id')}")

# If it's a login page, try to re-auth through it
if "/login" in resp.url or "Sign in" in title:
    print("\n--- Sudo/Login redirect detected, re-authenticating ---")
    token = c.extract_token(resp.text)
    
    # Check what form is on the page
    forms = soup.find_all("form")
    for f in forms:
        action = f.get("action", "")
        method = f.get("method", "")
        if action and "forgot" not in action:
            print(f"  Form: action={action} method={method}")
            inputs = f.find_all("input")
            for inp in inputs:
                print(f"    {inp.get('type','?')}: name={inp.get('name')} value={inp.get('value','')[:50]}")

    # Try sudo_login endpoint
    print("\n--- Trying sudo confirmation ---")
    sudo_data = {
        "authenticity_token": token,
        "sudo_login": os.environ['GITHUB_USERNAME'],
        "sudo_password": os.environ['GITHUB_PASSWORD'],
    }
    # Check if there's a specific form action for sudo
    sudo_form = soup.find("form", {"action": "/sessions/sudo"})
    if sudo_form:
        print("Found /sessions/sudo form")
        token2 = sudo_form.find("input", {"name": "authenticity_token"})
        if token2:
            sudo_data["authenticity_token"] = token2["value"]
    
    # Find the return_to parameter
    return_input = soup.find("input", {"name": "return_to"})
    if return_input:
        sudo_data["return_to"] = return_input.get("value", "")
        print(f"  return_to: {sudo_data['return_to']}")

    # First try: standard login flow if redirected to login
    resp2 = c.post("/session", data={
        "authenticity_token": token,
        "login": os.environ['GITHUB_USERNAME'],
        "password": os.environ['GITHUB_PASSWORD'],
        "commit": "Sign in",
    })
    print(f"  Re-login: {resp2.status_code} -> {resp2.url}")
    
    # Now try security page again
    resp3 = c.get("/settings/security")
    print(f"  Security after re-login: {resp3.status_code} -> {resp3.url}")
    soup3 = BeautifulSoup(resp3.text, "html.parser")
    title3 = soup3.title.string.strip() if soup3.title else ""
    print(f"  Title: {title3}")

# Also try password_and_authentication (GitHub's newer URL)
print("\n--- Trying /settings/security_analysis ---")
for ep in ["/settings/security_analysis", "/settings/sessions", "/settings/keys"]:
    resp = c.get(ep)
    print(f"  {ep}: {resp.status_code} -> {resp.url}")
    if resp.status_code == 200 and "/login" not in resp.url:
        soup = BeautifulSoup(resp.text, "html.parser")
        t = soup.title.string.strip() if soup.title else ""
        print(f"    Title: {t}")
        # Look for 2FA links
        links = soup.find_all("a", href=re.compile(r"two.factor|2fa|totp", re.I))
        for link in links:
            print(f"    2FA link: {link.get('href')} -> {link.text.strip()[:60]}")

# Try the direct enable 2FA page
print("\n--- Direct 2FA pages ---")
for ep in [
    "/settings/two_factor_authentication/intro",
    "/settings/two_factor_authentication/verify",
    "/settings/two_factor_authentication/app/new",
    "/users/two_factor_authentication",
    "/settings/security/two_factor_authentication",
]:
    resp = c.get(ep, allow_redirects=False)
    loc = resp.headers.get('Location', '')
    print(f"  {resp.status_code} {ep}" + (f" -> {loc}" if loc else ""))
