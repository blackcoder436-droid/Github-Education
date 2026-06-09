import re

html = open("pw_final_result.html", "r", encoding="utf-8").read()

# Find Banner content
for m in re.finditer(r'class="[^"]*Banner[^"]*"[^>]*>(.*?)</div>', html, re.DOTALL):
    text = re.sub(r'<[^>]+>', ' ', m.group(1)).strip()
    if text:
        print(f"BANNER: {text[:300]}")

# Find flash messages
for m in re.finditer(r'class="[^"]*flash[^"]*"[^>]*>(.*?)</div>', html, re.DOTALL):
    text = re.sub(r'<[^>]+>', ' ', m.group(1)).strip()
    if text:
        print(f"FLASH: {text[:300]}")

# Find any "required" text
for m in re.finditer(r'[^<]{0,50}required[^<]{0,100}', html, re.I):
    print(f"REQUIRED: {m.group().strip()[:200]}")

# Find "cannot be reviewed"
for m in re.finditer(r'[^<]{0,50}cannot be reviewed[^<]{0,200}', html, re.I):
    print(f"CANNOT: {m.group().strip()[:300]}")

# Find the proof_type hidden input value
for m in re.finditer(r'name="dev_pack_form\[proof_type\]"[^>]*>', html):
    print(f"PROOF_TYPE input: {m.group()[:200]}")
    
# Find the photo_proof input value
for m in re.finditer(r'name="dev_pack_form\[photo_proof\]"[^>]*>', html):
    print(f"PHOTO_PROOF input: {m.group()[:200]}")
for m in re.finditer(r'id="photo_proof"[^>]*>', html):
    print(f"PHOTO_PROOF id input: {m.group()[:200]}")

# Find the form_variant
for m in re.finditer(r'name="dev_pack_form\[form_variant\]"[^>]*>', html):
    print(f"FORM_VARIANT input: {m.group()[:200]}")

# Check if still showing step 2 form or somewhere else
if 'upload_proof_form' in html:
    print("\nStill showing step 2 form (upload_proof_form present)")
if 'initial_form' in html:
    print("initial_form also present")
    
# Check the form action
for m in re.finditer(r'<form[^>]*action="[^"]*developer_pack[^"]*"[^>]*>', html):
    print(f"\nFORM tag: {m.group()[:300]}")
