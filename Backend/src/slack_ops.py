import requests
import os
from src.core.config import settings

class SlackOps:
    """Utility class for Slack-specific operations like downloading files."""
    
    def __init__(self, token: str = None):
        self.token = token or settings.SLACK_BOT_TOKEN
        if not self.token:
            raise ValueError("SLACK_BOT_TOKEN is required for SlackOps")

    def download_file(self, url: str) -> bytes:
        """
        Download a file from Slack using the bot token for authentication.
        """
        if not self.token:
            raise ValueError("No SLACK_BOT_TOKEN found in settings")

        headers = {"Authorization": f"Bearer {self.token}"}
        
        # We must follow redirects but keep the header
        response = requests.get(url, headers=headers, allow_redirects=True)
        
        if response.status_code != 200:
            raise Exception(f"Failed to download file from Slack: {response.status_code} {response.text}")
            
        # Check if we got HTML instead of the file (means we were redirected to login)
        content_type = response.headers.get("Content-Type", "")
        if "text/html" in content_type:
            # Check for a specific Slack error in the HTML or just fail
            if "login" in response.text.lower():
                raise Exception("Slack redirected to login page. Please check if your Bot has 'files:read' scope and is invited to the channel.")
            
        return response.content
