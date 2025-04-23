import requests
from config import settings

# Microsoft Teams incoming webhook URL
WEBHOOK_URL = settings.TEAMS_WEBHOOK_URL

def send_teams_message(message: str, webhook_url: str = WEBHOOK_URL):
    """
    Send a plaintext message to Microsoft Teams via incoming webhook.
    """
    payload = {"text": message}
    response = requests.post(webhook_url, json=payload)
    response.raise_for_status()
    return response
