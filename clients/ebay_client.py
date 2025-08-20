import uuid

import requests

from auth.ebay_oauth import get_access_token
from configs.config import (
    PAYMENT_POLICY_ID,
    RETURN_POLICY_ID,
    MERCHANT_LOCATION_KEY,
    DEFAULT_FULFILLMENT_POLICY_ID,
)


def publish_item(
        title,
        description,
        brand,
        model,
        mpn,
        color,
        image_urls,
        price,
        compatible_years,
        part_type,
        fulfillment_policy_id: str | None = None
):
    token = get_access_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Content-Language": "it-IT",
    }

    # если из handlers ничего не пришло — используем дефолт
    effective_fpolicy_id = fulfillment_policy_id or DEFAULT_FULFILLMENT_POLICY_ID

    sku = f"sku-{str(uuid.uuid4())[:8]}"

    inventory_payload = {
        "availability": {"shipToLocationAvailability": {"quantity": 1}},
        "condition": "USED_EXCELLENT",
        "conditionDescription": (
            "Parte usata con segni di usura estetici, perfettamente funzionante. "
            "Controlla le foto per le condizioni esatte. / Used part with cosmetic wear, "
            "fully functional. Please check images for exact condition."
        ),
        "product": {
            "title": title,
            "description": description,
            "imageUrls": image_urls,
            "brand": brand,
            "mpn": mpn,
            "aspects": {
                "Marca": [brand],
                "MPN": [mpn],
                "Produttore compatibile": [brand],
                "Tipo": [part_type],
                "Colore": [color],
                "Ricambio": ["Sì"],
                "Destinazione d'uso": ["Parte di ricambio"],
            },
        },
    }

    inv = requests.put(
        f"https://api.ebay.com/sell/inventory/v1/inventory_item/{sku}",
        headers=headers,
        json=inventory_payload,
        timeout=30,
    )
    if inv.status_code not in (200, 204):
        return f"Failed to create inventory item: {inv.status_code} {inv.text}"

    offer_payload = {
        "sku": sku,
        "marketplaceId": "EBAY_IT",
        "format": "FIXED_PRICE",
        "availableQuantity": 1,
        "categoryId": "179753",
        "listingDescription": description,
        "listingPolicies": {
            "fulfillmentPolicyId": effective_fpolicy_id,
            "paymentPolicyId": PAYMENT_POLICY_ID,
            "returnPolicyId": RETURN_POLICY_ID,
        },
        "pricingSummary": {"price": {"value": str(price), "currency": "EUR"}},
        "quantityLimitPerBuyer": 1,
        "includeCatalogProductDetails": True,
        "merchantLocationKey": MERCHANT_LOCATION_KEY,
        "tax": {"applyTax": False},
        "hideBuyerDetails": False,
    }

    offer = requests.post(
        "https://api.ebay.com/sell/inventory/v1/offer",
        headers=headers,
        json=offer_payload,
        timeout=30,
    )
    if offer.status_code != 201:
        return f"Failed to create offer: {offer.status_code} {offer.text}"

    offer_id = offer.json().get("offerId")
    pub = requests.post(
        f"https://api.ebay.com/sell/inventory/v1/offer/{offer_id}/publish",
        headers=headers,
        timeout=30,
    )
    if pub.status_code != 200:
        return f"Failed to publish offer: {pub.status_code} {pub.text}"

    return f"Successfully published offer: {offer_id}"
