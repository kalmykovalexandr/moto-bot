from configs.config import EBAY_FPOLICY_ID_LIGHT, EBAY_FPOLICY_ID_DEFAULT, EBAY_FPOLICY_ID_MEDIUM, \
    EBAY_FPOLICY_ID_HEAVY, EBAY_FPOLICY_ID_XHEAVY

WEIGHT_THRESHOLDS = {"XS": 0.25, "S": 0.75, "M": 2.0, "L": 5.0, "XL": 999.0}


def pick_weight_class_by_kg(kg: float | None) -> str:
    if kg is None:
        return "M"
    try:
        w = float(kg)
    except Exception:
        return "M"
    if w <= WEIGHT_THRESHOLDS["XS"]: return "XS"
    if w <= WEIGHT_THRESHOLDS["S"]:  return "S"
    if w <= WEIGHT_THRESHOLDS["M"]:  return "M"
    if w <= WEIGHT_THRESHOLDS["L"]:  return "L"
    return "XL"


def pick_policy_by_weight_class(weight_class: str) -> str | None:
    wc = (weight_class or "").upper()
    if wc in ("XS", "S"):
        return EBAY_FPOLICY_ID_LIGHT or EBAY_FPOLICY_ID_DEFAULT
    if wc == "M":
        return EBAY_FPOLICY_ID_MEDIUM or EBAY_FPOLICY_ID_DEFAULT
    if wc == "L":
        return EBAY_FPOLICY_ID_HEAVY or EBAY_FPOLICY_ID_DEFAULT
    if wc == "XL":
        return EBAY_FPOLICY_ID_XHEAVY or EBAY_FPOLICY_ID_HEAVY or EBAY_FPOLICY_ID_DEFAULT
    return EBAY_FPOLICY_ID_DEFAULT
