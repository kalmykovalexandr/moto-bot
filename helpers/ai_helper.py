import asyncio
import json
import logging

from openai import OpenAI

from configs.config import OPENAI_API_KEY, WEIGHT_THRESHOLDS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

client = OpenAI(api_key=OPENAI_API_KEY)


def _call_openai(prompt: str, image_url: str) -> str:
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
        temperature=0.2,
    )
    return resp.choices[0].message.content.strip()


async def analyze_motorcycle_part(image_url: str, brand: str, model: str, year: str, max_part_len: int = 30):
    thr = WEIGHT_THRESHOLDS
    prompt = (
        f"You are a motorcycle specialist. You will see a photo of a motorcycle part.\n"
        f"User provided:\n- Brand: {brand}\n- Model: {model}\n- Year: {year}\n\n"
        "Task: identify the part and ESTIMATE its weight (part only, no packaging). "
        "Respond ONLY in JSON with fields:\n"
        "- is_motor (true/false)\n"
        "- part_type (Italian)\n"
        f"- part_type_short (Italian, max {max_part_len} chars, no brand/model/year)\n"
        "- color (Italian)\n"
        "- compatible_years (string like \"1997–2000\" or \"N/A\")\n"
        "- estimated_weight_kg (number, decimals allowed, e.g. 0.6)\n"
        "- weight_class (one of: XS, S, M, L, XL, XXL, FREIGHT) using these thresholds:\n"
        f"  XS: <= {thr['XS']} kg | "
        f"S: <= {thr['S']} kg | "
        f"M: <= {thr['M']} kg | "
        f"L: <= {thr['L']} kg | "
        f"XL: <= {thr['XL']} kg | "
        f"XXL: <= {thr['XXL']} kg | "
        "FREIGHT: > {thr['XXL']} kg\n"
        "If it's an engine (motor), also include:\n"
        "- engine_type, displacement, bore_stroke, compression_ratio, max_power, max_torque,\n"
        "- cooling, fuel_system, starter, gearbox, final_drive, recommended_oil, oil_capacity\n"
        "If unknown, use \"N/A\"."
    )

    try:
        text = await asyncio.to_thread(_call_openai, prompt, image_url)
        return json.loads(text)
    except Exception as e:
        logger.error(f"Failed to parse AI response: {e}", exc_info=True)
        return {"is_motor": False}
