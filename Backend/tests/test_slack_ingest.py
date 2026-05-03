import requests
import json

def test_slack_ingestion():
    url = "http://localhost:8002/api/ingest/source"
    payload = {
        "source_type": "slack",
        "content": "Hello team, I'm testing if Slack messages are correctly embedded and passed into our pipeline.",
        "title": "Slack Msg - Test User",
        "metadata": {
            "channel_id": "C_TEST_CHANNEL",
            "user": "U_TEST_USER"
        }
    }
    
    print(f"Testing {url} with payload:\n{json.dumps(payload, indent=2)}\n")
    
    try:
        response = requests.post(url, json=payload)
        
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("Success! Response JSON:")
            print(json.dumps(response.json(), indent=2))
        else:
            print("Failed! Response Text:")
            print(response.text)
            
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to the server. Is it running on http://localhost:8002 ?")
        print("Please make sure to restart your FastAPI server to pick up the recent code changes.")

if __name__ == "__main__":
    test_slack_ingestion()
