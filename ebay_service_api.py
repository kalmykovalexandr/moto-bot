from __future__ import annotations
import base64
import os
import time
from typing import List, Optional, Dict, Any

import requests
from fastapi import FastAPI, HTTPException, Query, Path
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, Field

# ------------------------------
# Env & constants
# ------------------------------
EBAY_CLIENT_ID = os.getenv("EBAY_CLIENT_ID")
EBAY_CLIENT_SECRET = os.getenv("EBAY_CLIENT_SECRET")
DEFAULT_RUNAME = os.getenv("EBAY_RUNAME")  # eBay Redirect URL name (RuName)
DEFAULT_MARKETPLACE_ID = os.getenv("EBAY_MARKETPLACE_ID", "EBAY_IT")

REQ_TIMEOUT = 20  # seconds

# In-memory store for demo (replace by DB in production)
SELLERS: Dict[str, Dict[str, Any]] = {}

# ------------------------------
# Pydantic models (subset matching your OpenAPI)
# ------------------------------
class OAuthURLResponse(BaseModel):
    url: str
    sellerId: str
    expiresAt: Optional[float]

class TokenResponse(BaseModel):
    access_token: str
    expires_in: int
    refresh_token: Optional[str] = None
    token_type: str = "Bearer"

class SellerConfig(BaseModel):
    sellerId: str
    marketplaceId: str = DEFAULT_MARKETPLACE_ID
    runame: Optional[str] = DEFAULT_RUNAME
    refreshToken: Optional[str] = None
    merchantLocationKey: Optional[str] = None
    paymentPolicyId: Optional[str] = None
    returnPolicyId: Optional[str] = None
    defaultFulfillmentPolicyId: Optional[str] = None
    fpolicyLightId: Optional[str] = None
    fpolicyMediumId: Optional[str] = None
    fpolicyHeavyId: Optional[str] = None
    fpolicyXHeavyId: Optional[str] = None

class Address(BaseModel):
    city: str
    stateOrProvince: str
    postalCode: str
    country: str = Field("IT", description="ISO country code")

class InventoryLocation(BaseModel):
    address: Address
    name: str
    merchantLocationStatus: str = Field("ENABLED", regex="^(ENABLED|DISABLED)$")
    locationInstructions: Optional[str] = None
    locationTypes: List[str] = ["WAREHOUSE"]

class ShipToRegion(BaseModel):
    regionName: str

class ShippingService(BaseModel):
    shippingServiceCode: str
    freeShipping: Optional[bool] = None
    sortOrder: Optional[int] = None
    shipToLocations: Optional[Dict[str, List[ShipToRegion]]] = None

class HandlingTime(BaseModel):
    unit: str = "BUSINESS_DAY"
    value: int = 2

class ShippingOption(BaseModel):
    optionType: str  # DOMESTIC | INTERNATIONAL
    costType: str = "FLAT_RATE"
    rateTableId: Optional[str] = None
    shippingServices: List[ShippingService]
    shipToLocations: Optional[Dict[str, List[ShipToRegion]]] = None

class FulfillmentPolicyCreateRequest(BaseModel):
    marketplaceId: str = DEFAULT_MARKETPLACE_ID
    name: str
    handlingTime: HandlingTime = HandlingTime()
    shippingOptions: List[ShippingOption]
    localPickup: bool = False

class FulfillmentPolicyResponse(BaseModel):
    fulfillmentPolicyId: str
    name: str
    marketplaceId: str

class AIAnalyzeRequest(BaseModel):
    imageUrl: str
    brand: str
    model: str
    year: str

class AIAnalyzeResponse(BaseModel):
    is_motor: bool
    part_type: Optional[str] = None
    part_type_short: Optional[str] = None
    color: Optional[str] = None
    compatible_years: Optional[str] = None
    estimated_weight_kg: Optional[float] = None
    weight_class: Optional[str] = None  # XS/S/M/L/XL

class ShippingPolicySelectionRequest(BaseModel):
    sellerId: str
    weight_class: Optional[str] = None
    estimated_weight_kg: Optional[float] = None

