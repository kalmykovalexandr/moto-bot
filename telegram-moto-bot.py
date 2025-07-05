import os
import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)

# Set your tokens and endpoint
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
EBAY_ENDPOINT = "https://web-production-bfa68.up.railway.app/publish"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Upload Photo", callback_data="upload_photo")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Welcome! This bot will help you list your products on eBay.",
        reply_markup=reply_markup
    )

# Callback for inline buttons
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "upload_photo":
        await query.edit_message_text("Please upload a photo of the item you want to sell.")

# Handle photo messages
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo_file = await update.message.photo[-1].get_file()
    photo_path = f"temp_{update.message.from_user.id}.jpg"
    await photo_file.download_to_drive(photo_path)

    await update.message.reply_text("Processing the photo and preparing the eBay listing...")

    # Optional: You can add recognition or GPT image processing here

    # Send POST request to your eBay backend
    try:
        response = requests.post(EBAY_ENDPOINT, json={})
        if response.status_code == 200:
            await update.message.reply_text("Item has been successfully published to eBay.")
        else:
            await update.message.reply_text(f"Failed to publish the item.\n{response.text}")
    except Exception as e:
        logger.error(f"Error while posting to eBay: {e}")
        await update.message.reply_text("An error occurred while publishing to eBay.")

# Main function to run the bot
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    app.run_polling()

if __name__ == "__main__":
    main()
