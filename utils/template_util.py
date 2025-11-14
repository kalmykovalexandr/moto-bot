from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

MAX_TITLE_LEN = 80

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
    base = _normalize_spaces(ai_title or user_hint or "Product")
    extras = []
    if brand and brand.lower() not in base.lower():
        extras.append(brand)
    if model and model.lower() not in base.lower():
        extras.append(model)
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


def _normalize_spaces(text: str) -> str:
    return " ".join(str(text).split())


def _cut_to(text: str, limit: int) -> str:
    cleaned = _normalize_spaces(text)
    return cleaned if len(cleaned) <= limit else cleaned[:limit].rstrip()