class ShippingPolicySelectionResponse(BaseModel):
    fulfillmentPolicyId: str
    resolvedWeightClass: str

# ------------------------------
# Helpers
# ------------------------------

def _require_env(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise HTTPException(500, f"Missing env var: {name}")
    return v


def _basic_auth_header() -> str:
    cid = _require_env("EBAY_CLIENT_ID")
    csec = _require_env("EBAY_CLIENT_SECRET")
    return base64.b64encode(f"{cid}:{csec}".encode()).decode()


def get_access_token_with_refresh(refresh_token: str, scopes: Optional[str] = None) -> TokenResponse:
    scopes = scopes or " ".join([
        "https://api.ebay.com/oauth/api_scope",
        "https://api.ebay.com/oauth/api_scope/sell.account",
        "https://api.ebay.com/oauth/api_scope/sell.inventory",
    ])
    headers = {
        "Authorization": f"Basic {_basic_auth_header()}",
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
    }
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "scope": scopes,
    }
    r = requests.post("https://api.ebay.com/identity/v1/oauth2/token", headers=headers, data=data, timeout=REQ_TIMEOUT)
    if r.status_code != 200:
        raise HTTPException(r.status_code, f"eBay token error: {r.text}")
    j = r.json()
    return TokenResponse(access_token=j["access_token"], expires_in=j.get("expires_in", 7200), token_type=j.get("token_type", "Bearer"))


def sellers_get(seller_id: str) -> Dict[str, Any]:
    s = SELLERS.get(seller_id)
    if not s:
        raise HTTPException(404, "Seller not found")
    return s


