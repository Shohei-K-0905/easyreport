import os
import json
import requests
from msal import ConfidentialClientApplication
from config import settings

# Acquire token for Microsoft Graph
CLIENT_ID = settings.MS_CLIENT_ID
TENANT_ID = settings.MS_TENANT_ID
CLIENT_SECRET = settings.MS_CLIENT_SECRET

AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPE = ["https://graph.microsoft.com/.default"]

app = ConfidentialClientApplication(
    client_id=CLIENT_ID,
    client_credential=CLIENT_SECRET,
    authority=AUTHORITY,
)

# Token cache can be implemented here or left default

def get_access_token():
    """
    Acquire access token for Graph API.
    """
    result = app.acquire_token_silent(SCOPE, account=None)
    if not result:
        result = app.acquire_token_for_client(scopes=SCOPE)
    if "access_token" in result:
        return result["access_token"]
    else:
        raise Exception(f"Could not acquire token: {result.get('error_description')}")


def update_excel_sheet(file_url: str, sheet_name: str, values: list[list[str]]):
    """
    Update rows in an Excel sheet stored in SharePoint/Teams.
    values: 2D list representing CSV rows. First row is header.
    """
    access_token = get_access_token()
    endpoint = f"https://graph.microsoft.com/v1.0/me/drive/root:/{file_url}:/workbook/worksheets/{sheet_name}/range(address='A1')"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    body = {"values": values}
    response = requests.patch(endpoint, headers=headers, json=body)
    response.raise_for_status()
    return response.json()
