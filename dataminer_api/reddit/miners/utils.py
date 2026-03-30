import re
from datetime import datetime, timezone
from typing import Dict, List, Optional


def build_patterns(keywords: List[str]) -> Dict[str, re.Pattern]:
    """Compile keyword patterns once so miners can reuse them."""
    return {
        keyword: re.compile(rf"\b{re.escape(keyword)}\b", re.IGNORECASE)
        for keyword in keywords
    }


def find_keywords(text: Optional[str], patterns: Dict[str, re.Pattern]) -> List[str]:
    """Return every keyword whose compiled pattern matches the given text."""
    if not text:
        return []

    found = []
    for keyword, pattern in patterns.items():
        if pattern.search(text):
            found.append(keyword)
    return found


def created_utc_to_iso(created_utc: float) -> str:
    """Convert Reddit UTC timestamp to ISO 8601 string."""
    return datetime.fromtimestamp(created_utc, tz=timezone.utc).isoformat()


def normalize_keywords(keywords: Optional[List[str]]) -> List[str]:
    """Normalize a keyword list by removing empty values and duplicates."""
    if not keywords:
        return []

    normalized = []
    seen = set()
    for keyword in keywords:
        if not keyword:
            continue
        cleaned = keyword.strip()
        if not cleaned:
            continue
        lowered = cleaned.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        normalized.append(cleaned)
    return normalized
