import base64
from urllib.parse import unquote

import requests
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from auth.ebay_oauth import get_access_token
from configs.config import EBAY_CLIENT_ID, EBAY_CLIENT_SECRET, EBAY_REDIRECT_URI

router = APIRouter()


@router.get("/ebay/token")
def fetch_token():
    token, expires_at = get_access_token()
    return {"access_token": token, "expires_at": expires_at}


@router.get("/health")
def health_check():
    return {"status": "ok"}


@router.get("/callback")
def callback(code: str = None):
    if not code:
        return JSONResponse(content={"error": "Missing authorization code"}, status_code=400)

    auth = base64.b64encode(f"{EBAY_CLIENT_ID}:{EBAY_CLIENT_SECRET}".encode()).decode()

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {auth}"
    }

    data = {
        "grant_type": "authorization_code",
        "code": unquote(code),
        "redirect_uri": EBAY_REDIRECT_URI
    }

    response = requests.post("https://api.ebay.com/identity/v1/oauth2/token", headers=headers, data=data)

    if response.status_code != 200:
        print("OAuth error (authorization_code):", response.status_code, response.text)

    if response.status_code == 200:
        tokens = response.json()
        return JSONResponse(content=tokens)
    else:
        return JSONResponse(content={"error": response.text}, status_code=response.status_code)


@router.post("/deletion-notification")
async def deletion_notification(request: Request):
    try:
        data = await request.json()
    except Exception:
        data = {"raw": await request.body()}

    print("Received deletion notification:", data)
    return {"status": "ok"}
