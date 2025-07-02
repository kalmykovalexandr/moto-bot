import os
from flask import Flask, request, jsonify
import requests, base64
from urllib.parse import unquote

app = Flask(__name__)

CLIENT_ID = 'Oleksand-Producti-PRD-c8e9abf40-17570312'
CLIENT_SECRET = 'PRD-8e9abf40dced-24f3-4a83-863b-c761'
REDIRECT_URI = 'https://web-production-bfa68.up.railway.app/callback'
SCOPES = 'https://api.ebay.com/oauth/api_scope https://api.ebay.com/oauth/api_scope/sell.inventory https://api.ebay.com/oauth/api_scope/sell.account'
RUNAME = 'Oleksandr_Kalmy-Oleksand-Produc-jhxqqwktz'

# Required for offer creation
MARKETPLACE_ID = "EBAY_IT"
FULFILLMENT_POLICY_ID = 294952595011
PAYMENT_POLICY_ID = 294966878011
RETURN_POLICY_ID = 294966928011

@app.route("/")
def home():
    return "Bot is running"

@app.route("/callback")
def callback():
    raw_code = request.args.get("code")
    if not raw_code:
        return "Missing authorization code", 400

    code = unquote(raw_code)
    auth = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()

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

    sku = str(uuid.uuid4())[:12]

    # Step 1: Inventory Item
    inventory_payload = {
        "availability": {
            "shipToLocationAvailability": {
                "quantity": 1
            }
        },
        "condition": "NEW",
        "product": {
            "title": "Test Item from Bot",
            "description": "This is a test item listed via eBay Inventory API.",
            "aspects": {
                "Brand": ["Generic"]
            },
            "imageUrls": [
                "https://via.placeholder.com/500"
            ]
        },
        "shipToLocations": {
            "country": "IT",
            "postalCode": "20100",  # Example postal code (Milan)
            "region": "Lombardia",
            "city": "Milano"
        }
    }

    inv = requests.put(f"https://api.ebay.com/sell/inventory/v1/inventory_item/{sku}", headers=headers, json=inventory_payload)
    if inv.status_code not in [200, 204]:
        return f"Failed to create inventory item:\n{inv.status_code}\n{inv.text}", 500

    # Step 2: Offer
    offer_payload = {
        "sku": sku,
        "marketplaceId": MARKETPLACE_ID,
        "format": "FIXED_PRICE",
        "listingDescription": "Test listing using eBay API.",
        "availableQuantity": 1,
        "categoryId": "9355",
        "listingPolicies": {
            "fulfillmentPolicyId": FULFILLMENT_POLICY_ID,
            "paymentPolicyId": PAYMENT_POLICY_ID,
            "returnPolicyId": RETURN_POLICY_ID
        },
        "pricingSummary": {
            "price": {
                "value": "9.99",
                "currency": "EUR"
            }
        }
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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
