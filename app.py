import base64
import uuid
from urllib.parse import unquote

import requests
from flask import Flask, request, jsonify

from config import *

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running"

@app.route("/callback")
def callback():
    raw_code = request.args.get("code")
    if not raw_code:
        return "Missing authorization code", 400

    code = unquote(raw_code)
    auth = base64.b64encode(f"{EBAY_CLIENT_ID}:{EBAY_CLIENT_SECRET}".encode()).decode()

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {auth}"
    }

    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI
    }

    response = requests.post("https://api.ebay.com/identity/v1/oauth2/token", headers=headers, data=data)

    if response.status_code == 200:
        tokens = response.json()
        refresh_token = tokens.get("refresh_token")
        access_token = tokens.get("access_token")
        print("REFRESH TOKEN:")
        print(refresh_token)
        return jsonify({
            "message": "Access and refresh tokens received",
            "refresh_token": refresh_token,
            "access_token": access_token
        })
    else:
        return f"Error fetching token: {response.text}", 400

def get_access_token():
    refresh_token = os.environ["EBAY_REFRESH_TOKEN"]
    auth = base64.b64encode(f"{EBAY_CLIENT_ID}:{EBAY_CLIENT_SECRET}".encode()).decode()
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
        access_token = r.json()["access_token"]
        return access_token
    else:
        raise Exception(f"Failed to get access token: {r.text}")


@app.route("/publish", methods=["POST"])
def publish():
    try:
        access_token = get_access_token()
    except Exception as e:
        return str(e), 500

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Content-Language": "it-IT"
    }

    sku = f"sku-{str(uuid.uuid4())[:8]}"

    # Step 1: Inventory Item
    inventory_payload = {
        "availability": {
            "shipToLocationAvailability": {
                "quantity": 1
            }
        },
        "condition": "NEW",
        "country": "IT",
        "location": "IT",
        "product": {
            "brand": "brand test",
            "mpn" : "7719",
            "subtitle": "Test Item from Bot, subtitle",
            "title": "Test Item from Bot",
            "description": "This is a test item listed via eBay Inventory API.",
            "imageUrls": ["https://via.placeholder.com/500"],
            "aspects": {
                "Capacità di memorizzazione": ["64 GB"],
                "Marca": ["Samsung"],
                "MPN": ["SM-G950F"],
                "Colore": ["Nero"],
                "Modello": ["Galaxy S8"]
            }
        }
    }

    inv = requests.put(f"https://api.ebay.com/sell/inventory/v1/inventory_item/{sku}", headers=headers, json=inventory_payload)
    print("Created inventory item:", inv)
    if inv.status_code not in [200, 204]:
        return f"Failed to create inventory item:\n{inv.status_code}\n{inv.text}", 500

    # Step 2: Offer
    offer_payload = {
        "sku": sku,
        "marketplaceId": MARKETPLACE_ID,
        "format": "FIXED_PRICE",
        "availableQuantity": 1,
        "categoryId": "9355",
        "listingDescription": "Test listing using eBay API.",
        "country": "IT",
        "location": "IT",
        "listingPolicies": {
            "fulfillmentPolicyId": 294952595011,
            "paymentPolicyId": 294966878011,
            "returnPolicyId": 294966928011
        },
        "pricingSummary": {
            "price": {
                "value": "9.99",
                "currency": "EUR"
            }
        },
        "quantityLimitPerBuyer": 1,
        "includeCatalogProductDetails": True,
        "merchantLocationKey": MERCHANT_LOCATION_KEY
    }

    offer = requests.post("https://api.ebay.com/sell/inventory/v1/offer", headers=headers, json=offer_payload)
    if offer.status_code != 201:
        return f"Failed to create offer:\n{offer.status_code}\n{offer.text}", 500

    offer_id = offer.json()["offerId"]

    # Step 3: Publish Offer
    pub = requests.post(f"https://api.ebay.com/sell/inventory/v1/offer/{offer_id}/publish", headers=headers)
    if pub.status_code != 200:
        return f"Failed to publish offer:\n{pub.status_code}\n{pub.text}", 500

    return jsonify({"message": "Item published successfully", "offerId": offer_id})

@app.route("/create-location", methods=["POST"])
def create_location():
    try:
        access_token = get_access_token()
    except Exception as e:
        return str(e), 500

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    location_key = MERCHANT_LOCATION_KEY
    url = f"https://api.ebay.com/sell/inventory/v1/location/{location_key}"

    payload = {
        "location": {
            "address": {
                "city": "Sezze",
                "stateOrProvince": "LT",
                "postalCode": "04018",
                "country": "IT"
            }
        },
        "name": "Sezze Warehouse",
        "merchantLocationStatus": "ENABLED",
        "locationInstructions": "Standard warehouse for shipping",
        "locationTypes": ["WAREHOUSE"]
    }

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code == 204:
        return jsonify({"message": "Location created successfully"})
    elif response.status_code == 409:
        return jsonify({"message": "Location already exists"}), 409
    else:
        return f"Failed to create location:\n{response.status_code}\n{response.text}", 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
