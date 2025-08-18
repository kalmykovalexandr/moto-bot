import json
import logging
import os
from openai import OpenAI

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


async def analyze_motorcycle_part(image_url: str, brand: str, model: str, year: str, max_part_len: int = 30):
    prompt = (
        f"You are a motorcycle specialist. In front of you is a photo of a motorcycle part.\n"
        f"The user has already provided the following information:\n- Brand: {brand}\n- Model: {model}\n- Year: {year}\n"
        "Your task: identify the part from the photo. Respond in JSON format with the following fields:\n"
        "- is_motor (true/false)\n"
        "- part_type (string, in Italian)\n"
        "- part_type_short (string, in Italian) = a concise name for the eBay title, "
        f"no brand/model/year, no articles, abbreviations allowed, MAX {max_part_len} characters\n"
        "- color (string, in Italian)\n- compatible_years (string, e.g., \"1997–2000\")\n"
        "If it is an engine, also include:\n"
        "- engine_type\n- displacement\n- bore_stroke\n"
        "- compression_ratio\n- max_power\n- max_torque\n- cooling\n"
        "- fuel_system\n- starter\n- gearbox\n- final_drive\n"
        "- recommended_oil\n- oil_capacity\n\n"
        "Respond ONLY in JSON format (do not add anything else, only JSON).\n"
        "If something is unknown, write \"N/A\".\n"
    )

    try:
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a motorcycle specialist."},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_url}},
                    ],
                },
            ],
            response_format={"type": "json_object"},
            max_tokens=800,
        )
        text = resp.choices[0].message.content.strip()
        return json.loads(text)
    except Exception as e:
        logger.error(f"Failed to parse AI response: {e}", exc_info=True)
        return {"is_motor": False}
