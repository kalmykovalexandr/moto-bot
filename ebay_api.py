import os
import uuid
import base64
import requests

CLIENT_ID = 'Oleksand-Producti-PRD-c8e9abf40-17570312'
CLIENT_SECRET = 'PRD-8e9abf40dced-24f3-4a83-863b-c761'
MARKETPLACE_ID = "EBAY_IT"
MERCHANT_LOCATION_KEY = "sezze-warehouse"
FULFILLMENT_POLICY_ID = 294952595011
PAYMENT_POLICY_ID = 294966878011
RETURN_POLICY_ID = 294966928011

def get_access_token():
    refresh_token = os.environ["REFRESH_TOKEN"]
    auth = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {auth}"
    }
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "scope": "https://api.ebay.com/oauth/api_scope https://api.ebay.com/oauth/api_scope/sell.inventory https://api.ebay.com/oauth/api_scope/sell.account"
    }

    r = requests.post("https://api.ebay.com/identity/v1/oauth2/token", headers=headers, data=data)
    if r.status_code == 200:
        return r.json()["access_token"]
    else:
        raise Exception(f"Failed to get access token: {r.text}")

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
            "subtitle": title[:80],
            "brand": brand,
            "mpn": mpn,
            "aspects": {
                "Brand": brand,
                "Model": model,
                "MPN": mpn,
                "Color": color,
                "Part Type": part_type,
                "Compatible Year": compatible_years.split("–") if "–" in compatible_years else [compatible_years]
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
        "categoryId": "10063",
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
