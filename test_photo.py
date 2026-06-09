import requests, random

# Test randomuser.me portrait download
num = random.randint(1, 99)
url = f"https://randomuser.me/api/portraits/men/{num}.jpg"
print(f"URL: {url}")
r = requests.get(url, timeout=15)
print(f"Status: {r.status_code}")
print(f"Size: {len(r.content)} bytes")
ct = r.headers.get("content-type", "")
print(f"Type: {ct}")
