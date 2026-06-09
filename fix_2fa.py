"""Fix 2FA enable - try the enable endpoint with type param."""
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

# Get initiate form
init_form = soup.find("form", {"action": "/settings/two_factor_authentication/setup/initiate"})
init_data = {}
for inp in init_form.find_all("input"):
    name = inp.get("name")
    if name:
        init_data[name] = inp.get("value", "")
init_data["type"] = "app"

# Get verify form (app)
verify_data = {}
for form in soup.find_all("form", {"action": "/settings/two_factor_authentication/setup/verify"}):
    type_inp = form.find("input", {"name": "type"})
    if type_inp and type_inp.get("value") == "app":
        for inp in form.find_all("input"):
            name = inp.get("name")
            if name:
                verify_data[name] = inp.get("value", "")
        break

# Get enable form
enable_form = soup.find("form", {"action": "/settings/two_factor_authentication/setup/enable"})
enable_data = {}
if enable_form:
    for inp in enable_form.find_all("input"):
        name = inp.get("name")
        if name:
            enable_data[name] = inp.get("value", "")
    print(f"Enable form data: {enable_data}")
else:
    print("No enable form found!")

# Get recovery download form
dl_form = soup.find("form", {"action": "/settings/two_factor_authentication/setup/recovery_download"})
dl_data = {}
if dl_form:
    for inp in dl_form.find_all("input"):
        name = inp.get("name")
        if name:
            dl_data[name] = inp.get("value", "")

json_h = {
    "Accept": "application/json",
    "X-Requested-With": "XMLHttpRequest",
    "Content-Type": "application/x-www-form-urlencoded",
    "Origin": c.BASE,
    "Referer": f"{c.BASE}/settings/two_factor_authentication/setup/intro",
}

# Step 1: Initiate
print("\n=== Initiate ===")
time.sleep(2)
r1 = c.session.post(
    f"{c.BASE}/settings/two_factor_authentication/setup/initiate",
    data=init_data,
    headers={**c.HEADERS, **json_h},
)
payload = r1.json()
secret = payload["mashed_secret"]
recovery = payload["formatted_recovery_codes"]
print(f"  Secret: {secret}")
print(f"  Recovery: {len(recovery)} codes")

# Step 2: Verify
print("\n=== Verify ===")
time.sleep(3)
totp = pyotp.TOTP(secret)
code = totp.now()
print(f"  Code: {code}")
verify_data["otp"] = code
r2 = c.session.post(
    f"{c.BASE}/settings/two_factor_authentication/setup/verify",
    data=verify_data,
    headers={**c.HEADERS, **json_h},
)
print(f"  Status: {r2.status_code}")

# Step 3: Try enable with different parameters
print("\n=== Enable (try variations) ===")
time.sleep(2)

# Try 1: enable with type=app
d1 = dict(enable_data)
d1["type"] = "app"
r3 = c.session.post(
    f"{c.BASE}/settings/two_factor_authentication/setup/enable",
    data=d1,
    headers={**c.HEADERS, **json_h},
)
print(f"  With type=app: {r3.status_code} -> {r3.text[:200]}")

# Try 2: enable without JSON headers (HTML form submit)
time.sleep(1)
r4 = c.post("/settings/two_factor_authentication/setup/enable", data=enable_data, allow_redirects=False)
print(f"  HTML submit: {r4.status_code} Location={r4.headers.get('Location','none')}")

# Try 3: enable with type=app, HTML submit
d3 = dict(enable_data)
d3["type"] = "app"
r5 = c.post("/settings/two_factor_authentication/setup/enable", data=d3, allow_redirects=False)
print(f"  HTML+type: {r5.status_code} Location={r5.headers.get('Location','none')}")

# Try 4: Maybe we need to download recovery codes first
print("\n=== Recovery Download ===")
time.sleep(1)
r6 = c.session.post(
    f"{c.BASE}/settings/two_factor_authentication/setup/recovery_download",
    data=dl_data,
    headers={**c.HEADERS, "Accept": "text/plain,*/*", "Content-Type": "application/x-www-form-urlencoded",
             "Origin": c.BASE, "Referer": f"{c.BASE}/settings/two_factor_authentication/setup/intro"},
)
print(f"  Status: {r6.status_code}")
print(f"  Body preview: {r6.text[:100]}")

# Try enable again after download
time.sleep(1) 
d4 = dict(enable_data)
r7 = c.session.post(
    f"{c.BASE}/settings/two_factor_authentication/setup/enable",
    data=d4,
    headers={**c.HEADERS, **json_h},
)
print(f"\n  Enable after download: {r7.status_code} -> {r7.text[:200]}")

# Check security page
time.sleep(2)
r8 = c.get("/settings/security")
if "Two-factor authentication is not enabled yet" in r8.text:
    print("\n  2FA still NOT enabled")
else:
    print("\n  2FA appears enabled!") 
    # Look for how the page describes 2FA status
    soup8 = BeautifulSoup(r8.text, "html.parser")
    for h2 in soup8.find_all("h2"):
        txt = h2.text.strip()
        if "factor" in txt.lower():
            print(f"    h2: {txt}")
