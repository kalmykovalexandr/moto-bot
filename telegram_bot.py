import logging
import asyncio
import contextlib
from telegram.ext import ApplicationBuilder
from configs.config import TELEGRAM_BOT_TOKEN
from handlers.handlers import create_conv_handler, register_handlers, error_handler

app_tg = None
_polling_task = None


async def start_bot():
    global app_tg, _polling_task
    app_tg = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).concurrent_updates(True).build()

    conv_handler = create_conv_handler()
    register_handlers(app_tg, conv_handler)
    app_tg.add_error_handler(error_handler)

    await app_tg.initialize()
    await app_tg.bot.delete_webhook(drop_pending_updates=True)
    await app_tg.start()

    _polling_task = asyncio.create_task(app_tg.updater.start_polling())
    logging.info("Telegram bot started (polling)")


async def stop_bot():
    global app_tg, _polling_task
    if not app_tg:
        return
    await app_tg.updater.stop()
    if _polling_task:
        _polling_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await _polling_task
        _polling_task = None
    await app_tg.stop()
    await app_tg.shutdown()
    logging.info("Telegram bot stopped")
