"""Try submitting with continue button value included."""
import os, re, json, time
from dotenv import load_dotenv
from client import GitHubClient
from bs4 import BeautifulSoup
load_dotenv()

c = GitHubClient()
ok = c.login(
    os.environ['GITHUB_USERNAME'], 
    os.environ['GITHUB_PASSWORD'],
    totp_secret="SFDHLAA7MDH2S7TN",
)
print(f"Login: {'OK' if ok else 'FAIL'}")

time.sleep(2)

# Get fresh form
resp = c.get("/settings/education/developer_pack_applications/new")
soup = BeautifulSoup(resp.text, "html.parser")
form = soup.find("form", {"action": "/settings/education/developer_pack_applications"})

# Get token
token = form.find("input", {"name": "authenticity_token"}).get("value")
print(f"Token: {token[:20]}...")

data = {
    "authenticity_token": token,
    "dev_pack_form[application_type]": "student",
    "dev_pack_form[school_name]": "SKT International College",
    "dev_pack_form[school_email]": "thawkhant.1280@gmail.com",
    "dev_pack_form[latitude]": "16.8661",
    "dev_pack_form[longitude]": "96.1951",
    "dev_pack_form[location_shared]": "true",
    "dev_pack_form[utm_source]": "",
    "dev_pack_form[utm_content]": "",
    "dev_pack_form[form_variant]": "initial_form",
    "dev_pack_form[browser_location]": "Yangon, Myanmar",
    "continue": "Continue",  # Submit button name/value
}

print(f"\nSubmitting with Turbo-Frame + continue button...")
time.sleep(3)
resp2 = c.session.post(
    f"{c.BASE}/settings/education/developer_pack_applications",
    data=data,
    headers={
        **c.HEADERS,
        "Turbo-Frame": "dev-pack-form",
        "Accept": "text/vnd.turbo-stream.html, text/html, application/xhtml+xml",
        "Origin": c.BASE,
        "Referer": f"{c.BASE}/settings/education/developer_pack_applications/new",
    },
)
print(f"Status: {resp2.status_code} Len: {len(resp2.text)}")

with open("edu_try2.html", "w", encoding="utf-8") as f:
    f.write(resp2.text)

soup2 = BeautifulSoup(resp2.text, "html.parser")
text = soup2.get_text(separator="\n", strip=True)
lines = [l for l in text.split("\n") if l.strip()]
print(f"\nResponse text ({len(lines)} lines):")
for line in lines[:30]:
    print(f"  {line[:150]}")

# Check for forms  
forms = soup2.find_all("form")
print(f"\nForms found: {len(forms)}")
for f2 in forms:
    action = f2.get("action", "")
    enc = f2.get("enctype", "")
    print(f"  Form: action={action} enctype={enc}")

# Check for file-attachment
fas = soup2.find_all("file-attachment")
print(f"\nFile attachments: {len(fas)}")

# Check for turbo-stream
streams = soup2.find_all("turbo-stream")
print(f"\nTurbo streams: {len(streams)}")
for ts in streams:
    action_attr = ts.get("action")
    target = ts.get("target")
    print(f"  action={action_attr} target={target}")

# Also try without turbo-frame (regular redirect)
print("\n\n=== Try #2: Regular POST (no Turbo-Frame) ===")
time.sleep(3)

# Get fresh form
resp3 = c.get("/settings/education/developer_pack_applications/new")
soup3 = BeautifulSoup(resp3.text, "html.parser")
form3 = soup3.find("form", {"action": "/settings/education/developer_pack_applications"})
token3 = form3.find("input", {"name": "authenticity_token"}).get("value")

data3 = {
    "authenticity_token": token3,
    "dev_pack_form[application_type]": "student",
    "dev_pack_form[school_name]": "SKT International College",
    "dev_pack_form[school_email]": "thawkhant.1280@gmail.com",
    "dev_pack_form[latitude]": "16.8661",
    "dev_pack_form[longitude]": "96.1951",
    "dev_pack_form[location_shared]": "true",
    "dev_pack_form[utm_source]": "",
    "dev_pack_form[utm_content]": "",
    "dev_pack_form[form_variant]": "initial_form",
    "dev_pack_form[browser_location]": "Yangon, Myanmar",
    "continue": "Continue",
}

resp4 = c.session.post(
    f"{c.BASE}/settings/education/developer_pack_applications",
    data=data3,
    headers={
        **c.HEADERS,
        "Origin": c.BASE,
        "Referer": f"{c.BASE}/settings/education/developer_pack_applications/new",
    },
    allow_redirects=False,
)
print(f"Status: {resp4.status_code}")
print(f"Location: {resp4.headers.get('Location', 'none')}")
print(f"URL: {resp4.url}")

if resp4.status_code in (301, 302, 303):
    resp5 = c.session.get(resp4.headers["Location"] if resp4.headers["Location"].startswith("http") else f"{c.BASE}{resp4.headers['Location']}")
    print(f"Redirect to: {resp5.url} Status: {resp5.status_code}")
    with open("edu_try2_redirect.html", "w", encoding="utf-8") as f:
        f.write(resp5.text)
    print(f"Saved edu_try2_redirect.html")
    soup5 = BeautifulSoup(resp5.text, "html.parser")
    text5 = soup5.get_text(separator="\n", strip=True)
    lines5 = [l for l in text5.split("\n") if l.strip()]
    for line in lines5[:20]:
        print(f"  {line[:150]}")
elif resp4.status_code == 200:
    with open("edu_try2_200.html", "w", encoding="utf-8") as f:
        f.write(resp4.text)
    print("Saved edu_try2_200.html")
    soup4 = BeautifulSoup(resp4.text, "html.parser")
    text4 = soup4.get_text(separator="\n", strip=True)
    lines4 = [l for l in text4.split("\n") if l.strip()]
    for line in lines4[:30]:
        print(f"  {line[:150]}")
