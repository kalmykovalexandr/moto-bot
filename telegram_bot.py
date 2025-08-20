import asyncio
import logging
from telegram.ext import ApplicationBuilder
from configs.config import TELEGRAM_BOT_TOKEN
from handlers.handlers import create_conv_handler, register_handlers, error_handler


async def start_bot():
    app_tg = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    conv_handler = create_conv_handler()
    register_handlers(app_tg, conv_handler)
    app_tg.add_error_handler(error_handler)

    await app_tg.bot.delete_webhook(drop_pending_updates=True)
    await app_tg.run_polling()


def run_in_background():
    asyncio.create_task(start_bot())
    logging.info("Telegram bot started in background")
