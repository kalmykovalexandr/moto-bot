import requests
from telegram.ext import ApplicationBuilder

from config import TELEGRAM_TOKEN
from handlers import create_conv_handler, register_handlers, error_handler


def main():
    requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/deleteWebhook")
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    conversation_handler = create_conv_handler()

    register_handlers(app, conversation_handler)
    app.add_error_handler(error_handler)
    app.run_polling()

if __name__ == "__main__":
    main()