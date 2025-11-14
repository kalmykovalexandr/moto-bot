import logging
import time
from typing import Optional, Tuple

import requests

from auth.ebay_oauth import get_access_token
from configs.config import EBAY_CATEGORY_TREE_ID

logger = logging.getLogger(__name__)

_CACHE_TTL_SECONDS = 300
_cache: dict[str, Tuple[float, Tuple[Optional[str], Optional[str]]]] = {}


def _cache_get(query: str) -> Optional[Tuple[Optional[str], Optional[str]]]:
    key = query.lower().strip()
    cached = _cache.get(key)
    if not cached:
        return None
    timestamp, value = cached
    if time.time() - timestamp > _CACHE_TTL_SECONDS:
        _cache.pop(key, None)
        return None
    return value


def _cache_set(query: str, value: Tuple[Optional[str], Optional[str]]):
    key = query.lower().strip()
    _cache[key] = (time.time(), value)


def suggest_category(query: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Returns (category_id, category_name) suggested by eBay for the given query.
    """
    if not query:
        return None, None

    cached = _cache_get(query)
    if cached:
        return cached

    token, _ = get_access_token()
    url = (
        f"https://api.ebay.com/commerce/taxonomy/v1_beta/category_tree/"
        f"{EBAY_CATEGORY_TREE_ID}/get_category_suggestions"
    )
    params = {"q": query}
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=15)
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.warning("Category suggestion failed for query '%s': %s", query, exc)
        return None, None

    data = response.json()
    suggestions = data.get("categorySuggestions") or []
    if not suggestions:
        _cache_set(query, (None, None))
        return None, None

    category = suggestions[0].get("category") or {}
    category_id = category.get("categoryId")
    category_name = category.get("categoryName")
    result = (category_id, category_name)
    _cache_set(query, result)
    return result
