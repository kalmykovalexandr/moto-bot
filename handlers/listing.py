import asyncio
import logging
import os
from typing import Dict, List

from telegram import Update
from telegram.ext import ContextTypes

from clients.cloudinary_client import delete_image, upload_image
from clients.ebay_client import publish_item
from clients.ebay_metadata_client import suggest_category
from configs.product_profiles import get_profile
from helpers.ai_helper import analyze_product
from utils.shipping_util import (
    WEIGHT_THRESHOLDS,
    pick_policy_by_weight_class,
    pick_weight_class_by_kg,
)
from utils.template_util import compose_listing_title, generate_product_description

from .constants import (
    AI_DATA_FETCHED,
    ASKING_PRICE,
    BRAND,
    CATEGORY_ID,
    CATEGORY_NAME,
    CLOUDINARY_IDS,
    COLOR,
    CONDITION,
    DESCRIPTION,
    ESTIMATED_WEIGHT,
    FULFILLMENT_POLICY_ID,
    IMAGE_URLS,
    MATERIAL,
    MPN,
    MODEL,
    PHOTO_PROCESSING,
    PRICE_PROMPT_SENT,
    PRODUCT_TYPE,
    PROFILE_ANSWERS,
    PROFILE_ID,
    TITLE,
    TRANSIENT_SESSION_KEYS,
    WEIGHT_CLASS,
)

logger = logging.getLogger(__name__)


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    user_data = context.user_data

    def _current_state():
        return ASKING_PRICE if user_data.get(PRICE_PROMPT_SENT) else ASKING_PHOTOS

    if not message:
        return _current_state()

    tg_file = None
    temp_path = f"temp_{message.from_user.id}.img"

    if message.photo:
        largest_photo = max(message.photo, key=lambda p: p.file_size)
        tg_file = await largest_photo.get_file()
    elif (
        message.document
        and message.document.mime_type
        and message.document.mime_type.startswith("image/")
    ):
        tg_file = await message.document.get_file()
    else:
        await message.reply_text("Please send a valid image file (JPEG/PNG).")
        return _current_state()

    await tg_file.download_to_drive(temp_path)

    user_data.setdefault(IMAGE_URLS, [])
    user_data.setdefault(CLOUDINARY_IDS, [])
    user_data.setdefault(PHOTO_PROCESSING, False)
    user_data.setdefault(AI_DATA_FETCHED, False)
    user_data.setdefault(PRICE_PROMPT_SENT, False)

    try:
        uploaded = await asyncio.to_thread(upload_image, temp_path)
        user_data[IMAGE_URLS].append(uploaded["secure_url"])
        user_data[CLOUDINARY_IDS].append(uploaded["public_id"])
    except Exception as exc:
        logger.error("Cloudinary upload failed: %s", exc, exc_info=True)
        await message.reply_text("Couldn't upload the photo. Please try again.")
        return ASKING_PRICE
    finally:
        try:
            os.remove(temp_path)
        except FileNotFoundError:
            pass

    if user_data[PHOTO_PROCESSING] or user_data[AI_DATA_FETCHED]:
        return ASKING_PRICE

    user_data[PHOTO_PROCESSING] = True
    profile = get_profile(context.user_data.get(PROFILE_ID))
    answers = context.user_data.get(PROFILE_ANSWERS, {})

    try:
        ai_data = await analyze_product(
            image_url=user_data[IMAGE_URLS][0],
            hints=answers,
            profile_hint=profile.ai_hint,
            weight_thresholds=WEIGHT_THRESHOLDS,
        )
        est_kg = ai_data.get("estimated_weight_kg")
        weight_class = ai_data.get("weight_class") or pick_weight_class_by_kg(est_kg)
        policy_id = pick_policy_by_weight_class(weight_class)

        brand = _pick_value(ai_data.get("brand"), answers.get("brand"))
        model = _pick_value(ai_data.get("model"), answers.get("model"))
        color = _pick_value(ai_data.get("color"), answers.get("color"))
        material = _pick_value(ai_data.get("material"), answers.get("material"))
        product_type = _pick_value(ai_data.get("product_type"), answers.get("title_hint"), "Product")
        condition = _pick_value(ai_data.get("condition"), answers.get("condition"), "Used")
        mpn = _pick_value(ai_data.get("mpn"), answers.get("sku"))

        title, description = generate_listing_content(ai_data, context, profile, answers)

        user_data.update(
            {
                WEIGHT_CLASS: weight_class,
                ESTIMATED_WEIGHT: est_kg,
                FULFILLMENT_POLICY_ID: policy_id,
                TITLE: title,
                DESCRIPTION: description,
                COLOR: color or "N/A",
                MATERIAL: material or "N/A",
                PRODUCT_TYPE: product_type or "Product",
                CONDITION: condition or "Used",
                BRAND: brand or "N/A",
                MODEL: model or "N/A",
                MPN: mpn or "N/A",
                AI_DATA_FETCHED: True,
            }
        )

        category_id, category_name = await asyncio.to_thread(suggest_category, title)
        if category_id:
            user_data[CATEGORY_ID] = category_id
            user_data[CATEGORY_NAME] = category_name
            await message.reply_text(f"Suggested eBay category: {category_name} ({category_id})")
        else:
            user_data.pop(CATEGORY_ID, None)
            user_data.pop(CATEGORY_NAME, None)
    except Exception as exc:
        logger.error("AI or listing preparation failed: %s", exc, exc_info=True)
        user_data[PHOTO_PROCESSING] = False
        await message.reply_text("Processing failed. Please send the photo again.")
        return ASKING_PRICE
    finally:
        user_data[PHOTO_PROCESSING] = False

    if not user_data[PRICE_PROMPT_SENT]:
        await message.reply_text("Photo(s) uploaded. Now enter the price (e.g., 19.99):")
        user_data[PRICE_PROMPT_SENT] = True

    return ASKING_PRICE


