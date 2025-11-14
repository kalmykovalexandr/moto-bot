ASKING_BRAND, ASKING_MODEL, ASKING_YEAR, ASKING_MPN, ASKING_PRICE = range(5)

SESSION_ACTIVE = "session_active"
BRAND = "brand"
MODEL = "model"
YEAR = "year"
MPN = "mpn"
IMAGE_URLS = "image_urls"
CLOUDINARY_IDS = "cloudinary_public_ids"
PHOTO_PROCESSING = "photo_processing"
AI_DATA_FETCHED = "ai_data_fetched"
PRICE_PROMPT_SENT = "price_prompt_sent"
WEIGHT_CLASS = "weight_class"
ESTIMATED_WEIGHT = "estimated_weight_kg"
FULFILLMENT_POLICY_ID = "fulfillment_policy_id"
TITLE = "title"
DESCRIPTION = "description"
COLOR = "color"
COMPATIBLE_YEARS = "compatible_years"
PART_TYPE = "part_type"
PHOTO_UPLOADED_FLAG = "photo_uploaded_once"
CATEGORY_ID = "category_id"
CATEGORY_NAME = "category_name"

TRANSIENT_SESSION_KEYS = [
    IMAGE_URLS,
    TITLE,
    DESCRIPTION,
    COLOR,
    PART_TYPE,
    COMPATIBLE_YEARS,
    AI_DATA_FETCHED,
    PHOTO_UPLOADED_FLAG,
    CLOUDINARY_IDS,
    PRICE_PROMPT_SENT,
    WEIGHT_CLASS,
    ESTIMATED_WEIGHT,
    FULFILLMENT_POLICY_ID,
    CATEGORY_ID,
    CATEGORY_NAME,
]
