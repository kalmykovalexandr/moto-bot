from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from .constants import (
    ASKING_BRAND,
    ASKING_MODEL,
    ASKING_PRICE,
    ASKING_YEAR,
    BRAND,
    IMAGE_URLS,
    MODEL,
    MPN,
    SESSION_ACTIVE,
    TRANSIENT_SESSION_KEYS,
    YEAR,
)
from .listing import delete_cloudinary_images_async


async def show_session_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = context.user_data
    if not data.get(SESSION_ACTIVE):
        await update.message.reply_text("Session is not active. Start with /start.")
        return

    summary = (
        "*Current session:*\n"
        f"- Brand: *{data.get(BRAND, 'N/A')}*\n"
        f"- Model: *{data.get(MODEL, 'N/A')}*\n"
        f"- Year: *{data.get(YEAR, 'N/A')}*\n"
        f"- MPN: *{data.get(MPN, 'N/A')}*\n"
    )
    await update.message.reply_text(summary, parse_mode="Markdown")


async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "Available commands:\n"
        "/start - Start a new session\n"
        "/end - End the current session\n"
        "/session - Show current session data\n"
        "/back - Go one step back\n"
        "/continue - Skip to the next part\n"
        "/help - Show this help message\n\n"
        "Send one of the commands to proceed."
    )
    await update.message.reply_text(help_text)


async def unknown_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_help(update, context)


async def handle_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data

    if SESSION_ACTIVE not in user_data:
        await update.message.reply_text("No active session. Use /start to begin.")
        return ConversationHandler.END

    if IMAGE_URLS in user_data:
        await delete_cloudinary_images_async(context)
        for key in TRANSIENT_SESSION_KEYS:
            user_data.pop(key, None)
        await update.message.reply_text("Returning to photo upload. Please send photo(s) again:")
        return ASKING_PRICE

    if MPN in user_data:
        user_data.pop(MPN, None)
        await update.message.reply_text("Returning to year input. Please re-enter the year:")
        return ASKING_YEAR

    if YEAR in user_data:
        user_data.pop(YEAR, None)
        await update.message.reply_text("Returning to model input. Please re-enter the model:")
        return ASKING_MODEL

    if MODEL in user_data:
        user_data.pop(MODEL, None)
        await update.message.reply_text("Returning to brand input. Please re-enter the brand:")
        return ASKING_BRAND

    await update.message.reply_text("Nothing to go back to.")
    return ConversationHandler.END


async def handle_continue(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send photo(s) of the next part:")
    return ASKING_PRICE
