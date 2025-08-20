from configs.config import FULFILLMENT_POLICIES, WEIGHT_THRESHOLDS, DEFAULT_WEIGHT_CLASS, DEFAULT_FULFILLMENT_POLICY_ID

_ALLOWED = {"XS", "S", "M", "L", "XL", "XXL", "FREIGHT"}


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