async def handle_price_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message:
        return ASKING_PRICE

    try:
        price = float(message.text.strip())
    except (ValueError, AttributeError):
        await message.reply_text("Invalid price. Please enter a numeric value like 19.99.")
        return ASKING_PRICE

    data = context.user_data
    missing = [TITLE, DESCRIPTION, IMAGE_URLS]
    if not all(data.get(key) for key in missing):
        await message.reply_text("Missing listing data. Please resend the photo(s) and try again.")
        return ASKING_PRICE

    try:
        result = await asyncio.to_thread(
            publish_item,
            title=data[TITLE],
            description=data[DESCRIPTION],
            brand=data.get(BRAND),
            model=data.get(MODEL),
            mpn=data.get(MPN),
            color=data.get(COLOR, "N/A"),
            material=data.get(MATERIAL, "N/A"),
            product_type=data.get(PRODUCT_TYPE, "Product"),
            image_urls=data[IMAGE_URLS],
            price=price,
            fulfillment_policy_id=data.get(FULFILLMENT_POLICY_ID),
            category_id=data.get(CATEGORY_ID),
        )
    except Exception as exc:
        logger.error("Failed to publish item: %s", exc, exc_info=True)
        await message.reply_text("Failed to contact eBay. Please try again.")
        return ASKING_PRICE

    await message.reply_text(result)

    if not str(result).startswith("Successfully published"):
        return ASKING_PRICE

    conclude_listing_session(context)
    await message.reply_text("Do you want to list another product? Send photos now or /end to finish.")
    return ASKING_PRICE


def conclude_listing_session(context: ContextTypes.DEFAULT_TYPE):
    for key in TRANSIENT_SESSION_KEYS:
        context.user_data.pop(key, None)


def generate_listing_content(
    ai_data: Dict,
    context: ContextTypes.DEFAULT_TYPE,
    profile,
    answers: Dict,
):
    tags_str = _join_tags(ai_data.get("tags"))
    features = _clean_features(ai_data.get("features"))
    brand = context.user_data.get(BRAND, "N/A")
    model = context.user_data.get(MODEL, "N/A")
    product_type = context.user_data.get(PRODUCT_TYPE, "Product")
    color = context.user_data.get(COLOR, "N/A")
    material = context.user_data.get(MATERIAL, "N/A")
    condition = context.user_data.get(CONDITION, "Used")
    included_items = ai_data.get("included_items", "N/A")
    description_body = ai_data.get("description", "")

    title = compose_listing_title(
        ai_title=ai_data.get("title"),
        user_hint=answers.get("title_hint"),
        brand=brand,
        model=model,
    )

    description = generate_product_description(
        template_name=profile.template,
        product_type=product_type,
        brand=brand,
        model=model,
        color=color,
        material=material,
        condition=condition,
        included_items=included_items,
        features=features,
        description=description_body,
        tags=tags_str,
    )

    return title, description


def _join_tags(tags: List[str] | None) -> str:
    cleaned = []
    seen = set()
    for tag in tags or []:
        tag_str = str(tag).strip()
        if not tag_str:
            continue
        key = tag_str.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(tag_str[:60])
    return ", ".join(cleaned)[:500]


def _clean_features(features: List[str] | None) -> List[str]:
    result = []
    seen = set()
    for feature in features or []:
        text = str(feature).strip()
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(text[:120])
        if len(result) >= 8:
            break
    return result


def _pick_value(*candidates):
    for value in candidates:
        if isinstance(value, str) and value.strip():
            return value.strip()
        if value and not isinstance(value, str):
            return value
    return None


async def delete_cloudinary_images_async(context: ContextTypes.DEFAULT_TYPE):
    ids = context.user_data.get(CLOUDINARY_IDS, [])
    for public_id in ids:
        try:
            await asyncio.to_thread(delete_image, public_id)
        except Exception as exc:
            logger.warning("Failed to delete Cloudinary image %s: %s", public_id, exc)