def _bearer(token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# ------------------------------
# FastAPI app
# ------------------------------
app = FastAPI(title="Listing Bot Service API", version="1.0.0")


@app.get("/health")
def health():
    return {"status": "ok"}


# ---------- OAuth ----------
@app.post("/oauth/ebay/url", response_model=OAuthURLResponse)
def build_auth_url(sellerId: str, state: Optional[str] = None):
    # Use seller-specific RuName if present
    seller = SELLERS.get(sellerId, {})
    runame = seller.get("runame") or DEFAULT_RUNAME
    if not runame:
        raise HTTPException(400, "Missing seller RuName or EBAY_RUNAME env")

    scopes = "%20".join([
        "https://api.ebay.com/oauth/api_scope",
        "https://api.ebay.com/oauth/api_scope/sell.account",
        "https://api.ebay.com/oauth/api_scope/sell.inventory",
    ])
    url = (
        "https://auth.ebay.com/oauth2/authorize"
        f"?client_id={EBAY_CLIENT_ID}"
        f"&response_type=code"
        f"&redirect_uri={runame}"
        f"&scope={scopes}"
        f"&state={state or 'state-' + str(int(time.time()))}"
    )
    return OAuthURLResponse(url=url, sellerId=sellerId, expiresAt=time.time() + 600)


@app.get("/oauth/ebay/callback", response_model=TokenResponse)
def oauth_callback(code: str = Query(...), state: Optional[str] = None):
    # Exchange code -> tokens (access + refresh)
    headers = {
        "Authorization": f"Basic {_basic_auth_header()}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": DEFAULT_RUNAME,
    }
    r = requests.post("https://api.ebay.com/identity/v1/oauth2/token", headers=headers, data=data, timeout=REQ_TIMEOUT)
    if r.status_code != 200:
        raise HTTPException(400, f"Error exchanging code: {r.text}")
    j = r.json()
    return TokenResponse(
        access_token=j.get("access_token"),
        refresh_token=j.get("refresh_token"),
        expires_in=j.get("expires_in", 7200),
        token_type=j.get("token_type", "Bearer"),
    )


@app.post("/sellers", response_model=SellerConfig)
def upsert_seller(cfg: SellerConfig):
    SELLERS[cfg.sellerId] = cfg.dict()
    return cfg


@app.get("/sellers/{sellerId}", response_model=SellerConfig)
def get_seller(sellerId: str = Path(...)):
    return SellerConfig(**sellers_get(sellerId))


@app.put("/sellers/{sellerId}", response_model=SellerConfig)
def update_seller(cfg: SellerConfig, sellerId: str = Path(...)):
    if cfg.sellerId != sellerId:
        raise HTTPException(400, "sellerId mismatch")
    SELLERS[cfg.sellerId] = cfg.dict()
    return cfg


@app.post("/sellers/{sellerId}/token/refresh", response_model=TokenResponse)
def refresh_access_token(sellerId: str = Path(...)):
    s = sellers_get(sellerId)
    rt = s.get("refreshToken")
    if not rt:
        raise HTTPException(400, "Seller has no refreshToken")
    return get_access_token_with_refresh(rt)


# ---------- eBay Account: rate tables & shipping services ----------
@app.get("/sellers/{sellerId}/rate-tables")
def list_rate_tables(sellerId: str, country_code: str = Query("IT")):
    token = refresh_access_token(sellerId).access_token
    url = f"https://api.ebay.com/sell/account/v1/rate_table?country_code={country_code}"
    r = requests.get(url, headers=_bearer(token), timeout=REQ_TIMEOUT)
    if r.status_code != 200:
        raise HTTPException(r.status_code, r.text)
    return r.json().get("rateTables", [])


@app.get("/sellers/{sellerId}/shipping-services")
def list_shipping_services(sellerId: str, siteId: int = Query(101)):
    # Trading API SOAP call: GeteBayDetails -> ShippingServiceDetails
    token = refresh_access_token(sellerId).access_token
    soap = f'''<?xml version="1.0" encoding="utf-8"?>
    <GeteBayDetailsRequest xmlns="urn:ebay:apis:eBLBaseComponents">
      <DetailName>ShippingServiceDetails</DetailName>
    </GeteBayDetailsRequest>'''
    headers = {
        "X-EBAY-API-CALL-NAME": "GeteBayDetails",
        "X-EBAY-API-SITEID": str(siteId),
        "X-EBAY-API-IAF-TOKEN": token,
        "Content-Type": "text/xml",
    }
    r = requests.post("https://api.ebay.com/ws/api.dll", headers=headers, data=soap, timeout=REQ_TIMEOUT)
    if r.status_code != 200:
        raise HTTPException(r.status_code, r.text)
    return JSONResponse(content={"raw": r.text})  # парсинг оставим клиенту или допишем позже


# ---------- Inventory location (warehouse) ----------
@app.put("/sellers/{sellerId}/inventory/locations/{merchantLocationKey}")
def create_or_update_location(
    sellerId: str,
    merchantLocationKey: str,
    body: InventoryLocation,
):
    token = refresh_access_token(sellerId).access_token
    url = f"https://api.ebay.com/sell/inventory/v1/location/{merchantLocationKey}"
    r = requests.put(url, headers={**_bearer(token), "Content-Type": "application/json"}, json=body.dict(), timeout=REQ_TIMEOUT)
    if r.status_code not in (200, 204):
        raise HTTPException(r.status_code, r.text)
    return {"status": "updated"}


# ---------- Fulfillment policies ----------
@app.get("/sellers/{sellerId}/fulfillment-policies", response_model=List[FulfillmentPolicyResponse])
def list_policies(sellerId: str):
    token = refresh_access_token(sellerId).access_token
    url = "https://api.ebay.com/sell/account/v1/fulfillment_policy?marketplace_id=EBAY_IT"
    r = requests.get(url, headers=_bearer(token), timeout=REQ_TIMEOUT)
    if r.status_code != 200:
        raise HTTPException(r.status_code, r.text)
    items = r.json().get("fulfillmentPolicies", [])
    out = []
    for p in items:
        out.append(FulfillmentPolicyResponse(
            fulfillmentPolicyId=p.get("fulfillmentPolicyId"),
            name=p.get("name"),
            marketplaceId=p.get("marketplaceId")
        ))
    return out


@app.post("/sellers/{sellerId}/fulfillment-policies", response_model=FulfillmentPolicyResponse, status_code=201)
def create_policy(sellerId: str, body: FulfillmentPolicyCreateRequest):
    token = refresh_access_token(sellerId).access_token
    url = "https://api.ebay.com/sell/account/v1/fulfillment_policy"
    r = requests.post(url, headers={**_bearer(token), "Content-Type": "application/json"}, json=body.dict(), timeout=REQ_TIMEOUT)
    if r.status_code not in (200, 201):
        raise HTTPException(r.status_code, r.text)
    p = r.json()
    return FulfillmentPolicyResponse(
        fulfillmentPolicyId=p.get("fulfillmentPolicyId"),
        name=p.get("name"),
        marketplaceId=p.get("marketplaceId")
    )


@app.put("/sellers/{sellerId}/fulfillment-policies/{policyId}", response_model=FulfillmentPolicyResponse)
def update_policy(sellerId: str, policyId: str, body: FulfillmentPolicyCreateRequest):
    token = refresh_access_token(sellerId).access_token
    url = f"https://api.ebay.com/sell/account/v1/fulfillment_policy/{policyId}"
    r = requests.put(url, headers={**_bearer(token), "Content-Type": "application/json"}, json=body.dict(), timeout=REQ_TIMEOUT)
    if r.status_code not in (200, 201):
        raise HTTPException(r.status_code, r.text)
    p = r.json()
    return FulfillmentPolicyResponse(
        fulfillmentPolicyId=p.get("fulfillmentPolicyId"),
        name=p.get("name"),
        marketplaceId=p.get("marketplaceId")
    )


# ---------- AI analyze (uses your existing ai.py if present) ----------
try:
    from ai import analyze_motorcycle_part as _ai_analyze
except Exception:
    _ai_analyze = None

@app.post("/ai/analyze-part", response_model=AIAnalyzeResponse)
async def analyze_part(body: AIAnalyzeRequest):
    if _ai_analyze is None:
        raise HTTPException(501, "ai.analyze_motorcycle_part not available in this deployment")
    data = await _ai_analyze(body.imageUrl, body.brand, body.model, body.year)
    return AIAnalyzeResponse(**data)


# ---------- Shipping: select fulfillment policy by weight ----------
WEIGHT_THRESHOLDS = {"XS": 0.25, "S": 0.75, "M": 2.0, "L": 5.0, "XL": 999.0}

def pick_weight_class_by_kg(kg: Optional[float]) -> str:
    try:
        w = float(kg) if kg is not None else None
    except Exception:
        w = None
    if w is None:
        return "M"
    if w <= WEIGHT_THRESHOLDS["XS"]: return "XS"
    if w <= WEIGHT_THRESHOLDS["S"]:  return "S"
    if w <= WEIGHT_THRESHOLDS["M"]:  return "M"
    if w <= WEIGHT_THRESHOLDS["L"]:  return "L"
    return "XL"

@app.post("/shipping/select-policy", response_model=ShippingPolicySelectionResponse)
def select_policy(body: ShippingPolicySelectionRequest):
    s = sellers_get(body.sellerId)
    wc = (body.weight_class or "").upper()
    if wc not in {"XS","S","M","L","XL"}:
        wc = pick_weight_class_by_kg(body.estimated_weight_kg)

    # Map to seller policies
    if wc in {"XS","S"}:
        policy = s.get("fpolicyLightId") or s.get("defaultFulfillmentPolicyId")
    elif wc == "M":
        policy = s.get("fpolicyMediumId") or s.get("defaultFulfillmentPolicyId")
    elif wc == "L":
        policy = s.get("fpolicyHeavyId") or s.get("defaultFulfillmentPolicyId")
    else:  # XL
        policy = s.get("fpolicyXHeavyId") or s.get("fpolicyHeavyId") or s.get("defaultFulfillmentPolicyId")

    if not policy:
        raise HTTPException(400, "Seller has no matching fulfillment policy configured")

    return ShippingPolicySelectionResponse(fulfillmentPolicyId=policy, resolvedWeightClass=wc)


# ------------------------------
# Run: uvicorn service_api:app --host 0.0.0.0 --port $PORT
# ------------------------------
