from telegram import Update
from telegram.ext import (
    CommandHandler,
    ConversationHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from configs.product_profiles import DEFAULT_PROFILE_ID, get_profile
from .constants import (
    ASKING_PHOTOS,
    ASKING_PRICE,
    COLLECTING_DETAILS,
    IMAGE_URLS,
    PROFILE_ANSWERS,
    PROFILE_FIELD_INDEX,
    PROFILE_FIELDS,
    PROFILE_ID,
    SESSION_ACTIVE,
)
from .listing import handle_photo, handle_price_input


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    selected_profile = context.user_data.get(PROFILE_ID, DEFAULT_PROFILE_ID)
    context.user_data.clear()
    context.user_data[PROFILE_ID] = selected_profile
    context.user_data[SESSION_ACTIVE] = True
    profile = get_profile(selected_profile)
    context.user_data[PROFILE_FIELDS] = profile.fields
    context.user_data[PROFILE_FIELD_INDEX] = 0
    context.user_data[PROFILE_ANSWERS] = {}

    intro = (
        f"Profile: *{profile.name}*\n"
        f"{profile.description}\n\n"
        "Let's gather some product details."
    )
    await update.message.reply_text(intro, parse_mode="Markdown")
    return await _prompt_next_field(update, context, profile)


async def _prompt_next_field(update: Update, context: ContextTypes.DEFAULT_TYPE, profile):
    idx = context.user_data.get(PROFILE_FIELD_INDEX, 0)
    fields = profile.fields
    if idx >= len(fields):
        context.user_data[IMAGE_URLS] = []
        await update.message.reply_text("Great! Now send photo(s) of the product.")
        return ASKING_PHOTOS

    field = fields[idx]
    prompt = field.prompt
    if field.optional:
        prompt += " (type 'skip' to leave blank)"
    await update.message.reply_text(prompt)
    return COLLECTING_DETAILS


async def handle_field_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    profile = get_profile(context.user_data.get(PROFILE_ID))
    idx = context.user_data.get(PROFILE_FIELD_INDEX, 0)
    fields = profile.fields
    if idx >= len(fields):
        await update.message.reply_text("All details collected. Please send photo(s).")
        return ASKING_PHOTOS

    field = fields[idx]
    text = (update.message.text or "").strip()
    if not text and not field.optional:
        await update.message.reply_text("Please provide a value.")
        return COLLECTING_DETAILS

    if field.optional and text.lower() == "skip":
        value = ""
    else:
        value = text

    context.user_data.setdefault(PROFILE_ANSWERS, {})
    context.user_data[PROFILE_ANSWERS][field.key] = value
    context.user_data[PROFILE_FIELD_INDEX] = idx + 1
    return await _prompt_next_field(update, context, profile)


async def end(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Session ended. To start a new session, type /start.")
    return ConversationHandler.END


def create_conv_handler():
    return ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            COLLECTING_DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_field_input)],
            ASKING_PHOTOS: [
                MessageHandler(filters.PHOTO | filters.Document.IMAGE, handle_photo),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_photo),
            ],
            ASKING_PRICE: [
                MessageHandler(filters.PHOTO | filters.Document.IMAGE, handle_photo),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_price_input),
            ],
        },
        fallbacks=[CommandHandler("end", end)],
    )
