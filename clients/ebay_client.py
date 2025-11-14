import uuid
from typing import Any, Dict

import requests

from auth.ebay_oauth import get_access_token
from configs.config import (
    MARKETPLACE_ID,
    MERCHANT_LOCATION_KEY,
    PAYMENT_POLICY_ID,
    RETURN_POLICY_ID,
)

INVENTORY_CONDITION = "USED_EXCELLENT"
INVENTORY_CONDITION_DESCRIPTION = (
    "Pre-owned item with cosmetic wear, fully functional. Please check images for exact condition."
)
DEFAULT_CATEGORY_ID = "179753"
DEFAULT_CURRENCY = "USD"


def _build_headers(token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Content-Language": "en-US",
    }


def _build_inventory_payload(
    sku: str,
    title: str,
    description: str,
    image_urls: list[str],
    brand: str,
    model: str,
    mpn: str,
    color: str,
    material: str,
    product_type: str,
) -> Dict[str, Any]:
    aspects = {}
    if brand and brand != "N/A":
        aspects["Brand"] = [brand]
    if model and model != "N/A":
        aspects["Model"] = [model]
    if mpn and mpn != "N/A":
        aspects["Manufacturer Part Number"] = [mpn]
    if product_type and product_type != "N/A":
        aspects["Type"] = [product_type]
    if color and color != "N/A":
        aspects["Color"] = [color]
    if material and material != "N/A":
        aspects["Material"] = [material]

    return {
        "sku": sku,
        "availability": {"shipToLocationAvailability": {"quantity": 1}},
        "condition": INVENTORY_CONDITION,
        "conditionDescription": INVENTORY_CONDITION_DESCRIPTION,
        "product": {
            "title": title,
            "description": description,
            "imageUrls": image_urls,
            "brand": brand,
            "model": model,
            "mpn": mpn,
            "aspects": aspects,
        },
    }


def _build_offer_payload(
    sku: str,
    description: str,
    price: float,
    fulfillment_policy_id: str | None,
    category_id: str | None,
) -> Dict[str, Any]:
    resolved_category = category_id or DEFAULT_CATEGORY_ID
    return {
        "sku": sku,
        "marketplaceId": MARKETPLACE_ID,
        "format": "FIXED_PRICE",
        "availableQuantity": 1,
        "categoryId": resolved_category,
        "listingDescription": description,
        "listingPolicies": {
            "fulfillmentPolicyId": fulfillment_policy_id,
            "paymentPolicyId": PAYMENT_POLICY_ID,
            "returnPolicyId": RETURN_POLICY_ID,
        },
        "pricingSummary": {"price": {"value": f"{price:.2f}", "currency": DEFAULT_CURRENCY}},
        "quantityLimitPerBuyer": 1,
        "includeCatalogProductDetails": True,
        "merchantLocationKey": MERCHANT_LOCATION_KEY,
        "tax": {"applyTax": False},
        "hideBuyerDetails": False,
    }


def publish_item(
    title: str,
    description: str,
    brand: str,
    model: str,
    mpn: str,
    color: str,
    material: str,
    product_type: str,
    image_urls: list[str],
    price: float,
    fulfillment_policy_id: str | None = None,
    category_id: str | None = None,
) -> str:
    token, _ = get_access_token()
    headers = _build_headers(token)
    sku = f"sku-{str(uuid.uuid4())[:8]}"

    inventory_payload = _build_inventory_payload(
        sku=sku,
        title=title,
        description=description,
        image_urls=image_urls,
        brand=brand,
        model=model,
        mpn=mpn,
        color=color,
        material=material,
        product_type=product_type,
    )

    inv_response = requests.put(
        f"https://api.ebay.com/sell/inventory/v1/inventory_item/{sku}",
        headers=headers,
        json=inventory_payload,
        timeout=30,
    )
    if inv_response.status_code not in (200, 204):
        return f"Failed to create inventory item: {inv_response.status_code} {inv_response.text}"

    offer_payload = _build_offer_payload(
        sku=sku,
        description=description,
        price=price,
        fulfillment_policy_id=fulfillment_policy_id,
        category_id=category_id,
    )
    offer_response = requests.post(
        "https://api.ebay.com/sell/inventory/v1/offer",
        headers=headers,
        json=offer_payload,
        timeout=30,
    )
    if offer_response.status_code != 201:
        return f"Failed to create offer: {offer_response.status_code} {offer_response.text}"

    offer_id = offer_response.json().get("offerId")
    publish_response = requests.post(
        f"https://api.ebay.com/sell/inventory/v1/offer/{offer_id}/publish",
        headers=headers,
        timeout=30,
    )
    if publish_response.status_code != 200:
        return f"Failed to publish offer: {publish_response.status_code} {publish_response.text}"

    return f"Successfully published offer: {offer_id}"
