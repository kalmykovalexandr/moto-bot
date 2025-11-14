import json
from typing import Any, Dict, List, Optional

from openai import AsyncOpenAI

from configs.config import OPENAI_API_KEY
from utils.shipping_util import WEIGHT_THRESHOLDS as DEFAULT_THRESHOLDS, pick_weight_class_by_kg

PROMPT_TEMPLATE = """
You are an e-commerce copywriter who inspects product photos and crafts marketplace listings.

Profile instructions:
{profile_hint}

User-provided hints:
{hints}

Return a STRICT JSON object (no Markdown, no comments) with this schema:
{{
  "title": string,                 // <= {max_title_len} characters
  "product_type": string,          // concise noun phrase (e.g., "Wireless headphones")
  "category_hint": string,         // best-fit catalog/category name
  "condition": string,             // New / Used / Refurbished / For parts / Unknown
  "material": string,
  "color": string,
  "brand": string,
  "model": string,
  "mpn": string,
  "included_items": string,
  "features": string[],            // 5-10 short selling points
  "description": string,           // 2-4 EN sentences
  "tags": string[],                // 5-15 keywords, no hashtags
  "estimated_weight_kg": number | null,
  "weight_class": string | null    // XS, S, M, L, XL, XXL, FREIGHT
}}

Weight class thresholds (kg):
{thresholds}

Rules:
- English only.
- If a field is unknown, output "N/A" (or null for numeric values).
- Ensure the JSON matches the schema exactly.
- Keep the title within the character limit and align estimated_weight_kg with weight_class.
"""

_client: Optional[AsyncOpenAI] = None


def _build_threshold_text(thresholds: Dict[str, float]) -> str:
    order = ["XS", "S", "M", "L", "XL", "XXL"]
    lines = [f"- {label}: <= {thresholds[label]}" for label in order]
    lines.append(f"- FREIGHT: > {thresholds['XXL']}")
    return "\n".join(lines)


def _format_hints(hints: Dict[str, str]) -> str:
    if not hints:
        return "None"
    lines = []
    for key, value in hints.items():
        value_str = str(value).strip()
        if not value_str:
            continue
        lines.append(f"- {key}: {value_str}")
    return "\n".join(lines) if lines else "None"


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


def _sanitize_str_list(values: Any, limit: int) -> List[str]:
    if isinstance(values, list):
        source = values
    elif values is None:
        source = []
    else:
        source = [values]
    cleaned: List[str] = []
    seen = set()
    for value in source:
        text = str(value).strip()
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(text[:120])
        if len(cleaned) >= limit:
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
        "title",
        "product_type",
        "category_hint",
        "condition",
        "material",
        "color",
        "brand",
        "model",
        "mpn",
        "included_items",
        "description",
    ]
    for field in text_fields:
        data[field] = data.get(field) or "N/A"
    data["features"] = _sanitize_str_list(data.get("features"), 10)
    data["tags"] = _sanitize_str_list(data.get("tags"), 20)
    return data


async def analyze_product(
    image_url: str,
    hints: Dict[str, str],
    profile_hint: str,
    max_title_len: int = 80,
    weight_thresholds: Optional[Dict[str, float]] = None,
    openai_client: Optional[AsyncOpenAI] = None,
    model_name: str = "gpt-4o-mini",
) -> Dict[str, Any]:
    thresholds = weight_thresholds or DEFAULT_THRESHOLDS
    prompt_text = PROMPT_TEMPLATE.format(
        max_title_len=max_title_len,
        thresholds=_build_threshold_text(thresholds),
        profile_hint=profile_hint or "General consumer product.",
        hints=_format_hints(hints),
    ).strip()

    client = _get_client(openai_client)
    response = await client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": "You create structured marketplace listings."},
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
    return _apply_defaults(data)
