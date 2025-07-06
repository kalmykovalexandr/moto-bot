import os
import logging
from telegram import Update
from telegram.ext import (ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler)
from ebay_api import publish_item
import tempfile
import cloudinary
import cloudinary.uploader
from telegram.request import HTTPXRequest
import requests
from openai import OpenAI
import json
import re

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ASKING_BRAND = 0
ASKING_MODEL = 1
ASKING_YEAR = 2
ASKING_MPN = 3
ASKING_PRICE = 4

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

cloudinary.config(
    cloud_name="dczhgkjpa",
    api_key="838981728989476",
    api_secret="0qgudi-oz4c8KNRUFsk7lTsXX3M"
)

client = OpenAI(api_key=OPENAI_API_KEY)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome! Please enter the motorcycle brand (e.g., Honda):"
    )
    return ASKING_BRAND

async def handle_brand_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    brand = update.message.text.strip()
    context.user_data["brand"] = brand
    await update.message.reply_text(
        "Now enter the motorcycle model (e.g., Transalp 650):"
    )
    return ASKING_MODEL

async def handle_model_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    model = update.message.text.strip()
    context.user_data["model"] = model
    await update.message.reply_text(
        "Now enter the year of the motorcycle (e.g., 1999):"
    )
    return ASKING_YEAR

async def handle_year_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    year = update.message.text.strip()
    context.user_data["year"] = year
    await update.message.reply_text(
        "Now enter the MPN (Manufacturer Part Number) of the motorcycle part:"
    )
    return ASKING_MPN

async def handle_mpn_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mpn = update.message.text.strip()
    context.user_data["mpn"] = mpn
    context.user_data["image_urls"] = []
    await update.message.reply_text(
        f"All parts will be associated with model: *{context.user_data['model']}* and year: *{context.user_data['year']}*\nMPN: *{mpn}*\n\nNow send one or more photos of the part (as regular photos or documents).",
        parse_mode="Markdown"
    )
    return ASKING_PRICE

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    files = update.message.photo or []
    if update.message.document:
        files.append(update.message.document)

    if not files:
        await update.message.reply_text("Please send a valid image file.")
        return ASKING_PRICE

    image_urls = []
    first_photo_path = None

    for i, item in enumerate(files):
        file = await item.get_file()
        temp_path = f"temp_{update.message.from_user.id}_{i}.jpg"
        await file.download_to_drive(temp_path)

        try:
            uploaded = cloudinary.uploader.upload(temp_path)
            hosted_url = uploaded["secure_url"]
            image_urls.append(hosted_url)
        except Exception as e:
            logger.error(f"Cloudinary upload failed: {e}")
            await update.message.reply_text("Failed to upload image.")
            continue
        finally:
            try:
                if i == 0:
                    first_photo_path = temp_path
                else:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
            except Exception as e:
                logger.warning(f"Failed to delete temp file: {e}")

    ai_data = await analyze_motorcycle_part(
        image_url=image_urls[0],
        brand=context.user_data["brand"],
        model=context.user_data["model"],
        year=context.user_data["year"]
    )

    if ai_data["is_motor"]:
        title = generate_motor_title(
            context.user_data["brand"],
            context.user_data["model"],
            ai_data["compatible_years"]
        )
        description = generate_motor_description(
            brand=context.user_data["brand"],
            model=context.user_data["model"],
            engine_type=ai_data["engine_type"],
            displacement=ai_data["displacement"],
            bore_stroke=ai_data["bore_stroke"],
            compression_ratio=ai_data["compression_ratio"],
            max_power=ai_data["max_power"],
            max_torque=ai_data["max_torque"],
            cooling=ai_data["cooling"],
            fuel_system=ai_data["fuel_system"],
            starter=ai_data["starter"],
            gearbox=ai_data["gearbox"],
            final_drive=ai_data["final_drive"],
            recommended_oil=ai_data["recommended_oil"],
            oil_capacity=ai_data["oil_capacity"],
            year=context.user_data["year"],
            compatible_years=ai_data["compatible_years"],
            color=ai_data["color"],
            mpn=context.user_data["mpn"]
        )
    else:
        title = generate_part_title(
            ai_data["part_type"],
            context.user_data["brand"],
            context.user_data["model"],
            ai_data["compatible_years"]
        )
        description = generate_part_description(
            brand=context.user_data["brand"],
            model=context.user_data["model"],
            year=context.user_data["year"],
            compatible_years=ai_data["compatible_years"],
            part_type=ai_data["part_type"],
            color=ai_data["color"],
            mpn=context.user_data["mpn"]
        )

    if first_photo_path:
        try:
            os.remove(first_photo_path)
        except Exception as e:
            logger.warning(f"Failed to delete first photo file: {e}")


    context.user_data.update({
        "image_urls": image_urls,
        "title": title,
        "description": description,
        "color": ai_data["color"],
        "compatible_years": ai_data["compatible_years"],
        "part_type": ai_data["part_type"]
    })

    await update.message.reply_text("Photo(s) uploaded.")
    return ASKING_PRICE

