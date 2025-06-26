import os
import logging
import datetime
import time
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

logging.basicConfig(level=logging.INFO)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Фото получено! 😉")

def wait_until_evening(start_hour=18, end_hour=23):
    while True:
        now = datetime.datetime.now()
        if start_hour <= now.hour < end_hour:
            logging.info("Наступило рабочее время. Бот запускается.")
            break
        logging.info(f"Сейчас {now.hour}:00 — нерабочее время. Засыпаю на 5 минут...")
        time.sleep(300)

def main():
    wait_until_evening(start_hour=16, end_hour=23)

    token = os.environ.get("BOT_TOKEN")
    app = ApplicationBuilder().token(token).build()
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.run_polling()

if __name__ == '__main__':
    main()
