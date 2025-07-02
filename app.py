import os
from flask import Flask, request, jsonify
import requests, base64
from urllib.parse import unquote

app = Flask(__name__)

CLIENT_ID = 'Oleksand-Producti-PRD-c8e9abf40-17570312'
CLIENT_SECRET = 'PRD-8e9abf40dced-24f3-4a83-863b-c761'
REDIRECT_URI = 'https://telegram-seller-bot-production.up.railway.app/callback'
SCOPES = 'https://api.ebay.com/oauth/api_scope https://api.ebay.com/oauth/api_scope/sell.inventory https://api.ebay.com/oauth/api_scope/sell.account'

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
        "redirect_uri": RUNAME
    }

    r = requests.post("https://api.ebay.com/identity/v1/oauth2/token", headers=headers, data=data)
    if r.status_code == 200:
        tokens = r.json()
        with open("refresh_token.txt", "w") as f:
            f.write(tokens["refresh_token"])
        return jsonify(tokens)
    else:
        return f"Error: {r.text}", 400

def get_access_token():
    with open("refresh_token.txt") as f:
        refresh_token = f.read().strip()

    auth = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {auth}"
    }
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "scope": SCOPES
    }

    r = requests.post("https://api.ebay.com/identity/v1/oauth2/token", headers=headers, data=data)
    if r.status_code == 200:
        return r.json()["access_token"]
    else:
        print("Access token error:", r.text)
        return None

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
