from telegram import Update
from telegram.ext import (
    CommandHandler,
    ConversationHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from .constants import (
    ASKING_BRAND,
    ASKING_MODEL,
    ASKING_MPN,
    ASKING_PRICE,
    ASKING_YEAR,
    BRAND,
    IMAGE_URLS,
    MODEL,
    MPN,
    SESSION_ACTIVE,
    YEAR,
)
from .listing import handle_photo, handle_price_input


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    context.user_data[SESSION_ACTIVE] = True
    await update.message.reply_text("Welcome! Please enter the motorcycle brand (e.g., Honda):")
    return ASKING_BRAND


async def end(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Session ended. To start a new session, type /start.")
    return ConversationHandler.END


async def handle_brand_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data[BRAND] = update.message.text.strip()
    await update.message.reply_text("Now enter the motorcycle model (e.g., Transalp 650):")
    return ASKING_MODEL


async def handle_model_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data[MODEL] = update.message.text.strip()
    await update.message.reply_text("Now enter the year of the motorcycle (e.g., 1999):")
    return ASKING_YEAR


async def handle_year_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data[YEAR] = update.message.text.strip()
    await update.message.reply_text("Now enter the MPN (Manufacturer Part Number) of the motorcycle part:")
    return ASKING_MPN


async def handle_mpn_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data[MPN] = update.message.text.strip()
    context.user_data[IMAGE_URLS] = []
    summary = (
        f"Session started for moto: {context.user_data.get(BRAND)} - {context.user_data.get(MODEL)}\n"
        f"Year: {context.user_data.get(YEAR)}\n"
        f"MPN: {context.user_data.get(MPN)}\n\n"
        "Now send photo(s) of the part."
    )
    await update.message.reply_text(summary, parse_mode="Markdown")
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
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_price_input),
            ],
        },
        fallbacks=[CommandHandler("end", end)],
    )
