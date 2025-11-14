import asyncio
import logging
import os
from typing import Dict

from telegram import Update
from telegram.ext import ContextTypes

from clients.cloudinary_client import delete_image, upload_image
from clients.ebay_client import publish_item
from clients.ebay_metadata_client import suggest_category
from helpers.ai_helper import analyze_motorcycle_part
from utils.shipping_util import (
    WEIGHT_THRESHOLDS,
    pick_policy_by_weight_class,
    pick_weight_class_by_kg,
)
from utils.template_util import (
    generate_motor_description,
    generate_motor_title,
    generate_part_description,
    generate_part_title,
)

from .constants import (
    AI_DATA_FETCHED,
    ASKING_PRICE,
    BRAND,
    CATEGORY_ID,
    CATEGORY_NAME,
    CLOUDINARY_IDS,
    COLOR,
    COMPATIBLE_YEARS,
    DESCRIPTION,
    ESTIMATED_WEIGHT,
    FULFILLMENT_POLICY_ID,
    IMAGE_URLS,
    MPN,
    MODEL,
    PART_TYPE,
    PHOTO_PROCESSING,
    PRICE_PROMPT_SENT,
    TITLE,
    TRANSIENT_SESSION_KEYS,
    WEIGHT_CLASS,
    YEAR,
)

logger = logging.getLogger(__name__)


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    user_data = context.user_data

    if not message or not message.photo:
        await message.reply_text("Please send a valid image file.")
        return ASKING_PRICE

    photos = message.photo
    largest_photo = max(photos, key=lambda p: p.file_size)
    tg_file = await largest_photo.get_file()
    temp_path = f"temp_{message.from_user.id}.jpg"
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
    try:
        ai_data = await analyze_motorcycle_part(
            image_url=user_data[IMAGE_URLS][0],
            brand=user_data.get(BRAND),
            model=user_data.get(MODEL),
            year=user_data.get(YEAR),
            weight_thresholds=WEIGHT_THRESHOLDS,
        )
        est_kg = ai_data.get("estimated_weight_kg")
        weight_class = ai_data.get("weight_class") or pick_weight_class_by_kg(est_kg)
        policy_id = pick_policy_by_weight_class(weight_class)
        title, description = generate_listing_content(ai_data, context)

        user_data.update(
            {
                WEIGHT_CLASS: weight_class,
                ESTIMATED_WEIGHT: est_kg,
                FULFILLMENT_POLICY_ID: policy_id,
                TITLE: title,
                DESCRIPTION: description,
                COLOR: ai_data.get("color", "N/A"),
                COMPATIBLE_YEARS: ai_data.get("compatible_years", "N/A"),
                PART_TYPE: ai_data.get("part_type", "N/A"),
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
            image_urls=data[IMAGE_URLS],
            price=price,
            compatible_years=data.get(COMPATIBLE_YEARS, "N/A"),
            part_type=data.get(PART_TYPE, "N/A"),
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
    await message.reply_text("Do you want to list another part? Send photos now or /end to finish.")
    return ASKING_PRICE


def conclude_listing_session(context: ContextTypes.DEFAULT_TYPE):
    for key in TRANSIENT_SESSION_KEYS:
        context.user_data.pop(key, None)


def generate_listing_content(ai_data: Dict, context: ContextTypes.DEFAULT_TYPE):
    def join_tags(tags):
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

    tags_str = join_tags(ai_data.get("tags"))
    brand = context.user_data.get(BRAND, "N/A")
    model = context.user_data.get(MODEL, "N/A")
    year = context.user_data.get(YEAR, "N/A")
    mpn = context.user_data.get(MPN, "N/A")

    if ai_data.get("is_motor"):
        title = generate_motor_title(
            brand=brand,
            model=model,
            compatible_years=ai_data.get("compatible_years", "N/A"),
            displacement=ai_data.get("displacement"),
        )
        description = generate_motor_description(
            brand=brand,
            model=model,
            year=year,
            compatible_years=ai_data.get("compatible_years", "N/A"),
            color=ai_data.get("color", "N/A"),
            mpn=mpn,
            engine_type=ai_data.get("engine_type", "N/A"),
            displacement=ai_data.get("displacement", "N/A"),
            bore_stroke=ai_data.get("bore_stroke", "N/A"),
            compression_ratio=ai_data.get("compression_ratio", "N/A"),
            max_power=ai_data.get("max_power", "N/A"),
            max_torque=ai_data.get("max_torque", "N/A"),
            cooling=ai_data.get("cooling", "N/A"),
            fuel_system=ai_data.get("fuel_system", "N/A"),
            starter=ai_data.get("starter", "N/A"),
            gearbox=ai_data.get("gearbox", "N/A"),
            final_drive=ai_data.get("final_drive", "N/A"),
            recommended_oil=ai_data.get("recommended_oil", "N/A"),
            oil_capacity=ai_data.get("oil_capacity", "N/A"),
            description=ai_data.get("description", ""),
            tags=tags_str,
        )
    else:
        part_for_title = ai_data.get("part_type", "Part")
        title = generate_part_title(
            part_type_for_title=part_for_title,
            brand=brand,
            model=model,
            compatible_years=ai_data.get("compatible_years", "N/A"),
            color=ai_data.get("color"),
        )
        description = generate_part_description(
            brand=brand,
            model=model,
            year=year,
            compatible_years=ai_data.get("compatible_years", "N/A"),
            part_type=ai_data.get("part_type", "N/A"),
            color=ai_data.get("color", "N/A"),
            mpn=mpn,
            description=ai_data.get("description", ""),
            tags=tags_str,
        )

    return title, description


async def delete_cloudinary_images_async(context: ContextTypes.DEFAULT_TYPE):
    ids = context.user_data.get(CLOUDINARY_IDS, [])
    for public_id in ids:
        try:
            await asyncio.to_thread(delete_image, public_id)
        except Exception as exc:
            logger.warning("Failed to delete Cloudinary image %s: %s", public_id, exc)
