from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from configs.product_profiles import find_profile, get_profile, list_profiles
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
    TRANSIENT_SESSION_KEYS,
)
from .listing import delete_cloudinary_images_async


async def show_session_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = context.user_data
    if not data.get(SESSION_ACTIVE):
        await update.message.reply_text("Session is not active. Start with /start.")
        return

    profile = get_profile(data.get(PROFILE_ID))
    answers = data.get(PROFILE_ANSWERS, {})
    lines = [
        f"*Current session ({profile.name}):*",
    ]
    for field in profile.fields:
        value = answers.get(field.key, "N/A") or "N/A"
        lines.append(f"- {field.prompt.split('(')[0].strip()}: *{value}*")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "Available commands:\n"
        "/start - Start a new session\n"
        "/end - End the current session\n"
        "/session - Show current session data\n"
        "/back - Go one step back\n"
        "/continue - Start a new product without ending the session\n"
        "/profile - View or select a product profile\n"
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
        return ASKING_PHOTOS

    fields = user_data.get(PROFILE_FIELDS) or []
    idx = user_data.get(PROFILE_FIELD_INDEX, 0)
    answers = user_data.get(PROFILE_ANSWERS, {})
    if idx > 0 and fields:
        field = fields[idx - 1]
        answers.pop(field.key, None)
        user_data[PROFILE_ANSWERS] = answers
        user_data[PROFILE_FIELD_INDEX] = idx - 1
        prompt = field.prompt
        if field.optional:
            prompt += " (type 'skip' to leave blank)"
        await update.message.reply_text(f"Returning to previous question:\n{prompt}")
        return COLLECTING_DETAILS

    await update.message.reply_text("Nothing to go back to.")
    return ConversationHandler.END


async def handle_continue(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send photo(s) of the next product:")
    return ASKING_PHOTOS


async def handle_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args if context.args else []
    if not args:
        profiles = list_profiles()
        lines = ["Available profiles:"]
        for profile in profiles:
            lines.append(f"- *{profile.id}*: {profile.name} — {profile.description}")
        lines.append("\nUse /profile <id> to select one (e.g., /profile generic).")
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
        return

    requested = args[0].lower()
    profile = find_profile(requested)
    if not profile:
        await update.message.reply_text(
            f"Unknown profile '{requested}'. Use /profile to view available options."
        )
        return

    context.user_data[PROFILE_ID] = profile.id
    await update.message.reply_text(
        f"Profile set to *{profile.name}*. Use /start to begin a session.",
        parse_mode="Markdown",
    )
