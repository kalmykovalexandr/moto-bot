import logging
import os
from typing import Dict

from telegram import Update
from telegram.ext import (
    CommandHandler, MessageHandler, filters,
    ContextTypes, ConversationHandler
)

from clients.cloudinary_client import delete_image, upload_image
from clients.ebay_client import publish_item
from utils.template_util import generate_motor_title, generate_motor_description, generate_part_title, \
    generate_part_description
from utils.shipping_util import WEIGHT_THRESHOLDS, pick_weight_class_by_kg, pick_policy_by_weight_class
from helpers.ai_helper import analyze_motorcycle_part

logger = logging.getLogger(__name__)

# Constants for conversation states
ASKING_BRAND, ASKING_MODEL, ASKING_YEAR, ASKING_MPN, ASKING_PRICE = range(5)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    context.user_data["session_active"] = True
    await update.message.reply_text("Welcome! Please enter the motorcycle brand (e.g., Honda):")
    return ASKING_BRAND


async def end(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Session ended. To start a new session, type /start.")
    return ConversationHandler.END


async def handle_brand_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["brand"] = update.message.text.strip()
    await update.message.reply_text("Now enter the motorcycle model (e.g., Transalp 650):")
    return ASKING_MODEL


async def handle_model_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["model"] = update.message.text.strip()
    await update.message.reply_text("Now enter the year of the motorcycle (e.g., 1999):")
    return ASKING_YEAR


async def handle_year_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["year"] = update.message.text.strip()
    await update.message.reply_text("Now enter the MPN (Manufacturer Part Number) of the motorcycle part:")
    return ASKING_MPN


async def handle_mpn_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["mpn"] = update.message.text.strip()
    context.user_data["image_urls"] = []
    await update.message.reply_text(
        (f"Session started for moto: {context.user_data['brand']} - {context.user_data['model']} \n"
         f"Year: {context.user_data['year']} \n"
         f"MPN: {context.user_data['mpn']} \n\n"
         "Now send photo(s) of the part."),
        parse_mode="Markdown"
    )

    return ASKING_PRICE


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ud = context.user_data
    ud.setdefault("image_urls", [])
    ud.setdefault("cloudinary_public_ids", [])
    ud.setdefault("photo_processing", False)
    ud.setdefault("ai_data_fetched", False)
    ud.setdefault("price_prompt_sent", False)

    if not update.message or not update.message.photo:
        await update.message.reply_text("Please send a valid image file.")
        return ASKING_PRICE

    photo = max(update.message.photo, key=lambda p: p.file_size)
    file = await photo.get_file()
    temp_path = f"temp_{update.message.from_user.id}.jpg"
    await file.download_to_drive(temp_path)

    try:
        uploaded = upload_image(temp_path)
        ud["image_urls"].append(uploaded["secure_url"])
        ud["cloudinary_public_ids"].append(uploaded["public_id"])
    except Exception as e:
        logger.error(f"Cloudinary upload failed: {e}")
        await update.message.reply_text("Couldn't upload the photo. Please try again.")
        return ASKING_PRICE
    finally:
        try:
            os.remove(temp_path)
        except Exception:
            pass

    if ud["photo_processing"] or ud["ai_data_fetched"]:
        return ASKING_PRICE

    ud["photo_processing"] = True
    try:
        ai_data = await analyze_motorcycle_part(
            image_url=ud["image_urls"][0],
            brand=ud["brand"],
            model=ud["model"],
            year=ud["year"],
            thr=WEIGHT_THRESHOLDS,
        )

        est_kg = ai_data.get("estimated_weight_kg")
        weight_class = ai_data.get("weight_class") or pick_weight_class_by_kg(est_kg)
        chosen_policy_id = pick_policy_by_weight_class(weight_class)

        title, description = generate_listing_content(ai_data, context)

        ud.update({
            "weight_class": weight_class,
            "estimated_weight_kg": est_kg,
            "fulfillment_policy_id": chosen_policy_id,
            "title": title,
            "description": description,
            "color": ai_data.get("color", "N/A"),
            "compatible_years": ai_data.get("compatible_years", "N/A"),
            "part_type": ai_data.get("part_type", "N/A"),
            "ai_data_fetched": True,
        })
    except Exception as e:
        logger.error(f"AI/prepare listing failed: {e}", exc_info=True)
        ud["photo_processing"] = False
        await update.message.reply_text("Processing failed. Please send the photo again.")
        return ASKING_PRICE
    finally:
        ud["photo_processing"] = False

    if not ud["price_prompt_sent"]:
        await update.message.reply_text("Photo(s) uploaded. Now enter the price (e.g., 19.99):")
        ud["price_prompt_sent"] = True

    return ASKING_PRICE



async def handle_price_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        price = float(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("Invalid price. Please enter a numeric value like 19.99.")
        return ASKING_PRICE

    data = context.user_data
    result = publish_item(
        title=data["title"],
        description=data["description"],
        brand=data["brand"],
        model=data["model"],
        mpn=data["mpn"],
        color=data.get("color", "N/A"),
        image_urls=data["image_urls"],
        price=price,
        compatible_years=data.get("compatible_years", "N/A"),
        part_type=data.get("part_type", "N/A"),
        fulfillment_policy_id=data.get("fulfillment_policy_id")
    )

    await update.message.reply_text(result)

    if not str(result).startswith("Successfully published"):
        return ASKING_PRICE

    try:
        conclude_listing_session(context)
    except Exception as e:
        logger.error(f"conclude_listing_session failed: {e}")

    await update.message.reply_text("Do you want to list another part? Send photos now or /end to finish.")
    return ASKING_PRICE


def conclude_listing_session(context: ContextTypes.DEFAULT_TYPE):
    for key in [
        "image_urls", "title", "description", "color", "part_type",
        "compatible_years", "ai_data_fetched", "photo_uploaded_once",
        "cloudinary_public_ids"
    ]:
        context.user_data.pop(key, None)


def generate_listing_content(ai_data: Dict, context: ContextTypes.DEFAULT_TYPE):
    def _join_tags(tags):
        if not tags:
            return ""
        cleaned = [str(t).strip() for t in tags if isinstance(t, str) and t.strip()]
        seen = set()
        unique = []
        for t in cleaned:
            key = t.lower()
            if key not in seen:
                seen.add(key)
                unique.append(t[:60])
        return ", ".join(unique)[:500]

    tags_str = _join_tags(ai_data.get("tags"))

    brand = context.user_data.get("brand", "N/A")
    model = context.user_data.get("model", "N/A")
    year = context.user_data.get("year", "N/A")
    mpn = context.user_data.get("mpn", "N/A")

    if ai_data.get("is_motor"):
        title = generate_motor_title(
            brand,
            model,
            ai_data.get("compatible_years", "N/A"),
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
            part_for_title,
            brand,
            model,
            ai_data.get("compatible_years", "N/A"),
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


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Exception while handling an update: {context.error}", exc_info=True)
    if isinstance(update, Update) and update.message:
        await update.message.reply_text("An internal error occurred.")


async def show_session_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = context.user_data
    if not data.get("session_active"):
        await update.message.reply_text("Session is not active. Start with /start.")
        return

    summary = (
        f"*Current session:*\n"
        f"• Brand: *{data.get('brand', '—')}*\n"
        f"• Model: *{data.get('model', '—')}*\n"
        f"• Year: *{data.get('year', '—')}*\n"
        f"• MPN: *{data.get('mpn', '—')}*\n"
    )
    await update.message.reply_text(summary, parse_mode="Markdown")


async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "Available commands:\n"
        "/start – Start a new session\n"
        "/end – End the current session\n"
        "/session – Show current session data\n"
        "/help – Show this help message\n\n"
        "To continue, send the command."
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")


async def unknown_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_help(update, context)


async def handle_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data

    if "session_active" not in user_data:
        await update.message.reply_text("No active session. Use /start to begin.")
        return ConversationHandler.END

    if "image_urls" in user_data:
        public_ids = user_data.get("cloudinary_public_ids", [])
        for pid in public_ids:
            try:
                delete_image(pid)
            except Exception as e:
                logger.warning(f"Failed to delete cloudinary image: {e}")

        for key in ["image_urls", "title", "description", "color", "part_type",
                    "compatible_years", "ai_data_fetched", "photo_uploaded_once", "cloudinary_public_ids"]:
            user_data.pop(key, None)

        await update.message.reply_text("Returning to photo upload. Please send photo(s) again:")
        return ASKING_PRICE

    if "mpn" in user_data:
        user_data.pop("mpn")
        await update.message.reply_text("Returning to year input. Please re-enter the year:")
        return ASKING_YEAR

    if "year" in user_data:
        user_data.pop("year")
        await update.message.reply_text("Returning to model input. Please re-enter the model:")
        return ASKING_MODEL

    if "model" in user_data:
        user_data.pop("model")
        await update.message.reply_text("Returning to brand input. Please re-enter the brand:")
        return ASKING_BRAND

    await update.message.reply_text("Nothing to go back to.")
    return ConversationHandler.END


async def handle_continue(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send photo(s) of the next part:")
    return ASKING_PRICE


def create_conv_handler():
    return ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASKING_BRAND: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_brand_input)],
            ASKING_MODEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_model_input)],
            ASKING_YEAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_year_input)],
            ASKING_MPN: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_mpn_input)],
            ASKING_PRICE: [
                MessageHandler(filters.PHOTO | filters.Document.IMAGE, handle_photo),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_price_input)
            ]
        },
        fallbacks=[CommandHandler("end", end)]
    )


def register_handlers(app, create_conv_handler):
    app.add_handler(create_conv_handler)
    app.add_handler(CommandHandler("end", end))
    app.add_handler(CommandHandler("session", show_session_data))
    app.add_handler(CommandHandler("help", show_help))
    app.add_handler(CommandHandler("back", handle_back))
    app.add_handler(CommandHandler("continue", handle_continue))
    app.add_handler(MessageHandler(filters.ALL, unknown_input))
