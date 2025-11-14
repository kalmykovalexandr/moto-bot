import json
from typing import Any, Dict, List, Optional

from openai import AsyncOpenAI

from configs.config import OPENAI_API_KEY
from utils.shipping_util import WEIGHT_THRESHOLDS as DEFAULT_THRESHOLDS, pick_weight_class_by_kg

PROMPT_TEMPLATE = """
You are a motorcycle parts expert. You will receive brand, model, year and an image of the part.
Return a STRICT JSON object in ENGLISH ONLY. Detect whether this is a complete engine or part.

JSON schema (no extra keys, no markdown):
{{
  "is_motor": boolean,
  "part_type": string,                          // e.g., "Front brake lever" (<= {max_part_len} chars)
  "color": string,                              // e.g., "Black"
  "compatible_years": string,                   // e.g., "1997-2000" or "N/A"

  "engine_type": string,
  "displacement": string,
  "bore_stroke": string,
  "compression_ratio": string,
  "max_power": string,
  "max_torque": string,
  "cooling": string,
  "fuel_system": string,
  "starter": string,
  "gearbox": string,
  "final_drive": string,
  "recommended_oil": string,
  "oil_capacity": string,

  "estimated_weight_kg": number | null,
  "weight_class": string | null,                // XS, S, M, L, XL, XXL, FREIGHT
  "description": string,                        // 1-3 concise EN sentences
  "tags": string[]                              // 5-20 short EN keywords
}}

Weight class thresholds (kg) - choose the SMALLEST class that fits the estimate:
{thresholds}

Context:
- Brand: {brand}
- Model: {model}
- Year: {year}

Rules:
- English only.
- If unknown, use "N/A" (or null where allowed).
- Return ONLY valid JSON, no comments.
- Ensure estimated weight aligns with the chosen weight_class.
"""

_client: Optional[AsyncOpenAI] = None


def _build_threshold_text(thresholds: Dict[str, float]) -> str:
    order = ["XS", "S", "M", "L", "XL", "XXL"]
    lines = [f"- {label}: <= {thresholds[label]}" for label in order]
    lines.append(f"- FREIGHT: > {thresholds['XXL']}")
    return "\n".join(lines)


def _get_client(client: Optional[AsyncOpenAI]) -> AsyncOpenAI:
    global _client
    if client:
        return client
    if _client is None:
        if not OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY is not configured.")
        _client = AsyncOpenAI(api_key=OPENAI_API_KEY)
    return _client


def _safe_json_loads(raw: str) -> Dict[str, Any]:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(raw[start : end + 1])
        return {}


def _sanitize_tags(tags: Any) -> List[str]:
    cleaned: List[str] = []
    if isinstance(tags, list):
        source = tags
    elif tags is None:
        source = []
    else:
        source = [tags]

    seen = set()
    for tag in source:
        tag_str = str(tag).strip()
        if not tag_str:
            continue
        key = tag_str.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(tag_str[:60])
        if len(cleaned) >= 20:
            break
    return cleaned


def _normalize_weight_class(weight_class: Optional[str], estimated_weight: Any) -> str:
    allowed = {"XS", "S", "M", "L", "XL", "XXL", "FREIGHT"}
    if weight_class and weight_class.upper() in allowed:
        return weight_class.upper()
    try:
        weight_value = float(estimated_weight) if estimated_weight is not None else None
    except (TypeError, ValueError):
        weight_value = None
    return pick_weight_class_by_kg(weight_value)


def _apply_defaults(data: Dict[str, Any]) -> Dict[str, Any]:
    text_fields = [
        "part_type",
        "color",
        "compatible_years",
        "engine_type",
        "displacement",
        "bore_stroke",
        "compression_ratio",
        "max_power",
        "max_torque",
        "cooling",
        "fuel_system",
        "starter",
        "gearbox",
        "final_drive",
        "recommended_oil",
        "oil_capacity",
    ]
    for field in text_fields:
        data[field] = data.get(field) or "N/A"
    data["description"] = data.get("description", "")
    return data


async def analyze_motorcycle_part(
    image_url: str,
    brand: str,
    model: str,
    year: str,
    max_part_len: int = 60,
    weight_thresholds: Optional[Dict[str, float]] = None,
    openai_client: Optional[AsyncOpenAI] = None,
    model_name: str = "gpt-4o-mini",
) -> Dict[str, Any]:
    thresholds = weight_thresholds or DEFAULT_THRESHOLDS
    prompt_text = PROMPT_TEMPLATE.format(
        max_part_len=max_part_len,
        thresholds=_build_threshold_text(thresholds),
        brand=brand,
        model=model,
        year=year,
    ).strip()

    client = _get_client(openai_client)
    response = await client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": "You are a precise assistant for motorcycle parts identification."},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt_text},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ],
            },
        ],
    )

    raw = (response.choices[0].message.content or "").strip()
    data = _safe_json_loads(raw)
    data["weight_class"] = _normalize_weight_class(
        data.get("weight_class"),
        data.get("estimated_weight_kg"),
    )
    data["tags"] = _sanitize_tags(data.get("tags"))
    return _apply_defaults(data)
