import os
import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters,
    ContextTypes, ConversationHandler
)
from ebay_api import publish_item
import tempfile
import cloudinary
import cloudinary.uploader
from telegram.request import HTTPXRequest
import requests
from openai import OpenAI
import json
import re

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ASKING_BRAND = 0
ASKING_MODEL = 1
ASKING_YEAR = 2
ASKING_MPN = 3
ASKING_PRICE = 4

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

cloudinary.config(
    cloud_name="dczhgkjpa",
    api_key="838981728989476",
    api_secret="0qgudi-oz4c8KNRUFsk7lTsXX3M"
)

client = OpenAI(api_key=OPENAI_API_KEY)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    context.user_data["session_active"] = True
    await update.message.reply_text(
        "Welcome! Please enter the motorcycle brand (e.g., Honda):"
    )
    return ASKING_BRAND

async def end(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Session ended. To start a new session, type /start.")
    return ConversationHandler.END

async def handle_brand_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    brand = update.message.text.strip()
    context.user_data["brand"] = brand
    await update.message.reply_text(
        "Now enter the motorcycle model (e.g., Transalp 650):"
    )
    return ASKING_MODEL

async def handle_model_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    model = update.message.text.strip()
    context.user_data["model"] = model
    await update.message.reply_text(
        "Now enter the year of the motorcycle (e.g., 1999):"
    )
    return ASKING_YEAR

async def handle_year_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    year = update.message.text.strip()
    context.user_data["year"] = year
    await update.message.reply_text(
        "Now enter the MPN (Manufacturer Part Number) of the motorcycle part:"
    )
    return ASKING_MPN

async def handle_mpn_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mpn = update.message.text.strip()
    context.user_data["mpn"] = mpn
    context.user_data["image_urls"] = []
    await update.message.reply_text(
        f"Session started for model: *{context.user_data['model']}* year: *{context.user_data['year']}*\nMPN: *{mpn}*\n\nNow send photo(s) of the part.",
        parse_mode="Markdown"
    )
    return ASKING_PRICE

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    files = update.message.photo or []
    if update.message.document:
        files.append(update.message.document)

    if not files:
        await update.message.reply_text("Please send a valid image file.")
        return ASKING_PRICE

    image_urls = context.user_data.get("image_urls", [])
    first_photo_path = None

    cloudinary_ids = context.user_data.get("cloudinary_public_ids", [])
    for i, item in enumerate(files):
        file = await item.get_file()
        temp_path = f"temp_{update.message.from_user.id}_{i}.jpg"
        await file.download_to_drive(temp_path)

        try:
            uploaded = cloudinary.uploader.upload(temp_path)
            hosted_url = uploaded["secure_url"]
            cloudinary_ids.append(uploaded["public_id"])
            image_urls.append(hosted_url)
        except Exception as e:
            logger.error(f"Cloudinary upload failed: {e}")
            continue
        finally:
            try:
                if i == 0:
                    first_photo_path = temp_path
                else:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
            except Exception as e:
                logger.warning(f"Failed to delete temp file: {e}")

    context.user_data["image_urls"] = image_urls

    if context.user_data.get("ai_data_fetched"):
        if not context.user_data.get("photo_uploaded_once"):
            await update.message.reply_text("Photo(s) uploaded.\nNow enter the price (e.g., 19.99):")
            context.user_data["photo_uploaded_once"] = True
        return ASKING_PRICE

    # AI processing (only once)
    ai_data = await analyze_motorcycle_part(
        image_url=image_urls[0],
        brand=context.user_data["brand"],
        model=context.user_data["model"],
        year=context.user_data["year"]
    )

    if ai_data["is_motor"]:
        title = generate_motor_title(
            context.user_data["brand"],
            context.user_data["model"],
            ai_data["compatible_years"]
        )
        description = generate_motor_description(
            brand=context.user_data["brand"],
            model=context.user_data["model"],
            engine_type=ai_data["engine_type"],
            displacement=ai_data["displacement"],
            bore_stroke=ai_data["bore_stroke"],
            compression_ratio=ai_data["compression_ratio"],
            max_power=ai_data["max_power"],
            max_torque=ai_data["max_torque"],
            cooling=ai_data["cooling"],
            fuel_system=ai_data["fuel_system"],
            starter=ai_data["starter"],
            gearbox=ai_data["gearbox"],
            final_drive=ai_data["final_drive"],
            recommended_oil=ai_data["recommended_oil"],
            oil_capacity=ai_data["oil_capacity"],
            year=context.user_data["year"],
            compatible_years=ai_data["compatible_years"],
            color=ai_data["color"],
            mpn=context.user_data["mpn"]
        )
    else:
        title = generate_part_title(
            ai_data["part_type"],
            context.user_data["brand"],
            context.user_data["model"],
            ai_data["compatible_years"]
        )
        description = generate_part_description(
            brand=context.user_data["brand"],
            model=context.user_data["model"],
            year=context.user_data["year"],
            compatible_years=ai_data["compatible_years"],
            part_type=ai_data["part_type"],
            color=ai_data["color"],
            mpn=context.user_data["mpn"]
        )

    if first_photo_path:
        try:
            os.remove(first_photo_path)
        except Exception as e:
            logger.warning(f"Failed to delete first photo file: {e}")

    context.user_data.update({
        "image_urls": image_urls,
        "title": title,
        "description": description,
        "color": ai_data["color"],
        "compatible_years": ai_data["compatible_years"],
        "part_type": ai_data["part_type"],
        "ai_data_fetched": True,
        "photo_uploaded_once": True,
        "cloudinary_public_ids": cloudinary_ids
    })

    await update.message.reply_text("Photo(s) uploaded.\nNow enter the price (e.g., 19.99):")
    return ASKING_PRICE

async def handle_price_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    price_text = update.message.text
    try:
        price = float(price_text)
    except ValueError:
        await update.message.reply_text("Invalid price. Please enter a numeric value like 19.99.")
        return ASKING_PRICE

    data = context.user_data
    result = publish_item(
        title=context.user_data["title"],
        description=context.user_data["description"],
        brand=data["brand"],
        model=data["model"],
        mpn=data["mpn"],
        color=data["color"],
        image_urls=data["image_urls"],
        price=price,
        compatible_years=data["compatible_years"],
        part_type=data["part_type"]
    )

    await update.message.reply_text(result)
    context.user_data.clear()
    return ConversationHandler.END

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f"Exception while handling an update: {context.error}", exc_info=True)
    if update and hasattr(update, "message"):
        try:
            await update.message.reply_text("An internal error occurred.")
        except Exception:
            pass

    if context.application:
        await context.application.stop()

