import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes
)
from ebay_api import publish_item
import tempfile
from telegram.ext import ConversationHandler
import cloudinary
import cloudinary.uploader

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ASKING_PRICE = 1

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

cloudinary.config(
    cloud_name="dczhgkjpa",
    api_key="838981728989476",
    api_secret="0qgudi-oz4c8KNRUFsk7lTsXX3M"
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("Upload Photo", callback_data="upload_photo")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Welcome! This bot will help you list your products on eBay.",
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "upload_photo":
        await query.edit_message_text("Please upload a photo of the item you want to sell.")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photos = update.message.photo
    if not photos:
        await update.message.reply_text("Please send at least one photo.")
        return

    image_urls = []
    for i, photo in enumerate(photos):
        file = await photo.get_file()
        temp_path = f"temp_{update.message.from_user.id}_{i}.jpg"
        await file.download_to_drive(temp_path)

        # Upload to Cloudinary
        uploaded = cloudinary.uploader.upload(temp_path)
        hosted_url = uploaded["secure_url"]
        image_urls.append(hosted_url)

        # Optionally delete local file
        try:
            os.remove(temp_path)
        except Exception as e:
            logger.warning(f"Failed to delete temp file: {e}")

    # Save item metadata
    context.user_data["image_urls"] = image_urls
    context.user_data["title"] = "Samsung Galaxy S8"
    context.user_data["description"] = "Refurbished Samsung Galaxy S8 64GB - Black"
    context.user_data["brand"] = "Samsung"
    context.user_data["model"] = "Galaxy S8"
    context.user_data["mpn"] = "SM-G950F"
    context.user_data["color"] = "Nero"
    context.user_data["capacity"] = "64 GB"

    await update.message.reply_text("Please enter the price (in EUR):")
    return ASKING_PRICE

async def handle_price_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    price_text = update.message.text
    try:
        price = float(price_text)
    except ValueError:
        await update.message.reply_text("Invalid price. Please enter a numeric value like 19.99.")
        return ASKING_PRICE

    # Получаем все сохранённые данные
    data = context.user_data
    result = publish_item(
        title=data["title"],
        description=data["description"],
        brand=data["brand"],
        model=data["model"],
        mpn=data["mpn"],
        color=data["color"],
        capacity=data["capacity"],
        image_urls=data["image_urls"],
        price=price
    )

    await update.message.reply_text(result)
    context.user_data.clear()
    return ConversationHandler.END

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f"Exception while handling an update: {context.error}", exc_info=True)

    if update and hasattr(update, "message"):
        try:
            await update.message.reply_text("An internal error occurred. The bot will now stop.")
        except Exception:
            pass

    # Stop the bot gracefully
    if context.application:
        logger.warning("Stopping bot due to error...")
        await context.application.stop()

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.PHOTO, handle_photo)],
        states={ASKING_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_price_input)]},
        fallbacks=[]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(conv_handler)

    # Register error handler
    app.add_error_handler(error_handler)

    app.run_polling()

if __name__ == "__main__":
    main()
