import json
from typing import Dict
from utils.shipping_util import WEIGHT_THRESHOLDS as THR, pick_weight_class_by_kg

async def analyze_motorcycle_part(
    image_url: str,
    brand: str,
    model: str,
    year: str,
    max_part_len: int = 60,
    openai_client=None,
    model_name: str = "gpt-4o-mini"
) -> Dict:

    thr = THR

    prompt_text = f"""
    You are a motorcycle parts expert. You will receive brand, model, year and an image of the part.
    Return a STRICT JSON object in ENGLISH ONLY. Detect whether this is a complete engine or a part.

    JSON schema (no extra keys, no markdown):
    {{
      "is_motor": boolean,
      "part_type": string,                          // e.g., "Front brake lever" (<= {max_part_len} chars, no brand/model/year)
      "color": string,                              // e.g., "Black"
      "compatible_years": string,                   // e.g., "1997–2000" or "N/A"

      "engine_type": string,                        // if is_motor else "N/A"
      "displacement": string,                       // e.g., "649 cc" or "N/A"
      "bore_stroke": string,                        // e.g., "83.0 x 60.0 mm" or "N/A"
      "compression_ratio": string,                  // e.g., "11.6:1" or "N/A"
      "max_power": string,                          // e.g., "50 kW (67 hp) @ 8000 rpm" or "N/A"
      "max_torque": string,                         // e.g., "64 Nm @ 6700 rpm" or "N/A"
      "cooling": string,                            // "Liquid"/"Air"/"Oil" or "N/A"
      "fuel_system": string,                        // e.g., "EFI", "Carburetor" or "N/A"
      "starter": string,                            // e.g., "Electric" or "N/A"
      "gearbox": string,                            // e.g., "6-speed" or "N/A"
      "final_drive": string,                        // e.g., "Chain" or "N/A"
      "recommended_oil": string,                    // e.g., "10W-40" or "N/A"
      "oil_capacity": string,                       // e.g., "2.1 L" or "N/A"

      "estimated_weight_kg": number | null,         // ESTIMATE part-only weight (no packaging). Use a realistic value.
      "weight_class": string | null,                // MUST be one of: XS, S, M, L, XL, XXL, FREIGHT according to thresholds below
      "description": string,                        // 1–3 concise EN sentences about the item
      "tags": string[]                              // 5–20 short EN keywords (no hashtags, no duplicates)
    }}

    Weight class thresholds (kg) — choose the SMALLEST class that fits the estimate:
    - XS: <= {thr["XS"]}
    - S:  <= {thr["S"]}
    - M:  <= {thr["M"]}
    - L:  <= {thr["L"]}
    - XL: <= {thr["XL"]}
    - XXL:<= {thr["XXL"]}
    - FREIGHT: > {thr["XXL"]}

    Context:
    - Brand: {brand}
    - Model: {model}
    - Year: {year}

    Rules:
    - ENGLISH ONLY.
    - If unknown, use "N/A" (or null where allowed).
    - Return ONLY valid JSON, no comments, no extra text.
    - Be consistent: "estimated_weight_kg" should match the chosen "weight_class".
    """

    messages = [
        {"role": "system", "content": "You are a precise assistant for motorcycle parts identification."},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt_text.strip()},
                {"type": "image_url", "image_url": {"url": image_url}}
            ],
        },
    ]

    resp = openai_client.chat.completions.create(
        model=model_name,
        messages=messages
    )

    raw = resp.choices[0].message.content.strip()
    try:
        data = json.loads(raw)
    except Exception:
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            data = json.loads(raw[start:end+1])
        else:
            data = {
                "is_motor": False,
                "part_type": "Part",
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
                "oil_capacity": "N/A",
                "estimated_weight_kg": None,
                "weight_class": None,
                "description": "",
                "tags": []
            }

    allowed = {"XS", "S", "M", "L", "XL", "XXL", "FREIGHT"}
    wc = str(data["weight_class"]).upper() if data["weight_class"] else None
    if wc not in allowed:
        try:
            est = float(data["estimated_weight_kg"]) if data["estimated_weight_kg"] is not None else None
        except Exception:
            est = None
        wc = pick_weight_class_by_kg(est)
    data["weight_class"] = wc

    for k in [
        "part_type","color","compatible_years","engine_type","displacement","bore_stroke",
        "compression_ratio","max_power","max_torque","cooling","fuel_system","starter",
        "gearbox","final_drive","recommended_oil","oil_capacity","description"
    ]:
        if k not in data or data[k] is None:
            data[k] = "N/A" if k != "description" else ""

    tags = data.get("tags") or []
    if not isinstance(tags, list):
        tags = [str(tags)]
    data["tags"] = [str(t).strip() for t in tags if str(t).strip()][:20]

    return data