async def handle_price_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    price_text = update.message.text
    try:
        price = float(price_text)
    except ValueError:
        await update.message.reply_text("Invalid price. Please enter a numeric value like 19.99.")
        return ASKING_PRICE

    data = context.user_data
    result = publish_item(
        title=context.user_data["title"],
        description=context.user_data["description"],
        brand=data["brand"],
        model=data["model"],
        mpn=data["mpn"],
        color=data["color"],
        image_urls=data["image_urls"],
        price=price,
        compatible_years=data["compatible_years"],
        part_type=data["part_type"]
    )

    await update.message.reply_text(result)
    context.user_data.clear()
    return ConversationHandler.END

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f"Exception while handling an update: {context.error}", exc_info=True)
    if update and hasattr(update, "message"):
        try:
            await update.message.reply_text("An internal error occurred.")
        except Exception:
            pass

    if context.application:
        await context.application.stop()

def generate_motor_description(
    brand: str,
    model: str,
    engine_type: str,
    displacement: str,
    bore_stroke: str,
    compression_ratio: str,
    max_power: str,
    max_torque: str,
    cooling: str,
    fuel_system: str,
    starter: str,
    gearbox: str,
    final_drive: str,
    recommended_oil: str,
    oil_capacity: str,
    year: str,
    compatible_years: str,
    color: str,
    mpn: str
    ) -> str:
    motor_description_template = """
        Motore {brand}  {model} Usato (Completo)

        Caratteristiche tecniche:
        • Tipo motore: {engine_type}
        • Cilindrata: {displacement}
        • Alesaggio × corsa: {bore_stroke}
        • Rapporto di compressione: {compression_ratio}
        • Potenza massima: {max_power}
        • Coppia massima: {max_torque}
        • Raffreddamento: {cooling}
        • Alimentazione: {fuel_system}
        • Avviamento: {starter}
        • Cambio: {gearbox}
        • Trasmissione finale: {final_drive}
        • Olio consigliato: {recommended_oil}
        • Capacità olio: {oil_capacity}
        • Anno: {year}
        • Anni compatibili: {compatible_years}
        • Colore: {color}
        • Codice (MPN): {mpn}

        Il motore è usato, testato e perfettamente funzionante. Presenta normali segni di usura estetica.
        Controlla attentamente le foto per verificare le condizioni reali del prodotto.

        Spedizione veloce e sicura in tutta Italia, mondo.

        Se il ricambio ricevuto risulta danneggiato durante la spedizione o non è funzionante,
        provvederemo al rimborso completo oppure alla sostituzione con un pezzo equivalente, se disponibile.
    """
    return motor_description_template.format(
        brand=brand,
        model=model,
        engine_type=engine_type,
        displacement=displacement,
        bore_stroke=bore_stroke,
        compression_ratio=compression_ratio,
        max_power=max_power,
        max_torque=max_torque,
        cooling=cooling,
        fuel_system=fuel_system,
        starter=starter,
        gearbox=gearbox,
        final_drive=final_drive,
        recommended_oil=recommended_oil,
        oil_capacity=oil_capacity,
        year=year,
        compatible_years=compatible_years,
        color=color,
        mpn=mpn
    )