def generate_motor_description(**kwargs) -> str:
    with open("templates/motor_description.html", encoding="utf-8") as f:
        return f.read().format(**kwargs)

def generate_part_description(**kwargs) -> str:
    with open("templates/part_description.html", encoding="utf-8") as f:
        return f.read().format(**kwargs)

def generate_motor_title(brand, model, compatible_years):
    return f"Motore {brand} {model} {compatible_years} Usato Funzionante"

def generate_part_title(part_type, brand, model, compatible_years):
    return f"{part_type} {brand} {model} {compatible_years} Usato Originale"

async def analyze_motorcycle_part(image_url: str, brand: str, model: str, year: str) -> dict:
    prompt = f"""
    Ты специалист по мотоциклам. Перед тобой фотография запчасти мотоцикла.
    Пользователь уже ввёл следующие данные:
    - Бренд: {brand}
    - Модель: {model}
    - Год: {year}

    Твоя задача: по фото определить, что это за запчасть. Ответь в формате JSON с полями:
    - is_motor (true/false)
    - part_type (string, на итальянском)
    - color (string, на итальянском)
    - compatible_years (string, например "1997–2000")
    Если это мотор, также добавь:
    - engine_type
    - displacement
    - bore_stroke
    - compression_ratio
    - max_power
    - max_torque
    - cooling
    - fuel_system
    - starter
    - gearbox
    - final_drive
    - recommended_oil
    - oil_capacity

    Ответь ТОЛЬКО в формате JSON (не добавляй ничего другого, только JSON):
    {{
      "is_motor": true/false,
      "part_type": "название на итальянском",
      "color": "цвет на итальянском",
      "compatible_years": "например, 1999–2003",
      "engine_type": "...",
      "displacement": "...",
      ...
    }}

    Если что-то неизвестно — напиши "N/A".
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Ты технический специалист по мотоциклам."},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_url}}
                    ]
                }
            ],
            max_tokens=1000
        )

        text = response.choices[0].message.content.strip()
        print(f"[DEBUG] AI Response: {text}")

        json_match = re.search(r"\{.*\}", text, re.DOTALL)
        if not json_match:
            logger.error("AI response is not JSON-formatted.")
            return fallback_data()

        return json.loads(json_match.group())

    except Exception as e:
        logger.error(f"Failed to parse AI response: {e}")
        return {
            "is_motor": False,
            "part_type": "N/A",
            "color": "N/A",
            "compatible_years": "N/A",
            "engine_type": "N/A",
            "displacement": "N/A",
            "bore_stroke": "N/A",
            "compression_ratio": "N/A",
            "max_power": "N/A",
            "max_torque": "N/A",
            "cooling": "N/A",
            "fuel_system": "N/A",
            "starter": "N/A",
            "gearbox": "N/A",
            "final_drive": "N/A",
            "recommended_oil": "N/A",
            "oil_capacity": "N/A"
        }

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
        "*Available commands:*\n"
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

    if "image_urls" in user_data:
        public_ids = user_data.get("cloudinary_public_ids", [])
        for pid in public_ids:
            try:
                cloudinary.uploader.destroy(pid)
            except Exception as e:
                logger.warning(f"Failed to delete cloudinary image: {e}")

        for key in ["image_urls", "title", "description", "color", "part_type",
                    "compatible_years", "ai_data_fetched", "photo_uploaded_once", "cloudinary_public_ids"]:
            user_data.pop(key, None)

        await update.message.reply_text("Returning to photo upload. Please send photo(s) again:")
        return ASKING_PRICE

    await update.message.reply_text("Nothing to go back to.")
    return ConversationHandler.END

def main():
    token = TELEGRAM_TOKEN
    requests.get(f"https://api.telegram.org/bot{token}/deleteWebhook")

    request = HTTPXRequest(connect_timeout=10.0, read_timeout=10.0)
    app = ApplicationBuilder().token(token).request(request).build()

    conv_handler = ConversationHandler(
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

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("end", end))
    app.add_handler(CommandHandler("session", show_session_data))
    app.add_handler(CommandHandler("help", show_help))
    app.add_handler(CommandHandler("back", handle_back))
    app.add_handler(MessageHandler(filters.ALL, unknown_input))
    app.add_error_handler(error_handler)
    app.run_polling()

if __name__ == "__main__":
    main()
