import requests
import sys

url = "http://localhost:8000/api/ingest/file"
pdf_path = r"E:\Quests-AI-copilot\Backend\data\quest-70-details.pdf"

try:
    with open(pdf_path, "rb") as f:
        files = {"file": ("quest-70-details.pdf", f, "application/pdf")}
        response = requests.post(url, files=files, timeout=120)
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json() if response.headers.get('content-type') == 'application/json' else response.text}")
    
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
