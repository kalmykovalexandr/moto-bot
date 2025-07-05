import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes
)
from ebay_api import publish_test_item

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    await update.message.reply_text("Uploading your photo and preparing the listing...")

    try:
        result = publish_test_item()  # 👈 вызываем напрямую
        await update.message.reply_text(result)
    except Exception as e:
        logger.error(f"eBay API error: {e}")
        await update.message.reply_text("An error occurred while publishing to eBay.")

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.run_polling()

if __name__ == "__main__":
    main()