def generate_part_description(
        brand: str,
        model: str,
        year: str,
        compatible_years: str,
        part_type: str,
        color: str,
        mpn: str
    ) -> str:
    general_description_template = """\
        Ricambio usato per moto – {brand} {model}

        Dettagli:
        • Compatibile con: {model}
        • Anno: {year}
        • Anno compatibile: {compatible_years}
        • Tipo di pezzo: {part_type}
        • Colore: {color}
        • Codice/MPN: {mpn}

        Parte originale usata, testata e perfettamente funzionante.
        Presenta segni di usura compatibili con l’utilizzo.
        Verifica le condizioni effettive tramite le foto allegate.

        Spedizione veloce e sicura in tutta Italia, mondo.

        Se il ricambio ricevuto risulta danneggiato durante la spedizione o non è funzionante,
        provvederemo al rimborso completo oppure alla sostituzione con un pezzo equivalente, se disponibile.
    """
    return general_description_template.format(
        brand=brand,
        model=model,
        year=year,
        compatible_years=compatible_years,
        part_type=part_type,
        color=color,
        mpn=mpn
    )

def generate_motor_title(brand, model, compatible_years):
    return f"Motore {brand} {model} {compatible_years} Usato Funzionante"

def generate_part_title(part_type, brand, model, compatible_years):
    return f"{part_type} {brand} {model} {compatible_years} Usato Originale"

async def analyze_motorcycle_part(image_url: str, brand: str, model: str, year: str) -> dict:
    prompt = f"""
    Ты специалист по мотоциклам. Перед тобой фотография запчасти мотоцикла.
    Пользователь уже ввёл следующие данные:
    - Бренд: {brand}
    - Модель: {model}
    - Год: {year}

    Твоя задача: по фото определить, что это за запчасть. Ответь в формате JSON с полями:
    - is_motor (true/false)
    - part_type (string, на итальянском)
    - color (string, на итальянском)
    - compatible_years (string, например "1997–2000")
    Если это мотор, также добавь:
    - engine_type
    - displacement
    - bore_stroke
    - compression_ratio
    - max_power
    - max_torque
    - cooling
    - fuel_system
    - starter
    - gearbox
    - final_drive
    - recommended_oil
    - oil_capacity

    Если что-то неизвестно — напиши "N/A".
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Ты технический специалист по мотоциклам."},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_url}}
                    ]
                }
            ],
            max_tokens=1000
        )

        raw_response = response.choices[0].message.content
        logger.debug(f"AI raw response: {raw_response}")

        match = re.search(r'\{.*\}', raw_response, re.DOTALL)
        if match:
            json_text = match.group()
            return json.loads(json_text)
        else:
            raise ValueError("No JSON object found in AI response.")

    except Exception as e:
        logger.error(f"Failed to parse AI response: {e}")
        return {
            "is_motor": False,
            "part_type": "N/A",
            "color": "N/A",
            "compatible_years": "N/A",
            "engine_type": "N/A",
            "displacement": "N/A",
            "bore_stroke": "N/A",
            "compression_ratio": "N/A",
            "max_power": "N/A",
            "max_torque": "N/A",
            "cooling": "N/A",
            "fuel_system": "N/A",
            "starter": "N/A",
            "gearbox": "N/A",
            "final_drive": "N/A",
            "recommended_oil": "N/A",
            "oil_capacity": "N/A"
        }

def main():
    token = TELEGRAM_TOKEN
    requests.get(f"https://api.telegram.org/bot{token}/deleteWebhook")

    request = HTTPXRequest(connect_timeout=10.0, read_timeout=10.0)
    app = ApplicationBuilder().token(token).request(request).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASKING_BRAND: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_brand_input)],
            ASKING_MODEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_model_input)],
            ASKING_YEAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_year_input)],
            ASKING_MPN: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_mpn_input)],
            ASKING_PRICE: [
                MessageHandler(filters.PHOTO | filters.Document.IMAGE, handle_photo),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_price_input)
            ]
        },
        fallbacks=[]
    )

    app.add_handler(conv_handler)
    app.add_error_handler(error_handler)
    app.run_polling()

if __name__ == "__main__":
    main()
