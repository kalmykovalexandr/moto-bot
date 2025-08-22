import os

# MAIN CONFIGS
EBAY_CLIENT_ID = os.getenv("EBAY_CLIENT_ID")
EBAY_CLIENT_SECRET = os.getenv("EBAY_CLIENT_SECRET")
EBAY_REFRESH_TOKEN = os.getenv("EBAY_REFRESH_TOKEN")
EBAY_REDIRECT_URI = os.getenv("EBAY_REDIRECT_URI")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")

EBAY_OAUTH_SCOPE="https://api.ebay.com/oauth/api_scope https://api.ebay.com/oauth/api_scope/sell.inventory https://api.ebay.com/oauth/api_scope/sell.account"
EBAY_OAUTH_URL = "https://api.ebay.com/identity/v1/oauth2/token"

# EBAY CONFIGS
MARKETPLACE_ID = "EBAY_IT"
MERCHANT_LOCATION_KEY = "sezze-warehouse"
PAYMENT_POLICY_ID = 273958512015
RETURN_POLICY_ID = 273958551015

# Fulfillment Policies by weight
FULFILLMENT_POLICIES = {
    "SHIP_XS": "273958585015",
    "SHIP_S": "273958644015",
    "SHIP_M": "273958658015",
    "SHIP_L": "273958675015",
    "SHIP_XL": "273958692015",
    "SHIP_XXL": "273958728015",
    "SHIP_FREIGHT": "273958776015",
}

# Weight thresholds (kg) used across the app
WEIGHT_THRESHOLDS = {
    "XS": 0.25,
    "S": 0.75,
    "M": 2.0,
    "L": 5.0,
    "XL": 20.0,
    "XXL": 50.0,
    # FREIGHT: > 50 kg
}
DEFAULT_WEIGHT_CLASS = "M"
DEFAULT_FULFILLMENT_POLICY_ID = FULFILLMENT_POLICIES["SHIP_M"]