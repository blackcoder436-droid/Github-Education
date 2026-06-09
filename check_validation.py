"""Check field-level validation errors in the step 2 response."""
import re
from bs4 import BeautifulSoup

with open("edu_final_200.html", "r", encoding="utf-8") as f:
    soup = BeautifulSoup(f.read(), "html.parser")

# Find all validation/error elements  
print("=== Validation elements ===")
for el in soup.find_all(True, class_=re.compile(r"FormControl-inlineValidation|invalid|danger")):
    text = el.get_text(strip=True)[:200]
    hidden = el.get("hidden")
    # Find nearest named ancestor
    parent_name = ""
    p = el.parent
    while p:
        n = p.get("name") if hasattr(p, "get") else None
        if n:
            parent_name = n
            break
        p = p.parent if hasattr(p, "parent") else None
    print(f"  hidden={hidden} parent={parent_name} text='{text[:100]}'")

# Check what the form looks like
print("\n=== Form fields with values ===")
form = soup.find("form", action=re.compile(r"developer_pack"))
if form:
    for inp in form.find_all("input"):
        name = inp.get("name", "")
        val = inp.get("value", "")[:80]
        typ = inp.get("type", "text")
        if name:
            print(f"  {typ}: {name} = '{val}'")

# Check specifically the proof_type hidden input value
print("\n=== proof_type hidden input ===")
proof_input = soup.find("input", {"name": "dev_pack_form[proof_type]"})
if proof_input:
    print(f"  value='{proof_input.get('value','')}'")
    print(f"  attrs={dict(proof_input.attrs)}")

# Check photo_proof hidden input
print("\n=== photo_proof hidden input ===")
photo_input = soup.find("input", {"name": "dev_pack_form[photo_proof]"})
if photo_input:
    val = photo_input.get("value", "")
    print(f"  value length={len(val)}")
    print(f"  value preview='{val[:100]}'")

# Check the error banner HTML
print("\n=== Error banners ===")
for banner in soup.find_all(class_=re.compile(r"Banner--error|flash-error")):
    text = banner.get_text(strip=True)[:300]
    print(f"  {text}")

# Check the photo_proof section more carefully
print("\n=== Photo proof section ===")
if photo_input:
    # Go up to find the containing div
    container = photo_input.parent
    while container and container.get("class") != ["d-none"]:
        container = container.parent
    if container:
        # Find sibling that has validation
        for sib in container.find_next_siblings():
            text = sib.get_text(strip=True)[:200]
            if text:
                print(f"  sibling: {text}")
            if "required" in text.lower() or "error" in text.lower():
                print(f"    VALIDATION ERROR FOUND!")
                break

# Print all visible text with errors
print("\n=== All visible error messages ===")
text_content = soup.get_text(separator="\n", strip=True)
for line in text_content.split("\n"):
    if "required" in line.lower() or "error" in line.lower() or "fix" in line.lower():
        print(f"  {line.strip()[:150]}")
