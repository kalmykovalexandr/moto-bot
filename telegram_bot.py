import logging
from telegram.ext import ApplicationBuilder
from configs.config import TELEGRAM_BOT_TOKEN
from handlers.handlers import create_conv_handler, register_handlers, error_handler

app_tg = None

async def start_bot():
    global app_tg
    app_tg = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).concurrent_updates(True).build()

    conv_handler = create_conv_handler()
    register_handlers(app_tg, conv_handler)
    app_tg.add_error_handler(error_handler)

    await app_tg.initialize()
    await app_tg.bot.delete_webhook(drop_pending_updates=True)
    await app_tg.start()
    await app_tg.updater.start_polling()
    logging.info("Telegram bot started (polling)")

async def stop_bot():
    global app_tg
    if not app_tg:
        return
    await app_tg.updater.stop()
    await app_tg.stop()
    await app_tg.shutdown()
    logging.info("Telegram bot stopped")
