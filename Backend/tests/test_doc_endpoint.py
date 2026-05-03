import requests
import json

doc_id = "0a55777e-c7ad-4a44-a52f-186a8e579025"
url = f"http://localhost:8002/api/documents/{doc_id}"
print(f"Calling: {url}")
try:
    r = requests.get(url, timeout=5)
    print(f"Status: {r.status_code}")
    print(f"Response: {r.text}")
except Exception as e:
    print(f"Error: {e}")