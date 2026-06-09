"""Find the webcam-upload JS chunk URL."""
import re
from bs4 import BeautifulSoup

# Check the full page HTML for JS assets
with open("edu_try2_200.html", "r", encoding="utf-8") as f:
    html = f.read()

# Find all asset URLs
pattern = re.compile(r'https://github\.githubassets\.com/assets/[^\s"\'<>]+\.js', re.I)
js_urls = set(pattern.findall(html))
print(f"JS files found: {len(js_urls)}")
for url in sorted(js_urls):
    name = url.split("/")[-1]
    print(f"  {name}")

# Also look for chunk mappings
print("\n=== Chunk/import map references ===")
# Look for import maps or chunk loading code
import_pattern = re.compile(r'"([^"]+)":\s*"([a-f0-9]{16,})"')
for m in import_pattern.finditer(html):
    name = m.group(1)
    hash_val = m.group(2)
    if "webcam" in name.lower() or "upload" in name.lower() or "education" in name.lower():
        print(f"  {name}: {hash_val}")

# Check for webcam in any context
print("\n=== 'webcam' references ===")
for m in re.finditer(r'.{0,80}webcam.{0,80}', html, re.I):
    print(f"  {m.group()[:160]}")

# Check all link/script tags
print("\n=== All link stylesheets ===")
soup = BeautifulSoup(html, "html.parser")
for link in soup.find_all("link", rel="stylesheet"):
    href = link.get("href", "")
    if "webcam" in href.lower() or "upload" in href.lower():
        print(f"  {href}")

# Look at the main app bundle reference  
print("\n=== Main app bundles ===")
for script in soup.find_all("script", src=True):
    src = script.get("src", "")
    name = src.split("/")[-1]
    if "app" in name.lower() or "vendor" in name.lower() or "main" in name.lower() or "react" in name.lower():
        print(f"  {name}")
        print(f"  {src}")

# Check modulepreload
for link in soup.find_all("link", rel="modulepreload"):
    href = link.get("href", "")
    name = href.split("/")[-1] 
    print(f"  preload: {name}")
