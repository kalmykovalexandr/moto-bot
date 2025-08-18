import base64
import os
import uuid

import requests

from config import FULFILLMENT_POLICY_ID, PAYMENT_POLICY_ID, RETURN_POLICY_ID, MERCHANT_LOCATION_KEY

EBAY_TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"
EBAY_CLIENT_ID = os.getenv("EBAY_CLIENT_ID")
EBAY_CLIENT_SECRET = os.getenv("EBAY_CLIENT_SECRET")
REQUIRED_SCOPES = " ".join([
    "https://api.ebay.com/oauth/api_scope/sell.inventory",
    "https://api.ebay.com/oauth/api_scope/sell.account",
    "https://api.ebay.com/oauth/api_scope"  # общий
])


def _require_env(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise RuntimeError(f"Missing env var: {name}")
    return v.strip()

def get_access_token() -> str:
    client_id = _require_env("EBAY_CLIENT_ID")
    client_secret = _require_env("EBAY_CLIENT_SECRET")

    # читаем и старое имя на всякий случай
    refresh_token = os.getenv("EBAY_REFRESH_TOKEN") or os.getenv("REFRESH_TOKEN")
    if not refresh_token:
        raise RuntimeError("Missing env var: EBAY_REFRESH_TOKEN (or REFRESH_TOKEN)")
    refresh_token = refresh_token.strip()

    basic = base64.b64encode(f"{client_id}:{client_secret}".encode("utf-8")).decode("ascii")

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {basic}",
        "Accept": "application/json",
    }
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "scope": REQUIRED_SCOPES,
    }

    r = requests.post(EBAY_TOKEN_URL, headers=headers, data=data, timeout=20)
    if r.status_code == 200:
        return r.json()["access_token"]

    # Улучшаем диагностику
    tail_id = client_id[-4:] if len(client_id) >= 4 else client_id
    raise Exception(
        "Failed to get access token: "
        f"status={r.status_code}, body={r.text}, "
        f"client_id_endswith={tail_id}"
    )

def publish_item(title, description, brand, model, mpn, color, image_urls, price, compatible_years, part_type):
    access_token = get_access_token()
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Content-Language": "it-IT"
    }

    sku = f"sku-{str(uuid.uuid4())[:8]}"

    inventory_payload = {
        "availability": {
            "shipToLocationAvailability": {
                "quantity": 1
            }
        },
        "condition": "USED_EXCELLENT",
        "conditionDescription": "Parte usata con segni di usura estetici, perfettamente funzionante. Controlla le foto per le condizioni esatte. / Used part with cosmetic wear, fully functional. Please check images for exact condition.",
        "product": {
            "title": title,
            "description": description,
            "imageUrls": image_urls,
            "brand": brand,
            "mpn": mpn,
            "aspects": {
                  "Marca": [brand],
                  "MPN": [mpn],
                  "Produttore compatibile": [brand],
                  "Tipo": [part_type],
                  "Colore": [color],
                  "Ricambio": ["Sì"],
                  "Destinazione d'uso": ["Parte di ricambio"]
                }
        }
    }

    inv = requests.put(f"https://api.ebay.com/sell/inventory/v1/inventory_item/{sku}", headers=headers, json=inventory_payload)
    if inv.status_code not in [200, 204]:
        return f"Failed to create inventory item: {inv.status_code} {inv.text}"

    offer_payload = {
        "sku": sku,
        "marketplaceId": "EBAY_IT",
        "format": "FIXED_PRICE",
        "availableQuantity": 1,
        "categoryId": "179753",
        "listingDescription": description,
        "listingPolicies": {
            "fulfillmentPolicyId": FULFILLMENT_POLICY_ID,
            "paymentPolicyId": PAYMENT_POLICY_ID,
            "returnPolicyId": RETURN_POLICY_ID
        },
        "pricingSummary": {
            "price": {
                "value": str(price),
                "currency": "EUR"
            }
        },
        "quantityLimitPerBuyer": 1,
        "includeCatalogProductDetails": True,
        "merchantLocationKey": MERCHANT_LOCATION_KEY,
        "tax": {
            "applyTax": False
        },
        "hideBuyerDetails": False
    }

    offer = requests.post("https://api.ebay.com/sell/inventory/v1/offer", headers=headers, json=offer_payload)
    if offer.status_code != 201:
        return f"Failed to create offer: {offer.status_code} {offer.text}"

    offer_id = offer.json()["offerId"]
    pub = requests.post(f"https://api.ebay.com/sell/inventory/v1/offer/{offer_id}/publish", headers=headers)
    if pub.status_code != 200:
        return f"Failed to publish offer: {pub.status_code} {pub.text}"

    return f"Successfully published offer: {offer_id}"
