"""Complete 2FA setup flow test."""
import os, re, time, json
from dotenv import load_dotenv
from client import GitHubClient
from bs4 import BeautifulSoup
import pyotp
load_dotenv()

c = GitHubClient()
c.login(os.environ['GITHUB_USERNAME'], os.environ['GITHUB_PASSWORD'])
print("Logged in as:", c.username)

# Step 1: Visit intro page
print("\n=== Step 1: Visit intro ===")
resp = c.get("/settings/two_factor_authentication/setup/intro")
soup = BeautifulSoup(resp.text, "html.parser")

# Extract initiate form  
init_form = soup.find("form", {"action": "/settings/two_factor_authentication/setup/initiate"})
init_data = {}
for inp in init_form.find_all("input"):
    name = inp.get("name")
    if name:
        init_data[name] = inp.get("value", "")

# Extract verify form
verify_form = None
for form in soup.find_all("form", {"action": "/settings/two_factor_authentication/setup/verify"}):
    type_inp = form.find("input", {"name": "type"})
    if type_inp and type_inp.get("value") == "app":
        verify_form = form
        break

verify_data = {}
if verify_form:
    for inp in verify_form.find_all("input"):
        name = inp.get("name")
        if name:
            verify_data[name] = inp.get("value", "")
print(f"  verify keys: {list(verify_data.keys())}")

# Extract recovery download form
dl_form = soup.find("form", {"action": "/settings/two_factor_authentication/setup/recovery_download"})
dl_data = {}
if dl_form:
    for inp in dl_form.find_all("input"):
        name = inp.get("name")
        if name:
            dl_data[name] = inp.get("value", "")

# Extract enable form
enable_form = soup.find("form", {"action": "/settings/two_factor_authentication/setup/enable"})
enable_data = {}
if enable_form:
    for inp in enable_form.find_all("input"):
        name = inp.get("name")
        if name:
            enable_data[name] = inp.get("value", "")

print(f"  dl keys: {list(dl_data.keys())}")
print(f"  enable keys: {list(enable_data.keys())}")

# Step 2: POST initiate with type=app
print("\n=== Step 2: Initiate ===")
init_data["type"] = "app"
headers = {
    "Accept": "application/json",
    "X-Requested-With": "XMLHttpRequest", 
    "Content-Type": "application/x-www-form-urlencoded",
    "Origin": "https://github.com",
    "Referer": "https://github.com/settings/two_factor_authentication/setup/intro",
}
time.sleep(2)
resp2 = c.session.post(
    f"{c.BASE}/settings/two_factor_authentication/setup/initiate",
    data=init_data,
    headers={**c.HEADERS, **headers},
)
data = resp2.json()
secret = data.get("mashed_secret", "")
recovery_codes = data.get("formatted_recovery_codes", [])
print(f"  Secret: {secret}")
print(f"  Recovery codes: {len(recovery_codes)}")

# Step 3: Generate TOTP code and verify
print("\n=== Step 3: Verify TOTP ===")
totp = pyotp.TOTP(secret)
code = totp.now()
print(f"  TOTP code: {code}")

verify_data["otp"] = code
time.sleep(2)
resp3 = c.session.post(
    f"{c.BASE}/settings/two_factor_authentication/setup/verify",
    data=verify_data,
    headers={**c.HEADERS, **headers},
)
print(f"  Status: {resp3.status_code}")
print(f"  CT: {resp3.headers.get('Content-Type','')}")
try:
    vdata = resp3.json()
    print(f"  JSON: {json.dumps(vdata, indent=2)[:500]}")
except:
    print(f"  Response: {resp3.text[:500]}")

# Step 4: Download recovery codes
print("\n=== Step 4: Recovery download ===")
time.sleep(1)
resp4 = c.session.post(
    f"{c.BASE}/settings/two_factor_authentication/setup/recovery_download",
    data=dl_data,
    headers={**c.HEADERS, "Accept": "text/plain,*/*", "Content-Type": "application/x-www-form-urlencoded",
             "Origin": "https://github.com", "Referer": "https://github.com/settings/two_factor_authentication/setup/intro"},
)
print(f"  Status: {resp4.status_code}")
print(f"  CT: {resp4.headers.get('Content-Type','')}")
print(f"  Body: {resp4.text[:300]}")

# Step 5: Enable 2FA
print("\n=== Step 5: Enable 2FA ===")
time.sleep(1)
resp5 = c.session.post(
    f"{c.BASE}/settings/two_factor_authentication/setup/enable",
    data=enable_data,
    headers={**c.HEADERS, **headers},
)
print(f"  Status: {resp5.status_code}")
print(f"  CT: {resp5.headers.get('Content-Type','')}")
try:
    edata = resp5.json()
    print(f"  JSON: {json.dumps(edata, indent=2)[:500]}")
except:
    print(f"  Response: {resp5.text[:300]}")

# Check if 2FA is now enabled by visiting security page
print("\n=== Verify ===")
time.sleep(2)
resp6 = c.get("/settings/security")
soup6 = BeautifulSoup(resp6.text, "html.parser")
if "Disable" in resp6.text and "two-factor" in resp6.text.lower():
    print("  2FA appears ENABLED!")
else:
    print("  2FA status unclear")

# Save the secret and recovery codes
print(f"\n=== SAVE THIS ===")
print(f"  TOTP Secret: {secret}")
print(f"  Recovery codes:")
for rc in recovery_codes:
    print(f"    {rc}")
