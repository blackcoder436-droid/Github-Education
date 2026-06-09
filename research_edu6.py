"""Enable 2FA on this account, then submit education form."""
import os, re, json, time
from dotenv import load_dotenv
from client import GitHubClient
from bs4 import BeautifulSoup
import pyotp
load_dotenv()

c = GitHubClient()
c.login(os.environ['GITHUB_USERNAME'], os.environ['GITHUB_PASSWORD'])
print("Logged in as:", c.username)

# ── Enable 2FA ──
print("\n=== Enabling 2FA ===")
resp = c.get("/settings/security")
if "Disable two-factor authentication" in resp.text:
    print("  Already enabled!")
else:
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
    
    # Get verify form
    verify_data = {}
    for form in soup.find_all("form", {"action": "/settings/two_factor_authentication/setup/verify"}):
        type_inp = form.find("input", {"name": "type"})
        if type_inp and type_inp.get("value") == "app":
            for inp in form.find_all("input"):
                name = inp.get("name")
                if name:
                    verify_data[name] = inp.get("value", "")
            break
    
    # Initiate
    json_headers = {
        "Accept": "application/json",
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded",
        "Origin": c.BASE,
        "Referer": f"{c.BASE}/settings/two_factor_authentication/setup/intro",
    }
    time.sleep(2)
    resp2 = c.session.post(
        f"{c.BASE}/settings/two_factor_authentication/setup/initiate",
        data=init_data,
        headers={**c.HEADERS, **json_headers},
    )
    payload = resp2.json()
    secret = payload["mashed_secret"]
    recovery = payload["formatted_recovery_codes"]
    print(f"  Secret: {secret}")
    print(f"  Recovery codes: {len(recovery)}")
    
    # Verify
    time.sleep(2)
    totp = pyotp.TOTP(secret)
    code = totp.now()
    verify_data["otp"] = code
    resp3 = c.session.post(
        f"{c.BASE}/settings/two_factor_authentication/setup/verify",
        data=verify_data,
        headers={**c.HEADERS, **json_headers},
    )
    print(f"  Verify: {resp3.status_code}")
    
    # Confirm 2FA is enabled
    time.sleep(2)
    resp_check = c.get("/settings/security")
    if "Disable two-factor authentication" in resp_check.text:
        print("  2FA ENABLED!")
        # Save credentials
        with open("2fa_credentials.txt", "w") as f:
            f.write(f"Username: {c.username}\n")
            f.write(f"TOTP Secret: {secret}\n")
            f.write(f"Recovery Codes:\n")
            for rc in recovery:
                f.write(f"  {rc}\n")
        print("  Saved 2fa_credentials.txt")
    else:
        print("  2FA NOT enabled - something went wrong")
        exit(1)

# ── Submit Education Form ──
print("\n=== Submitting Education Form ===")
time.sleep(3)

resp = c.get("/settings/education/developer_pack_applications/new")
soup = BeautifulSoup(resp.text, "html.parser")
form = soup.find("form", {"action": "/settings/education/developer_pack_applications"})

data = {}
for inp in form.find_all("input"):
    name = inp.get("name")
    if name and inp.get("type") != "submit":
        if name not in data:
            data[name] = inp.get("value", "")
for sel in form.find_all("select"):
    name = sel.get("name")
    if name:
        opts = sel.find_all("option")
        data[name] = opts[0].get("value", "") if opts else ""

data["dev_pack_form[application_type]"] = "student"
data["dev_pack_form[school_name]"] = "SKT International College"
data["dev_pack_form[school_email]"] = "thawkhant.1280@gmail.com"
data["dev_pack_form[latitude]"] = "16.8661"
data["dev_pack_form[longitude]"] = "96.1951"
data["dev_pack_form[location_shared]"] = "true"
data["dev_pack_form[form_variant]"] = "initial_form"

print(f"  Submitting with: {json.dumps({k:v for k,v in data.items() if 'token' not in k}, indent=2)}")

time.sleep(2)
resp2 = c.session.post(
    f"{c.BASE}/settings/education/developer_pack_applications",
    data=data,
    headers={
        **c.HEADERS,
        "Turbo-Frame": "dev-pack-form",
        "Accept": "text/vnd.turbo-stream.html, text/html, application/xhtml+xml",
        "Origin": c.BASE,
        "Referer": f"{c.BASE}/settings/education/benefits",
    },
)
print(f"\nStatus: {resp2.status_code}")

with open("edu_after_2fa.html", "w", encoding="utf-8") as f:
    f.write(resp2.text)
print("Saved edu_after_2fa.html")

soup2 = BeautifulSoup(resp2.text, "html.parser")
text = soup2.get_text(separator="\n", strip=True)
lines = [l for l in text.split("\n") if l.strip() and len(l.strip()) > 3]
print(f"\nResponse ({len(lines)} lines):")
for line in lines[:60]:
    print(f"  {line[:150]}")

# Look for forms
forms = soup2.find_all("form")
for f2 in forms:
    action = f2.get("action", "")
    if action:
        enc = f2.get("enctype", "")
        print(f"\nForm: action={action} enctype={enc}")
        for inp in f2.find_all(["input", "select", "textarea", "file-attachment"]):
            name = inp.get("name", "")
            val = inp.get("value", "")[:80]
            typ = inp.get("type", inp.name)
            if name:
                print(f"  {typ}: {name} = {val}")
            # file-attachment
            if inp.name == "file-attachment":
                print(f"  file-attachment: {inp.attrs}")
