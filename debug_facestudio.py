#!/usr/bin/env python3
"""Debug Face Studio API - check different endpoints and methods."""

import os
import requests
from pathlib import Path

print("=" * 70)
print("Face Studio API Debug")
print("=" * 70)

api_key = os.environ.get("FACESTUDIO_API_KEY", "").strip()

if not api_key:
    print("\nx FACESTUDIO_API_KEY environment variable not set")
    print("  Set it: $env:FACESTUDIO_API_KEY='your-key'")
    exit(1)

print(f"\nAPI Key: {api_key[:15]}...")
print("\n" + "-" * 70)

# Test different endpoints and methods
tests = [
    # (name, method, url, headers, data)
    ("GET /v1/generate", "GET", "https://facestud.io/v1/generate", 
     {"Authorization": f"Bearer {api_key}"}, None),
    
    ("POST /v1/generate (JSON)", "POST", "https://facestud.io/v1/generate",
     {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
     {}),
    
    ("POST /v1/generate (Form)", "POST", "https://facestud.io/v1/generate",
     {"Authorization": f"Bearer {api_key}"},
     None),
    
    ("GET /api/generate", "GET", "https://facestud.io/api/generate",
     {"Authorization": f"Bearer {api_key}"}, None),
    
    ("GET without Bearer", "GET", "https://facestud.io/v1/generate",
     {"X-API-Key": api_key}, None),
    
    ("POST with query param", "POST", "https://facestud.io/v1/generate?format=jpg",
     {"Authorization": f"Bearer {api_key}"}, None),
]

for i, (name, method, url, headers, data) in enumerate(tests, 1):
    print(f"\n[Test {i}] {name}")
    print(f"  Method: {method}")
    print(f"  URL: {url}")
    print(f"  Headers: {headers}")
    
    try:
        if method == "GET":
            resp = requests.get(url, headers=headers, timeout=10)
        else:  # POST
            if data is not None:
                resp = requests.post(url, json=data, headers=headers, timeout=10)
            else:
                resp = requests.post(url, headers=headers, timeout=10)
        
        print(f"  Status: {resp.status_code}")
        
        if resp.status_code == 200:
            size = len(resp.content)
            print(f"  Response size: {size} bytes")
            
            # Try to identify if it's an image
            if size > 100:
                from io import BytesIO
                from PIL import Image
                try:
                    img = Image.open(BytesIO(resp.content))
                    print(f"  Image: {img.format} {img.width}x{img.height}")
                    print(f"  ✓ SUCCESS!")
                    
                    # Save it
                    test_dir = Path("test_output")
                    test_dir.mkdir(exist_ok=True)
                    save_path = test_dir / f"facestudio_test_{i}.png"
                    with open(save_path, "wb") as f:
                        f.write(resp.content)
                    print(f"  Saved: {save_path}")
                except:
                    print(f"  Response: {resp.text[:100]}")
            else:
                print(f"  Response: {resp.text}")
        else:
            # Print error details
            try:
                error_json = resp.json()
                print(f"  Error: {error_json}")
            except:
                print(f"  Response: {resp.text[:200]}")
    
    except Exception as e:
        print(f"  Exception: {e}")

print("\n" + "=" * 70)
print("Debug Complete")
print("=" * 70)
