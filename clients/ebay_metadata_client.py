import logging
import time
from typing import Optional, Tuple

import requests

from auth.ebay_oauth import get_access_token
from configs.config import EBAY_CATEGORY_TREE_ID, MARKETPLACE_ID

logger = logging.getLogger(__name__)

_CACHE_TTL_SECONDS = 300
_cache: dict[str, Tuple[float, Tuple[Optional[str], Optional[str]]]] = {}
_category_tree_id: Optional[str] = EBAY_CATEGORY_TREE_ID.strip() if EBAY_CATEGORY_TREE_ID else None


def _cache_key(query: str, tree_id: Optional[str]) -> str:
    key = query.lower().strip()
    tree = (tree_id or "unknown").strip()
    return f"{tree}:{key}"


def _cache_get(query: str, tree_id: Optional[str]) -> Optional[Tuple[Optional[str], Optional[str]]]:
    key = _cache_key(query, tree_id)
    cached = _cache.get(key)
    if not cached:
        return None
    timestamp, value = cached
    if time.time() - timestamp > _CACHE_TTL_SECONDS:
        _cache.pop(key, None)
        return None
    return value


def _cache_set(query: str, tree_id: Optional[str], value: Tuple[Optional[str], Optional[str]]):
    key = _cache_key(query, tree_id)
    _cache[key] = (time.time(), value)


def _fetch_default_category_tree_id(token: str) -> Optional[str]:
    url = "https://api.ebay.com/commerce/taxonomy/v1/get_default_category_tree_id"
    params = {"marketplace_id": MARKETPLACE_ID}
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    try:
        response = requests.get(url, headers=headers, params=params, timeout=15)
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.warning("Failed to fetch default category tree id: %s", exc)
        return None

    data = response.json() if response.content else {}
    tree_id = data.get("categoryTreeId")
    if not tree_id:
        logger.warning("Default category tree id missing in response: %s", data)
    return tree_id


def _resolve_category_tree_id(token: str) -> Optional[str]:
    global _category_tree_id
    if _category_tree_id:
        return _category_tree_id
    tree_id = _fetch_default_category_tree_id(token)
    if tree_id:
        _category_tree_id = tree_id
    return _category_tree_id


def suggest_category(query: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Returns (category_id, category_name) suggested by eBay for the given query.
    """
    if not query:
        return None, None

    token, _ = get_access_token()
    tree_id = _resolve_category_tree_id(token)
    if not tree_id:
        logger.warning("Unable to resolve category tree id; skipping suggestion.")
        return None, None

    cached = _cache_get(query, tree_id)
    if cached:
        return cached

    url = (
        f"https://api.ebay.com/commerce/taxonomy/v1/category_tree/"
        f"{tree_id}/get_category_suggestions"
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
        logger.warning(
            "Category suggestion failed for query '%s' with tree %s: %s", query, tree_id, exc
        )
        return None, None

    data = response.json()
    suggestions = data.get("categorySuggestions") or []
    if not suggestions:
        _cache_set(query, tree_id, (None, None))
        return None, None

    category = suggestions[0].get("category") or {}
    category_id = category.get("categoryId")
    category_name = category.get("categoryName")
    result = (category_id, category_name)
    _cache_set(query, tree_id, result)
    return result
