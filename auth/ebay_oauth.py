import base64
import logging
import time
import requests
from configs.config import EBAY_CLIENT_ID, EBAY_CLIENT_SECRET, EBAY_REFRESH_TOKEN

EBAY_OAUTH_URL = "https://api.ebay.com/identity/v1/oauth2/token"

_access_token = None
_expires_at = 0  # timestamp

def get_access_token():
    global _access_token, _expires_at
    now = int(time.time())
    if _access_token and now < _expires_at:
        return _access_token
    return _request_new_access_token()

def _request_new_access_token():
    global _access_token, _expires_at

    auth = base64.b64encode(f"{EBAY_CLIENT_ID}:{EBAY_CLIENT_SECRET}".encode()).decode()
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {auth}"
    }
    data = {
        "grant_type": "refresh_token",
        "refresh_token": EBAY_REFRESH_TOKEN,
        "scope": (
            "https://api.ebay.com/oauth/api_scope "
            "https://api.ebay.com/oauth/api_scope/sell.inventory "
            "https://api.ebay.com/oauth/api_scope/sell.account"
        )
    }

    response = requests.post(EBAY_OAUTH_URL, headers=headers, data=data, timeout=15)
    response.raise_for_status()

    tokens = response.json()
    _access_token = tokens["access_token"]
    expires_in = tokens.get("expires_in", 7200)
    _expires_at = int(time.time()) + expires_in - 60

    logging.info(f"New eBay access token received, valid {expires_in} sec")
    return _access_token
