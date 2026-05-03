import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db import supabase


async def test_slack_message_save():
    """Test saving a Slack message to database."""
    
    print("Testing Slack message save to database...")
    
    # Test save a sample message
    from src.slack_listener import save_slack_message
    
    result = await save_slack_message(
        channel_id="C12345",
        channel_name="test-channel",
        user_id="U12345",
        text="This is a test message from Slack listener",
        ts="1234567890.123456",
        thread_ts=None,
    )
    
    print(f"Result: {result}")
    
    # Check if it was saved
    documents = await supabase.supabase_client.fetch(
        "SELECT * FROM documents ORDER BY created_at DESC LIMIT 5"
    )
    
    print(f"\nRecent documents in DB:")
    for doc in documents:
        print(f"  - {doc.get('title')} ({doc.get('source_type')}) - Status: {doc.get('status')}")
    
    return result


if __name__ == "__main__":
    result = asyncio.run(test_slack_message_save())
    print(f"\nTest {'PASSED' if result and result.get('status') in ['created', 'duplicate'] else 'FAILED'}")