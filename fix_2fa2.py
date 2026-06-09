"""Final 2FA flow - correct order: initiate -> verify -> download -> enable."""
import os, re, json, time
from dotenv import load_dotenv
from client import GitHubClient
from bs4 import BeautifulSoup
import pyotp
load_dotenv()

c = GitHubClient()
c.login(os.environ['GITHUB_USERNAME'], os.environ['GITHUB_PASSWORD'])
print("Logged in as:", c.username)

# Visit intro page
resp = c.get("/settings/two_factor_authentication/setup/intro")
soup = BeautifulSoup(resp.text, "html.parser")

# Extract all form data
init_form = soup.find("form", {"action": "/settings/two_factor_authentication/setup/initiate"})
init_data = {inp.get("name"): inp.get("value", "") for inp in init_form.find_all("input") if inp.get("name")}
init_data["type"] = "app"

verify_data = {}
for form in soup.find_all("form", {"action": "/settings/two_factor_authentication/setup/verify"}):
    ti = form.find("input", {"name": "type"})
    if ti and ti.get("value") == "app":
        verify_data = {inp.get("name"): inp.get("value", "") for inp in form.find_all("input") if inp.get("name")}
        break

dl_form = soup.find("form", {"action": "/settings/two_factor_authentication/setup/recovery_download"})
dl_data = {inp.get("name"): inp.get("value", "") for inp in dl_form.find_all("input") if inp.get("name")}

enable_form = soup.find("form", {"action": "/settings/two_factor_authentication/setup/enable"})
enable_data = {inp.get("name"): inp.get("value", "") for inp in enable_form.find_all("input") if inp.get("name")}

json_h = {
    "Accept": "application/json",
    "X-Requested-With": "XMLHttpRequest",
    "Content-Type": "application/x-www-form-urlencoded",
    "Origin": c.BASE,
    "Referer": f"{c.BASE}/settings/two_factor_authentication/setup/intro",
}

# Step 1: Initiate
print("1. Initiate")
time.sleep(2)
r = c.session.post(f"{c.BASE}/settings/two_factor_authentication/setup/initiate", data=init_data, headers={**c.HEADERS, **json_h})
p = r.json()
secret = p["mashed_secret"]
recovery = p["formatted_recovery_codes"]
print(f"   Secret: {secret}")

# Step 2: Verify
print("2. Verify")
time.sleep(3)
verify_data["otp"] = pyotp.TOTP(secret).now()
r = c.session.post(f"{c.BASE}/settings/two_factor_authentication/setup/verify", data=verify_data, headers={**c.HEADERS, **json_h})
print(f"   Status: {r.status_code}")

# Step 3: Download recovery codes
print("3. Download recovery")
time.sleep(1)
r = c.session.post(
    f"{c.BASE}/settings/two_factor_authentication/setup/recovery_download",
    data=dl_data,
    headers={**c.HEADERS, "Accept": "text/plain,*/*", "Content-Type": "application/x-www-form-urlencoded",
             "Origin": c.BASE, "Referer": f"{c.BASE}/settings/two_factor_authentication/setup/intro"},
)
print(f"   Status: {r.status_code} ({len(r.text)} bytes)")

# Step 4: Enable with type=app
print("4. Enable")
time.sleep(1)
enable_data["type"] = "app"
r = c.session.post(f"{c.BASE}/settings/two_factor_authentication/setup/enable", data=enable_data, headers={**c.HEADERS, **json_h})
print(f"   Status: {r.status_code}")
print(f"   Body: {r.text[:200]}")

# Check
time.sleep(2)
r = c.get("/settings/security")
if "Two-factor authentication is not enabled yet" in r.text:
    print("\nFAIL: 2FA still NOT enabled")
else:
    print("\nSUCCESS: 2FA enabled!")

# Save credentials
with open("2fa_credentials.txt", "w") as f:
    f.write(f"Username: {c.username}\n")
    f.write(f"TOTP Secret: {secret}\n")
    f.write(f"Recovery Codes:\n")
    for rc in recovery:
        f.write(f"  {rc}\n")
print("Saved 2fa_credentials.txt")
