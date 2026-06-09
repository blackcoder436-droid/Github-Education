from bs4 import BeautifulSoup

html = open("pw_final_result.html", "r", encoding="utf-8").read()
soup = BeautifulSoup(html, "html.parser")

# Find ALL validation error messages (color-fg-danger)
print("=== All danger/error elements ===")
for el in soup.find_all(class_=lambda c: c and ("danger" in str(c) or "error" in str(c) or "invalid" in str(c))):
    text = el.get_text(strip=True)
    if text:
        parent_name = ""
        for p in el.parents:
            if p.get("id"):
                parent_name = p.get("id")
                break
            if p.name in ("action-menu", "div") and p.get("class"):
                parent_name = f"{p.name}.{' '.join(p['class'][:2])}"
                break
        print(f"  [{parent_name}] {text[:200]}")

# Find the webcam-upload / photo_proof container
print("\n=== Photo proof container ===")
pp = soup.find(id="photo_proof")
if pp:
    # Walk up to find parent form group
    parent = pp.parent
    for i in range(5):
        if parent:
            classes = parent.get("class", [])
            text = parent.get_text(strip=True)[:200]
            print(f"  parent {i}: <{parent.name} class='{' '.join(classes)}'> text={text[:100]}")
            # Check for error
            err = parent.find(class_=lambda c: c and "danger" in str(c))
            if err:
                print(f"    ERROR: {err.get_text(strip=True)}")
            parent = parent.parent

# Check the Banner content more carefully
print("\n=== Banner full content ===")
banner = soup.find("x-banner")
if banner:
    print(banner.get_text(strip=True)[:500])

# Check form fields that have validation errors
print("\n=== aria-describedby with validation ===")
for el in soup.find_all(attrs={"aria-describedby": True}):
    desc = el.get("aria-describedby", "")
    if "validation" in desc:
        name = el.get("name", el.name)
        print(f"  {name}: aria-describedby={desc}")
        # Find the validation element
        for vid in desc.split():
            if "validation" in vid:
                vel = soup.find(id=vid)
                if vel:
                    print(f"    -> {vel.get_text(strip=True)[:200]}")

# Check if photo_proof has its own required/validation
print("\n=== Photo proof full context ===")
# Find the form group containing photo_proof
for div in soup.find_all("div", class_="FormField"):
    inp = div.find(id="photo_proof")
    if inp:
        print(f"  Found FormField with photo_proof:")
        print(str(div)[:1000])
        break

# Alternatively look for react partial for webcam
react = soup.find("react-partial", attrs={"partial-name": lambda x: x and "webcam" in str(x)})
if react:
    print(f"\n=== React partial (webcam) ===")
    print(str(react)[:500])
