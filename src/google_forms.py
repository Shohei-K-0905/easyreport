import requests
from config import settings

# Google Form ID from environment
FORM_ID = settings.GOOGLE_FORM_ID
# Entry field env var keys and corresponding entry IDs
ENTRY_ENV_KEYS = [key for key in settings.dict().keys() if key.startswith("GOOGLE_ENTRY")]


def submit_google_form(responses: dict[str, str]) -> requests.Response:
    """
    Submit responses to Google Form. 
    'responses' keys should match ENTRY_ENV_KEYS (e.g. 'GOOGLE_ENTRY_1').
    """
    form_url = f"https://docs.google.com/forms/d/e/{FORM_ID}/formResponse"
    # Map entry IDs to provided answers
    data = {
        getattr(settings, key): responses[key]
        for key in ENTRY_ENV_KEYS
        if key in responses
    }
    response = requests.post(form_url, data=data)
    response.raise_for_status()
    return response
