"""Quick check for script tags in saved HTML files."""
import re, os

files = ["edu_form.html", "edu_form_full.html", "edu_benefits.html", "profile_page.html"]
for fname in files:
    if not os.path.exists(fname):
        continue
    html = open(fname, "r", encoding="utf-8").read()
    scripts = re.findall(r'<script[^>]*src="([^"]*)"', html)
    has_head = "<head>" in html[:1000]
    print(f"{fname}: {len(html)} bytes, {len(scripts)} script src tags, has_head={has_head}")
    for s in scripts[:3]:
        print(f"  {s[:100]}")
