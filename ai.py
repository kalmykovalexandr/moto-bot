from openai import OpenAI
from config import OPENAI_API_KEY
from openai.types.chat.chat_completion_message_param import (
    ChatCompletionUserMessageParam,
    ChatCompletionSystemMessageParam,
)
import logging
import json
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)


async def analyze_motorcycle_part(image_url: str, brand: str, model: str, year: str):
    prompt = (
        f"You are a motorcycle specialist. In front of you is a photo of a motorcycle part.\n"
        f"The user has already provided the following information:\n- Brand: {brand}\n- Model: {model}\n- Year: {year}\n"
        "Your task: identify the part from the photo. Respond in JSON format with the following fields:\n"
        "- is_motor (true/false)\n- part_type (string, in Italian)\n"
        "- color (string, in Italian)\n- compatible_years (string, e.g., \"1997–2000\")\n"
        "If it is an engine, also include:\n"
        "- engine_type\n- displacement\n- bore_stroke\n"
        "- compression_ratio\n- max_power\n- max_torque\n- cooling\n"
        "- fuel_system\n- starter\n- gearbox\n- final_drive\n"
        "- recommended_oil\n- oil_capacity\n\n"
        "Respond ONLY in JSON format (do not add anything else, only JSON):\n"
        "{\n  \"is_motor\": true/false,\n  \"part_type\": \"name in Italian\",\n"
        "  \"color\": \"color in Italian\",\n  \"compatible_years\": \"e.g., 1999–2003\",\n"
        "  \"engine_type\": \"...\",\n  \"displacement\": \"...\",\n  ...  \n}\n"
        "If something is unknown, write \"N/A\".\n"
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                ChatCompletionSystemMessageParam(role="system", content="You are a motorcycle specialist."),
                ChatCompletionUserMessageParam(role="user", content=f"{prompt}\nHere is an image: {image_url}")
            ],
            max_tokens=1000
        )

        text = response.choices[0].message.content.strip()
        json_match = re.search(r"\{.*}", text, re.DOTALL)

        logger.info(response)

        if not json_match:
            logger.error("AI response is not JSON-formatted.")
            return {}

        return json.loads(json_match.group())
    except Exception as e:
        logger.error(f"Failed to parse AI response: {e}")
        return {"is_motor": False}
