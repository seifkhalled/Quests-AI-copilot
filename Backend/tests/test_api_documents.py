import requests

response = requests.get("http://localhost:8000/api/documents")
print(f"Status: {response.status_code}")
print(f"Text: {response.text[:500]}")