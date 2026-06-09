import re
from bs4 import BeautifulSoup

html = open("pw_final_result.html", "r", encoding="utf-8").read()
soup = BeautifulSoup(html, "html.parser")

# Find action-menu and its contents
am = soup.find("action-menu")
if am:
    print("=== action-menu found ===")
    # Find hidden input
    hidden = am.find("input", {"name": "dev_pack_form[proof_type]"})
    if hidden:
        print(f"Hidden input: {hidden}")
        print(f"  value attr: {hidden.get('value', '(NO VALUE ATTR)')}")
    # Find the validation error
    val_err = am.find(class_=lambda c: c and "danger" in c)
    if val_err:
        print(f"Validation error: {val_err.text.strip()}")
    print(f"\nFull action-menu HTML (first 2000 chars):")
    print(str(am)[:2000])

# Also check if there's a separate validation element
print("\n\n=== Validation messages ===")
for el in soup.find_all(class_=lambda c: c and "validation" in str(c)):
    print(f"  {el.get('id', '')} -> {el.text.strip()[:100]}")

# Check the proof_type input in the RESPONSE (after submission, server re-rendered the form)
print("\n\n=== All proof_type inputs ===")
for inp in soup.find_all("input", {"name": "dev_pack_form[proof_type]"}):
    print(f"  value={inp.get('value', '(NONE)')}, type={inp.get('type')}, id={inp.get('id')}")

# Check photo_proof 
print("\n=== All photo_proof inputs ===")  
for inp in soup.find_all("input", {"name": "dev_pack_form[photo_proof]"}):
    print(f"  value={inp.get('value', '(NONE)')[:80]}, type={inp.get('type')}, id={inp.get('id')}")

# Check form_variant
print("\n=== All form_variant inputs ===")
for inp in soup.find_all("input", {"name": "dev_pack_form[form_variant]"}):
    print(f"  value={inp.get('value', '(NONE)')}, type={inp.get('type')}, id={inp.get('id')}")

# Check if there's a selected item in action-menu
print("\n=== Selected items in action-menu ===")
for btn in soup.find_all("button", {"role": "menuitemradio"}):
    checked = btn.get("aria-checked", "false")
    dv = btn.get("data-value", "")
    if checked == "true":
        print(f"  SELECTED: {dv}")
    else:
        print(f"  unchecked: {dv[:60]}")
