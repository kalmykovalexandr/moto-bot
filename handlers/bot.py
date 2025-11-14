import logging

from telegram.ext import CommandHandler, MessageHandler, filters

from .commands import (
    handle_back,
    handle_continue,
    handle_profile,
    show_help,
    show_session_data,
    unknown_input,
)
from .conversation import end

logger = logging.getLogger(__name__)


def register_handlers(app, conv_handler):
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("end", end))
    app.add_handler(CommandHandler("session", show_session_data))
    app.add_handler(CommandHandler("help", show_help))
    app.add_handler(CommandHandler("back", handle_back))
    app.add_handler(CommandHandler("continue", handle_continue))
    app.add_handler(CommandHandler("profile", handle_profile))
    app.add_handler(MessageHandler(filters.ALL, unknown_input))


async def error_handler(update, context):
    if context.error:
        logger.error("Exception while handling an update: %s", context.error, exc_info=True)
    if update and getattr(update, "message", None):
        await update.message.reply_text("An internal error occurred.")
