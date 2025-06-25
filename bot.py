import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# Логирование для отладки
logging.basicConfig(level=logging.INFO)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = update.effective_chat.id
    logging.info(f"Photo received from {user.username} in chat {chat_id}")
    await update.message.reply_text("Фото получено! Скоро начнём загрузку на eBay 😉")

def main():
    import os
    token = os.environ.get("BOT_TOKEN")
    app = ApplicationBuilder().token(token).build()

    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    app.run_polling()

if __name__ == '__main__':
    main()
