"""Deep analysis of Education Benefits page."""
import re
from bs4 import BeautifulSoup

with open("edu_benefits.html", "r", encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")

# Search for custom elements related to education
print("=== Custom elements ===")
for tag in soup.find_all(True):
    if "-" in tag.name:
        attrs_str = " ".join(f"{k}={str(v)[:80]}" for k, v in tag.attrs.items())
        if any(kw in tag.name.lower() or kw in attrs_str.lower() 
               for kw in ["education", "student", "school", "application", "benefit", "discount"]):
            print(f"  <{tag.name}> {attrs_str[:200]}")

# Search for data attributes
print("\n=== Data attributes with education/student ===")
for tag in soup.find_all(True):
    for attr, val in tag.attrs.items():
        if isinstance(val, str) and any(kw in val.lower() for kw in ["education", "student", "school", "application", "discount"]):
            if attr.startswith("data-"):
                print(f"  <{tag.name}>[{attr}] = {val[:120]}")

# Search for script tags with education content
print("\n=== Scripts with education ===")
for script in soup.find_all("script"):
    src = script.get("src", "")
    text = script.string or ""
    if "education" in src.lower() or "education" in text.lower()[:500]:
        if src:
            print(f"  src: {src}")
        else:
            print(f"  inline ({len(text)} chars): {text[:200]}")

# Look for react-partial elements
print("\n=== React partials ===")
for rp in soup.find_all("react-partial"):
    name = rp.get("partial-name", "")
    print(f"  partial: {name}")
    # Check for data in script tags inside
    for sc in rp.find_all("script"):
        if sc.get("type") == "application/json":
            data = sc.string or ""
            print(f"    JSON ({len(data)} chars): {data[:300]}")

# Look for turbo-frame or include-fragment
print("\n=== Turbo/Fragment ===")
for tag in soup.find_all(["turbo-frame", "include-fragment"]):
    src = tag.get("src", "")
    tid = tag.get("id", "")
    print(f"  <{tag.name}> id={tid} src={src}")

# Find any URLs related to education
print("\n=== URLs in HTML ===")
urls = re.findall(r'(?:src|href|action|url|data-url|data-src)="([^"]*(?:education|student|school|discount|benefit)[^"]*)"', html, re.I)
for u in urls:
    print(f"  {u}")

# Look at all link/script assets
print("\n=== Education-related assets ===")
for tag in soup.find_all(["script", "link"]):
    src = tag.get("src", tag.get("href", ""))
    if src and "education" in src.lower():
        print(f"  <{tag.name}> {src}")
