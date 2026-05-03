import asyncio
from fastapi.testclient import TestClient
from main import app
from src.db.supabase_client import get_supabase
import uuid

client = TestClient(app)
sb = get_supabase()

def run_checks():
    print("--- Starting Checks 4 to 8 ---")
    
    # Setup: Create a new user and conversation
    user_id = str(uuid.uuid4())
    conv_id = str(uuid.uuid4())
    
    # Mocking conversation creation since we are directly inserting
    sb.table("conversations").insert({
        "id": conv_id,
        "user_id": user_id,
        "scope": "global",
        "status": "active"
    }).execute()
    print(f"Created conversation: {conv_id} for user: {user_id}")

    # --- Check 4 ---
    print("\n[Check 4] Send a test message")
    response = client.post("/api/chat", json={
        "conversation_id": conv_id,
        "user_id": user_id,
        "message": "What backend quests are available?"
    })
    
    if response.status_code != 200:
        print(f"FAILED Check 4: Status code {response.status_code}")
        print(response.json())
        return
        
    data = response.json()
    print(f"Response Intent: {data.get('intent')}")
    print(f"Answer: {data.get('answer')[:100]}...")
    
    # Verify DB has 2 rows
    msgs = sb.table("messages").select("*").eq("conversation_id", conv_id).execute()
    print(f"DB Message count: {len(msgs.data)}")
    if len(msgs.data) != 2 or data.get('intent') != 'quest_search':
        print("FAILED Check 4 assertion")
    else:
        print("PASS Check 4")

    # --- Check 5 ---
    print("\n[Check 5] Context window sliding")
    # Send 5 more messages to reach 6 total
    for i in range(2, 7):
        print(f"Sending message {i}/6...")
        client.post("/api/chat", json={
            "conversation_id": conv_id,
            "user_id": user_id,
            "message": f"This is message number {i}"
        })
        
    res = client.get(f"/api/chat/{conv_id}/messages?user_id={user_id}")
    data = res.json()
    msg_count = data.get("message_count", 0)
    print(f"Total messages returned by endpoint: {msg_count}")
    if msg_count == 12:
        print("PASS Check 5")
    else:
        print("FAILED Check 5: Expected 12")

    # --- Check 6 ---
    print("\n[Check 6] End conversation")
    res = client.post(f"/api/chat/{conv_id}/end?user_id={user_id}")
    print(f"End conversation response: {res.json()}")
    
    conv_check = sb.table("conversations").select("status").eq("id", conv_id).single().execute()
    print(f"DB status: {conv_check.data.get('status')}")
    
    res_after = client.post("/api/chat", json={
        "conversation_id": conv_id,
        "user_id": user_id,
        "message": "Are you there?"
    })
    print(f"Post-end message status code: {res_after.status_code}")
    print(f"Post-end message response: {res_after.json()}")
    if res_after.status_code == 400 and conv_check.data.get('status') == 'ended':
        print("PASS Check 6")
    else:
        print("FAILED Check 6")

    # --- Check 7 ---
    print("\n[Check 7] Insight written on insight_request")
    new_conv_id = str(uuid.uuid4())
    sb.table("conversations").insert({
        "id": new_conv_id,
        "user_id": user_id,
        "scope": "global",
        "status": "active"
    }).execute()
    
    res = client.post("/api/chat", json={
        "conversation_id": new_conv_id,
        "user_id": user_id,
        "message": "What tech stacks appear most often across all the quests?"
    })
    data = res.json()
    print(f"Intent: {data.get('intent')}")
    print(f"Confidence: {data.get('confidence')}")
    
    # Check insights table
    insights = sb.table("insights").select("*").order("generated_at", desc=True).limit(1).execute()
    if insights.data:
        latest = insights.data[0]
        print(f"Latest insight found: {latest.get('title')}")
        print("PASS Check 7")
    else:
        print("No insight found in DB")
        print("FAILED Check 7")

if __name__ == "__main__":
    run_checks()
