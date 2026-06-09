"""Deep inspect form HTML for hidden fields and JS behavior."""
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
resp = c.get("/settings/education/developer_pack_applications/new")
soup = BeautifulSoup(resp.text, "html.parser")

# Save full form HTML
form = soup.find("form", {"action": "/settings/education/developer_pack_applications"})
if form:
    with open("edu_form_full.html", "w", encoding="utf-8") as f:
        f.write(str(form))
    print(f"Saved form HTML ({len(str(form))} bytes)")

# Check for React/JS data
print("\n=== React/JS embedded data ===")
for script in soup.find_all("script", {"data-target": "react-partial.embeddedData"}):
    data = script.get_text(strip=True)
    if data:
        try:
            j = json.loads(data)
            print(json.dumps(j, indent=2)[:2000])
        except:
            print(f"Raw: {data[:500]}")

# Check for custom elements
print("\n=== Custom elements ===")
for el in soup.find_all(re.compile(r"^[a-z]+-")):
    if el.name not in ("turbo-frame", "tool-tip"):
        attrs = {k:v for k,v in el.attrs.items()}
        print(f"  <{el.name}> attrs={attrs}")

# Check all data-action attributes (event bindings)
print("\n=== Data actions (JS event handlers) ===")
if form:
    for el in form.find_all(True, attrs={"data-action": True}):
        action = el.get("data-action")
        name = el.get("name", "")
        print(f"  {el.name}: action='{action}' name='{name}'")

# Check submit button
print("\n=== Submit button ===")
if form:
    for btn in form.find_all("button"):
        print(f"  button: name={btn.get('name')} type={btn.get('type')} text='{btn.get_text(strip=True)}'")
        for k,v in btn.attrs.items():
            if k.startswith("data-"):
                print(f"    {k}={v}")

# Check turbo-frame structure
print("\n=== Turbo frames ===")
for tf in soup.find_all("turbo-frame"):
    print(f"  id={tf.get('id')} src={tf.get('src')}")

# Check if form has data attributes
if form:
    print(f"\n=== Form attributes ===")
    for k,v in form.attrs.items():
        print(f"  {k}={v}")

# Check if there's a separate application ID or something
print("\n=== URL patterns in page ===")
for a in soup.find_all("a"):
    href = a.get("href", "")
    if "education" in href or "developer_pack" in href:
        print(f"  {href}")

# Look for the school name field + related hidden inputs more carefully
print("\n=== School name area ===")
if form:
    ac = form.find("auto-complete")
    if ac:
        print(f"  auto-complete: {dict(ac.attrs)}")
        parent = ac.parent
        if parent:
            # Find all inputs in the autocomplete parent section
            for inp in parent.find_all("input"):
                print(f"    input: name={inp.get('name')} type={inp.get('type')} value={inp.get('value','')[:50]}")
