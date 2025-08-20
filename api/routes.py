from fastapi import APIRouter
from auth.ebay_oauth import get_access_token

router = APIRouter()


@router.get("/ebay/token")
def fetch_token():
    token, expires_at = get_access_token()
    return {"access_token": token, "expires_at": expires_at}


@router.get("/health")
def health_check():
    return {"status": "ok"}
