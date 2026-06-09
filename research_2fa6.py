"""Research 2FA - initiate with type parameter."""
import os, re, time, json
from dotenv import load_dotenv
from client import GitHubClient
from bs4 import BeautifulSoup
load_dotenv()

c = GitHubClient()
c.login(os.environ['GITHUB_USERNAME'], os.environ['GITHUB_PASSWORD'])
print("Logged in as:", c.username)

# Visit intro page
resp = c.get("/settings/two_factor_authentication/setup/intro")
soup = BeautifulSoup(resp.text, "html.parser")

# Get the initiate form
init_form = soup.find("form", {"action": "/settings/two_factor_authentication/setup/initiate"})
init_data = {}
for inp in init_form.find_all("input"):
    name = inp.get("name")
    if name:
        init_data[name] = inp.get("value", "")

# Add type=app
init_data["type"] = "app"
print(f"Initiate data: {init_data}")

# POST initiate as JSON request
headers = {
    "Accept": "application/json",
    "X-Requested-With": "XMLHttpRequest",
    "Content-Type": "application/x-www-form-urlencoded",
    "Origin": "https://github.com",
    "Referer": "https://github.com/settings/two_factor_authentication/setup/intro",
}
resp2 = c.session.post(
    f"{c.BASE}/settings/two_factor_authentication/setup/initiate",
    data=init_data,
    headers={**c.HEADERS, **headers},
)
print(f"\nStatus: {resp2.status_code}")
print(f"Content-Type: {resp2.headers.get('Content-Type', '')}")

try:
    data = resp2.json()
    print(f"JSON: {json.dumps(data, indent=2)[:3000]}")
    
    # Look for TOTP secret
    if "secret" in data:
        print(f"\nTOTP Secret: {data['secret']}")
    if "totp" in data:
        print(f"\nTOTP data: {data['totp']}")
    if "qr" in str(data).lower():
        print("QR data found in response!")
except:
    print(f"Response: {resp2.text[:2000]}")

# Also try with sms type
print("\n--- Try type=sms ---")
resp = c.get("/settings/two_factor_authentication/setup/intro")
soup = BeautifulSoup(resp.text, "html.parser")
init_form = soup.find("form", {"action": "/settings/two_factor_authentication/setup/initiate"})
init_data = {}
for inp in init_form.find_all("input"):
    name = inp.get("name")
    if name:
        init_data[name] = inp.get("value", "")
init_data["type"] = "sms"

resp3 = c.session.post(
    f"{c.BASE}/settings/two_factor_authentication/setup/initiate",
    data=init_data,
    headers={**c.HEADERS, **headers},
)
print(f"Status: {resp3.status_code}")
try:
    print(f"JSON: {json.dumps(resp3.json(), indent=2)[:1000]}")
except:
    print(f"Response: {resp3.text[:500]}")
