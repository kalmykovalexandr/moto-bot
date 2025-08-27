from configs.config import FULFILLMENT_POLICIES, DEFAULT_FULFILLMENT_POLICY_ID

_ALLOWED = {"XS", "S", "M", "L", "XL", "XXL", "FREIGHT"}

# SHIPPING CONFIGS
DEFAULT_WEIGHT_CLASS = "M"
WEIGHT_THRESHOLDS = {
    "XS": 0.25,
    "S": 0.75,
    "M": 2.0,
    "L": 5.0,
    "XL": 20.0,
    "XXL": 50.0,
    # FREIGHT: > 50 kg
}

def pick_weight_class_by_kg(kg: float | None) -> str:
    if kg is None:
        return DEFAULT_WEIGHT_CLASS
    try:
        w = float(kg)
    except Exception:
        return DEFAULT_WEIGHT_CLASS

    thr = WEIGHT_THRESHOLDS
    if w <= thr["XS"]:  return "XS"
    if w <= thr["S"]:   return "S"
    if w <= thr["M"]:   return "M"
    if w <= thr["L"]:   return "L"
    if w <= thr["XL"]:  return "XL"
    if w <= thr["XXL"]: return "XXL"
    return "FREIGHT"


_CLASS_TO_POLICY = {
    "XS": FULFILLMENT_POLICIES["SHIP_XS"],
    "S": FULFILLMENT_POLICIES["SHIP_S"],
    "M": FULFILLMENT_POLICIES["SHIP_M"],
    "L": FULFILLMENT_POLICIES["SHIP_L"],
    "XL": FULFILLMENT_POLICIES["SHIP_XL"],
    "XXL": FULFILLMENT_POLICIES["SHIP_XXL"],
    "FREIGHT": FULFILLMENT_POLICIES["SHIP_FREIGHT"],
}


def pick_policy_by_weight_class(weight_class: str) -> str:
    wc = (weight_class or "").upper()
    if wc not in _ALLOWED:
        wc = DEFAULT_WEIGHT_CLASS
    return _CLASS_TO_POLICY.get(wc, DEFAULT_FULFILLMENT_POLICY_ID)
