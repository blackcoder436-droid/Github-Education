"""Research 2FA setup flow with working credentials."""
import os, re, time, random, json
from dotenv import load_dotenv
from client import GitHubClient
from bs4 import BeautifulSoup
load_dotenv()

c = GitHubClient()
ok = c.login(os.environ['GITHUB_USERNAME'], os.environ['GITHUB_PASSWORD'])
print(f"Login: {'OK' if ok else 'FAIL'} as {c.username}")

if not ok:
    print("Cannot continue without login")
    exit(1)

# Verify session
resp = c.get("/settings/profile")
print(f"Profile: {resp.status_code} -> {resp.url}")
if "/login" in resp.url:
    print("Session not authenticated!")
    exit(1)

print("\n=== Checking 2FA status ===")
soup = BeautifulSoup(resp.text, "html.parser")
# Look for 2FA indicators on profile/settings pages
twofa_links = soup.find_all("a", href=re.compile(r"two.factor|2fa", re.I))
for link in twofa_links:
    print(f"  2FA link: {link.get('href')} -> {link.text.strip()[:60]}")

# Check password_and_authentication page
print("\n=== /settings/security ===")
resp = c.get("/settings/security")
print(f"  {resp.status_code} -> {resp.url}")
soup = BeautifulSoup(resp.text, "html.parser")
title = soup.title.string.strip() if soup.title else ""
print(f"  Title: {title}")

# If redirected to login for sudo, try to handle it
if "/login" in resp.url:
    print("  Redirected to login (sudo mode needed)")
    # Try to login through the sudo form
    token = c.extract_token(resp.text)
    
    # Check if it's a sudo password confirmation (not full login)
    sudo_form = soup.find("form", {"class": re.compile(r"sudo")})
    if sudo_form:
        print(f"  Found sudo form")
    
    # Re-authenticate
    data = {
        "authenticity_token": token,
        "login": os.environ['GITHUB_USERNAME'],
        "password": os.environ['GITHUB_PASSWORD'],
        "commit": "Sign in",
    }
    # Add return_to
    ret = soup.find("input", {"name": "return_to"})
    if ret:
        data["return_to"] = ret.get("value", "")
        print(f"  return_to: {data['return_to']}")
    
    resp2 = c.post("/session", data=data, allow_redirects=True)
    print(f"  Re-auth: {resp2.status_code} -> {resp2.url}")
    
    # Now try security page again
    time.sleep(2)
    resp = c.get("/settings/security")
    print(f"  Security retry: {resp.status_code} -> {resp.url}")
    soup = BeautifulSoup(resp.text, "html.parser")
    title = soup.title.string.strip() if soup.title else ""
    print(f"  Title: {title}")

if resp.status_code == 200 and "/login" not in resp.url:
    # Save the page for analysis
    with open("security_page.html", "w", encoding="utf-8") as f:
        f.write(resp.text)
    print("  Saved security_page.html")
    
    # Look for 2FA section
    twofa_section = soup.find(text=re.compile(r"Two-factor|two.factor", re.I))
    if twofa_section:
        parent = twofa_section.find_parent()
        print(f"  2FA section found in <{parent.name}>")
    
    # Look for enable 2FA button/link
    enable_btns = soup.find_all(["a", "button"], text=re.compile(r"enable|set.up|configure", re.I))
    for btn in enable_btns:
        href = btn.get("href", btn.get("formaction", ""))
        print(f"  Button: '{btn.text.strip()[:40]}' href={href}")
    
    # All links on the page
    all_links = soup.find_all("a", href=True)
    for link in all_links:
        href = link["href"]
        if "two_factor" in href or "2fa" in href or "security" in href or "totp" in href:
            print(f"  Relevant link: {href} -> {link.text.strip()[:40]}")

# Try the intro endpoint we found earlier
print("\n=== /settings/two_factor_authentication/setup/intro ===")
resp = c.get("/settings/two_factor_authentication/setup/intro")
print(f"  {resp.status_code} -> {resp.url}")
if resp.status_code == 200 and "/login" not in resp.url:
    soup = BeautifulSoup(resp.text, "html.parser")
    title = soup.title.string.strip() if soup.title else ""
    print(f"  Title: {title}")
    with open("2fa_intro.html", "w", encoding="utf-8") as f:
        f.write(resp.text)
    print("  Saved 2fa_intro.html")
    
    # Look for forms
    forms = soup.find_all("form")
    for form in forms:
        action = form.get("action", "")
        if action and "logout" not in action:
            print(f"  Form: action={action}")
            for inp in form.find_all("input"):
                print(f"    {inp.get('type','?')}: {inp.get('name','?')}={inp.get('value','')[:50]}")
    
    # Look for buttons/links to continue
    btns = soup.find_all(["a", "button"], text=re.compile(r"continue|next|enable|set.up|app|sms", re.I))
    for btn in btns:
        href = btn.get("href", "")
        print(f"  Action: '{btn.text.strip()[:40]}' tag={btn.name} href={href}")

# Try setup page directly
print("\n=== /settings/two_factor_authentication/setup ===")
resp = c.get("/settings/two_factor_authentication/setup")
print(f"  {resp.status_code} -> {resp.url}")
if resp.status_code == 200 and "/login" not in resp.url:
    with open("2fa_setup.html", "w", encoding="utf-8") as f:
        f.write(resp.text)
    print("  Saved 2fa_setup.html")
