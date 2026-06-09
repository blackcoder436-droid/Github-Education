"""Research school autocomplete and education form submission."""
import os, re, json, time
from dotenv import load_dotenv
from client import GitHubClient
from bs4 import BeautifulSoup
load_dotenv()

c = GitHubClient()
c.login(os.environ['GITHUB_USERNAME'], os.environ['GITHUB_PASSWORD'])
print("Logged in as:", c.username)

# Try the school autocomplete endpoint
print("\n=== School autocomplete ===")
resp = c.session.get(
    f"{c.BASE}/settings/education/developer_pack_applications/schools",
    params={"q": "SKT International"},
    headers={
        **c.HEADERS,
        "Accept": "text/fragment+html",
        "X-Requested-With": "XMLHttpRequest",
    },
)
print(f"Status: {resp.status_code}")
print(f"CT: {resp.headers.get('Content-Type','')}")
print(f"Body ({len(resp.text)} chars):")
print(resp.text[:2000])

# Try with different accept header
print("\n=== School autocomplete (JSON) ===")
resp2 = c.session.get(
    f"{c.BASE}/settings/education/developer_pack_applications/schools",
    params={"q": "SKT"},
    headers={
        **c.HEADERS,
        "Accept": "application/json",
    },
)
print(f"Status: {resp2.status_code}")
print(f"CT: {resp2.headers.get('Content-Type','')}")
print(f"Body: {resp2.text[:1000]}")

# Now try submitting the initial form
print("\n=== Submit initial form ===")
resp = c.get("/settings/education/developer_pack_applications/new")
soup = BeautifulSoup(resp.text, "html.parser")
form = soup.find("form", {"action": "/settings/education/developer_pack_applications"})
if not form:
    print("  Form not found!")
else:
    # Extract form fields
    data = {}
    for inp in form.find_all("input"):
        name = inp.get("name")
        if name and inp.get("type") != "submit":
            data[name] = inp.get("value", "")
    for sel in form.find_all("select"):
        name = sel.get("name")
        if name:
            opt = sel.find("option", selected=True)
            data[name] = opt.get("value", "") if opt else ""
    
    # Fill in the form
    data["dev_pack_form[application_type]"] = "student"
    data["dev_pack_form[school_name]"] = "SKT International College"
    data["dev_pack_form[school_email]"] = "thawkhant.1280@gmail.com"
    data["dev_pack_form[latitude]"] = "16.8661"
    data["dev_pack_form[longitude]"] = "96.1951"
    data["dev_pack_form[location_shared]"] = "true"
    data["dev_pack_form[form_variant]"] = "initial_form"
    
    print(f"  Data: {json.dumps(data, indent=2)}")
    
    time.sleep(2)
    resp2 = c.post(
        "/settings/education/developer_pack_applications",
        data=data,
        allow_redirects=False,
    )
    print(f"\n  Status: {resp2.status_code}")
    print(f"  Location: {resp2.headers.get('Location', 'none')}")
    print(f"  CT: {resp2.headers.get('Content-Type', '')}")
    
    if resp2.status_code == 200:
        # Might return the next step form
        soup2 = BeautifulSoup(resp2.text, "html.parser")
        with open("edu_step2.html", "w", encoding="utf-8") as f:
            f.write(resp2.text)
        print("  Saved edu_step2.html")
        
        text = soup2.get_text(separator="\n", strip=True)
        lines = [l for l in text.split("\n") if l.strip()]
        print(f"\n  Response content ({len(lines)} lines):")
        for line in lines[:60]:
            print(f"    {line[:150]}")
        
        # Find forms in response
        forms = soup2.find_all("form")
        for f2 in forms:
            action = f2.get("action", "")
            if action:
                print(f"\n  Form: action={action}")
                for inp in f2.find_all(["input", "select", "textarea"]):
                    name = inp.get("name", "")
                    val = inp.get("value", "")[:60]
                    typ = inp.get("type", inp.name)
                    if name:
                        print(f"    {typ}: {name} = {val}")
    elif resp2.status_code in (301, 302):
        loc = resp2.headers.get("Location", "")
        print(f"  Following redirect to: {loc}")
        resp3 = c.get(loc)
        with open("edu_step2.html", "w", encoding="utf-8") as f:
            f.write(resp3.text)
        print(f"  Saved edu_step2.html ({resp3.status_code})")
    else:
        print(f"  Body: {resp2.text[:500]}")
