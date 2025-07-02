import os
from flask import Flask, request, jsonify
import requests, base64
from urllib.parse import unquote

app = Flask(__name__)

CLIENT_ID = 'Oleksand-Producti-PRD-c8e9abf40-17570312'
CLIENT_SECRET = 'PRD-8e9abf40dced-24f3-4a83-863b-c761'
REDIRECT_URI = 'https://telegram-seller-bot-production.up.railway.app/callback'
SCOPES = 'https://api.ebay.com/oauth/api_scope https://api.ebay.com/oauth/api_scope/sell.inventory https://api.ebay.com/oauth/api_scope/sell.account'
RUNAME = 'Oleksandr_Kalmy-Oleksand-Produc-jhxqqwktz'

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
        print("REFRESH TOKEN:")
        print(refresh_token)
        return jsonify({
            "message": "Refresh token received",
            "refresh_token": refresh_token
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
    access_token = get_access_token()
    if not access_token:
        return "Access token error", 500

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    payload = {
        "sku": "test-sku-001",
        "product": {
            "title": "Test product from bot",
            "description": "This is a test listing from my Telegram bot.",
            "aspects": {
                "Brand": ["Honda"]
            },
            "imageUrls": [
                "https://example.com/image.jpg"
            ]
        },
        "availability": {
            "shipToLocationAvailability": {
                "quantity": 1
            }
        },
        "price": {
            "value": "149.99",
            "currency": "EUR"
        }
    }

    r = requests.put("https://api.ebay.com/sell/inventory/v1/inventory_item/test-sku-001", headers=headers, json=payload)

    if r.status_code == 204:
        return "Item successfully listed", 200
    else:
        return f"Listing error: {r.status_code}\n{r.text}", 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
