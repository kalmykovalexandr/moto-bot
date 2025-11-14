from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

MAX_TITLE_LEN = 80
_PLACEHOLDER_VALUES = {"n/a", "na", "none", "unknown", "unspecified"}

_TEMPLATES_DIR = Path("templates")
_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATES_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
    trim_blocks=True,
    lstrip_blocks=True,
)


def compose_listing_title(
    ai_title: str | None,
    user_hint: str | None,
    brand: str | None,
    model: str | None,
) -> str:
    base = _sanitize_component(ai_title) or _sanitize_component(user_hint) or "Product"
    extras = []
    clean_brand = _sanitize_component(brand)
    clean_model = _sanitize_component(model)
    if clean_brand and clean_brand.lower() not in base.lower():
        extras.append(clean_brand)
    if clean_model and clean_model.lower() not in base.lower():
        extras.append(clean_model)
    candidate = " ".join([base] + extras).strip()
    if not candidate:
        candidate = "Product"
    return _cut_to(candidate, MAX_TITLE_LEN)


def generate_product_description(template_name: str, **kwargs: Any) -> str:
    tmpl = _env.get_template(template_name)
    normalized = {key: _safe_text(value) for key, value in kwargs.items()}
    return tmpl.render(**normalized)


def _safe_text(value: Any) -> Any:
    if isinstance(value, str):
        text = value.strip()
        return text if text else "N/A"
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return value


def _sanitize_component(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = _normalize_spaces(value)
    if not cleaned or cleaned.lower() in _PLACEHOLDER_VALUES:
        return None
    return cleaned


def _normalize_spaces(text: str) -> str:
    return " ".join(str(text).split())


def _cut_to(text: str, limit: int) -> str:
    cleaned = _normalize_spaces(text)
    return cleaned if len(cleaned) <= limit else cleaned[:limit].rstrip()
