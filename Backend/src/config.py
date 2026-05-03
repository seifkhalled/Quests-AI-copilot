import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Slack App Credentials
    APP_ID = os.environ.get("APP_ID")
    CLIENT_ID = os.environ.get("ClientID")
    CLIENT_SECRET = os.environ.get("ClientSecret")
    SIGNING_SECRET = os.environ.get("Signing_Secret")
    VERIFICATION_TOKEN = os.environ.get("Verification_Token")
    
    # Tokens
    SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
    SLACK_APP_TOKEN = os.environ.get("SLACK_APP_TOKEN")
    
    # Qdrant (Optional)
    QDRANT_URL = os.environ.get("QDRANT_URL")
    QDRANT_API_KEY = os.environ.get("QDRANT_API_KEY")
    
    @classmethod
    def validate_slack_tokens(cls):
        """Validate that required Slack tokens are present"""
        if not cls.SLACK_BOT_TOKEN:
            raise ValueError("Missing SLACK_BOT_TOKEN in environment")
        if not cls.SLACK_APP_TOKEN:
            raise ValueError("Missing SLACK_APP_TOKEN in environment")
        return True
