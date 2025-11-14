from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(frozen=True)
class FieldConfig:
    key: str
    prompt: str
    optional: bool = False


@dataclass(frozen=True)
class ProductProfile:
    id: str
    name: str
    description: str
    fields: List[FieldConfig] = field(default_factory=list)
    template: str = "product_description.html"
    ai_hint: str = ""


GENERIC_PROFILE = ProductProfile(
    id="generic",
    name="Generic Product",
    description="Use for any consumer item (electronics, apparel, collectibles, etc.).",
    ai_hint=(
        "You help describe any physical product for online marketplaces. "
        "Highlight features, materials, included items, and best use cases."
    ),
    fields=[
        FieldConfig(
            key="title_hint",
            prompt="What item are you listing? Provide a concise name (e.g., 'Wireless headphones').",
        ),
        FieldConfig(
            key="brand",
            prompt="Enter the product brand (or type 'skip' if unknown).",
            optional=True,
        ),
        FieldConfig(
            key="model",
            prompt="Enter the model/variant (or type 'skip').",
            optional=True,
        ),
        FieldConfig(
            key="condition",
            prompt="Enter the condition (New / Used / Refurbished / For parts).",
        ),
        FieldConfig(
            key="sku",
            prompt="Enter SKU/MPN/Code (or type 'skip').",
            optional=True,
        ),
        FieldConfig(
            key="color",
            prompt="Enter the main color (or type 'skip').",
            optional=True,
        ),
        FieldConfig(
            key="material",
            prompt="Enter the main material (or type 'skip').",
            optional=True,
        ),
    ],
)

PRODUCT_PROFILES: Dict[str, ProductProfile] = {
    GENERIC_PROFILE.id: GENERIC_PROFILE,
}

DEFAULT_PROFILE_ID = GENERIC_PROFILE.id


def get_profile(profile_id: Optional[str]) -> ProductProfile:
    if not profile_id:
        return PRODUCT_PROFILES[DEFAULT_PROFILE_ID]
    return PRODUCT_PROFILES.get(profile_id, PRODUCT_PROFILES[DEFAULT_PROFILE_ID])


def find_profile(profile_id: str) -> Optional[ProductProfile]:
    return PRODUCT_PROFILES.get(profile_id)


def list_profiles() -> List[ProductProfile]:
    return list(PRODUCT_PROFILES.values())
