"""Research 2FA initiate endpoint and full flow."""
import os, re, time, json, random
from dotenv import load_dotenv
from client import GitHubClient
from bs4 import BeautifulSoup
load_dotenv()

c = GitHubClient()
c.login(os.environ['GITHUB_USERNAME'], os.environ['GITHUB_PASSWORD'])
print("Logged in as:", c.username)

# Step 1: Visit the 2FA intro page
print("\n=== Step 1: Visit 2FA intro page ===")
resp = c.get("/settings/two_factor_authentication/setup/intro")
print(f"  {resp.status_code} {resp.url}")
soup = BeautifulSoup(resp.text, "html.parser")

# Extract initiate form data
init_form = soup.find("form", {"action": "/settings/two_factor_authentication/setup/initiate"})
if not init_form:
    print("  No initiate form found!")
    exit(1)

init_data = {}
for inp in init_form.find_all("input"):
    name = inp.get("name")
    if name:
        init_data[name] = inp.get("value", "")
print(f"  Initiate form data: {list(init_data.keys())}")

# Also extract the verify form data for later
verify_form = soup.find("form", {"action": "/settings/two_factor_authentication/setup/verify"})
verify_data = {}
if verify_form:
    type_inp = verify_form.find("input", {"name": "type"})
    if type_inp and type_inp.get("value") == "app":
        for inp in verify_form.find_all("input"):
            name = inp.get("name")
            if name:
                verify_data[name] = inp.get("value", "")
print(f"  Verify form data: {list(verify_data.keys())}")

# Step 2: POST initiate - try as JSON request (like JS would do)
print("\n=== Step 2: POST initiate ===")
time.sleep(2)

# Try with Accept: application/json to see if it returns JSON
headers = {
    "Accept": "application/json",
    "X-Requested-With": "XMLHttpRequest",
    "Content-Type": "application/x-www-form-urlencoded",
}
resp2 = c.session.post(
    f"{c.BASE}/settings/two_factor_authentication/setup/initiate",
    data=init_data,
    headers={**c.HEADERS, **headers},
)
print(f"  Status: {resp2.status_code}")
print(f"  Content-Type: {resp2.headers.get('Content-Type', '')}")
print(f"  Content-Length: {len(resp2.content)}")

# Check if JSON
try:
    data = resp2.json()
    print(f"  JSON response: {json.dumps(data, indent=2)[:2000]}")
except:
    # Not JSON, check HTML
    text = resp2.text[:2000]
    print(f"  Response text: {text}")

# Step 2b: Try without JSON accept
print("\n=== Step 2b: POST initiate (HTML) ===")
# Need to re-visit intro page first to get fresh tokens
resp = c.get("/settings/two_factor_authentication/setup/intro")
soup = BeautifulSoup(resp.text, "html.parser")
init_form = soup.find("form", {"action": "/settings/two_factor_authentication/setup/initiate"})
init_data = {}
if init_form:
    for inp in init_form.find_all("input"):
        name = inp.get("name")
        if name:
            init_data[name] = inp.get("value", "")

resp3 = c.post("/settings/two_factor_authentication/setup/initiate", data=init_data, allow_redirects=False)
print(f"  Status: {resp3.status_code}")
print(f"  Location: {resp3.headers.get('Location', 'none')}")
if resp3.status_code in (301, 302, 303):
    resp3b = c.get(resp3.headers['Location'])
    print(f"  Followed: {resp3b.status_code} {resp3b.url}")

# Step 3: Check if a data URL endpoint exists for QR/secret
print("\n=== Step 3: Check data URL endpoints ===")
# The form has a js-data-url-csrf input which suggests a data URL pattern
csrf_inputs = soup.find_all("input", {"class": "js-data-url-csrf"})
for ci in csrf_inputs:
    print(f"  js-data-url-csrf: {ci.get('value', '')[:60]}")

# Try fetching the setup data via GET with JSON
for ep in [
    "/settings/two_factor_authentication/setup",
    "/settings/two_factor_authentication/setup/app",
    "/settings/two_factor_authentication/setup/totp",
    "/settings/two_factor_authentication",
]:
    resp = c.session.get(
        f"{c.BASE}{ep}",
        headers={**c.HEADERS, "Accept": "application/json", "X-Requested-With": "XMLHttpRequest"},
    )
    if resp.status_code == 200:
        ct = resp.headers.get("Content-Type", "")
        print(f"  {ep}: {resp.status_code} CT={ct[:40]}")
        if "json" in ct:
            try:
                print(f"    JSON: {json.dumps(resp.json(), indent=2)[:500]}")
            except:
                pass
