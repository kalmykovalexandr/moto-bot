import json
import logging

from openai import OpenAI

from configs.config import OPENAI_API_KEY

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)


async def analyze_motorcycle_part(image_url: str, brand: str, model: str, year: str, max_part_len: int = 30):
    prompt = (
        f"You are a motorcycle specialist. In front of you is a photo of a motorcycle part.\n"
        f"The user has provided:\n- Brand: {brand}\n- Model: {model}\n- Year: {year}\n\n"
        "Task: identify the part and ESTIMATE weight for shipping. Respond ONLY in JSON with fields:\n"
        "- is_motor (true/false)\n"
        "- part_type (Italian)\n"
        f"- part_type_short (Italian) = concise name, MAX {max_part_len} chars (no brand/model/year)\n"
        "- color (Italian)\n"
        "- compatible_years (string like \"1997–2000\")\n"
        "- estimated_weight_kg (number) = rough estimate of the PART weight (not packaged). Use decimals (e.g., 0.6).\n"
        "- weight_class (one of: XS, S, M, L, XL) based on these thresholds:\n"
        "  XS: <=0.25 kg | S: <=0.75 kg | M: <=2 kg | L: <=5 kg | XL: >5 kg\n"
        "If it is an engine, also include:\n"
        "- engine_type, displacement, bore_stroke, compression_ratio, max_power, max_torque,\n"
        "- cooling, fuel_system, starter, gearbox, final_drive, recommended_oil, oil_capacity\n"
        "If unknown, use \"N/A\".\n"
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
