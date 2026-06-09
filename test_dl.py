import requests

r = requests.get(
    "https://ui-avatars.com/api/?name=TW&size=256&background=0D8ABC&color=fff&bold=true&format=png",
    timeout=15
)
print(f"Status: {r.status_code}")
print(f"Size: {len(r.content)} bytes")
print(f"Content-Type: {r.headers.get('content-type')}")
