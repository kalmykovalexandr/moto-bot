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
    return "✅ Бот работает!"

@app.route("/callback")
def callback():
    raw_code = request.args.get("code")
    if not raw_code:
        return "❌ Нет кода авторизации", 400

    code = unquote(raw_code)
    print("Code:")
    print(code)

    # Авторизация
    auth = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {auth}"
    }
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": 'Oleksandr_Kalmy-Oleksand-Produc-jhxqqwktz'
    }

    r = requests.post("https://api.ebay.com/identity/v1/oauth2/token", headers=headers, data=data)

    if r.status_code == 200:
        tokens = r.json()
        print("✅ Токены получены:")
        print(tokens)
        return jsonify(tokens)
    else:
        print("❌ Ошибка:")
        print(r.text)
        print(r.status_code)
        return "❌ Ошибка при получении токенов", 400

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
