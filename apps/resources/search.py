"""Lightweight Persian/English facility search."""

from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher

from .models import Facility

_CHAR_TRANSLATION = str.maketrans(
    {
        "ي": "ی",
        "ى": "ی",
        "ك": "ک",
        "أ": "ا",
        "إ": "ا",
        "آ": "ا",
        "ٱ": "ا",
        "ة": "ه",
        "ۀ": "ه",
    }
)
_DIACRITICS = re.compile(r"[\u064B-\u065F\u0670\u0640]")
_PUNCTUATION = re.compile(r"[^\w\s]", re.UNICODE)
_WHITESPACE = re.compile(r"\s+")

# Terms that are useful on their own but too broad to be the sole match in a
# multi-word query (for example, "زمین" in "زمین فوتبال").
GENERIC_TERMS = frozenset(
    {
        "زمین",
        "سالن",
        "ورزشی",
        "ورزش",
        "محل",
        "مرکز",
        "field",
        "court",
        "ground",
        "pitch",
        "hall",
        "sports",
        "sport",
    }
)

# Related terms let "شنا" find pools and "فوتبال" find artificial turf.
RELATED_TERMS: dict[str, tuple[str, ...]] = {
    "فوتبال": ("چمن مصنوعی", "فوتسال", "soccer", "football", "futsal"),
    "فوتسال": ("فوتبال", "futsal", "soccer", "football"),
    "چمن": ("چمن مصنوعی", "artificial turf", "turf"),
    "مصنوعی": ("چمن مصنوعی", "artificial turf"),
    "چمن مصنوعی": ("چمن", "مصنوعی", "artificial turf", "turf"),
    "تنیس": ("tennis",),
    "بدمینتون": ("badminton",),
    "شنا": ("استخر", "swimming", "pool"),
    "استخر": ("شنا", "swimming", "pool"),
    "سالن": ("سالن ورزشی", "hall", "gym", "sports hall"),
    "ورزشی": ("ورزش", "سالن ورزشی", "sport", "sports", "gym"),
    "ورزش": ("ورزشی", "sport", "sports"),
    "سالن ورزشی": ("سالن", "ورزشی", "gym", "sports hall", "hall"),
    "زمین": ("field", "court", "ground", "pitch"),
    "soccer": ("فوتبال", "چمن مصنوعی", "فوتسال"),
    "football": ("فوتبال", "چمن مصنوعی", "فوتسال"),
    "futsal": ("فوتسال", "فوتبال"),
    "tennis": ("تنیس",),
    "badminton": ("بدمینتون",),
    "swimming": ("شنا", "استخر"),
    "pool": ("استخر", "شنا"),
    "gym": ("سالن ورزشی", "سالن", "ورزشی"),
    "hall": ("سالن", "سالن ورزشی"),
    "sports": ("ورزشی", "ورزش", "سالن ورزشی"),
    "sport": ("ورزشی", "ورزش"),
    "sports hall": ("سالن ورزشی", "سالن", "ورزشی"),
    "field": ("زمین",),
    "court": ("زمین",),
    "ground": ("زمین",),
    "pitch": ("زمین",),
    "turf": ("چمن مصنوعی", "چمن"),
    "artificial": ("چمن مصنوعی",),
    "artificial turf": ("چمن مصنوعی", "چمن", "turf"),
}

FIELD_WEIGHTS = {"name": 5, "type": 3, "location": 2}


def normalize_text(value: str) -> str:
    """Normalize Persian/Arabic variants, punctuation, and whitespace."""

    text = unicodedata.normalize("NFKC", value or "")
    text = text.translate(_CHAR_TRANSLATION)
    text = _DIACRITICS.sub("", text)
    text = text.replace("\u200c", " ").replace("\u200d", " ")
    text = _PUNCTUATION.sub(" ", text)
    text = _WHITESPACE.sub(" ", text)
    return text.strip().lower()


def _compact(text: str) -> str:
    return text.replace(" ", "")


def _contains(text: str, term: str) -> bool:
    if not text or not term:
        return False
    if term in text:
        return True
    compact_term = _compact(term)
    return bool(compact_term) and compact_term in _compact(text)


def _starts_with(text: str, term: str) -> bool:
    if not text or not term:
        return False
    return text.startswith(term) or _compact(text).startswith(_compact(term))


def _equals(text: str, term: str) -> bool:
    if not text or not term:
        return False
    return text == term or _compact(text) == _compact(term)


def _variants(term: str) -> set[str]:
    variants = {term}
    variants.update(RELATED_TERMS.get(term, ()))
    return {variant for variant in variants if variant}


def _normalized_fields(facility: Facility) -> dict[str, str]:
    return {
        "name": normalize_text(facility.name),
        "type": normalize_text(facility.type),
        "location": normalize_text(facility.location),
    }


def _fuzzy_match_text(text: str, term: str) -> bool:
    """Match a query token to a field word with a small edit tolerance."""

    if len(term) < 5 or term in GENERIC_TERMS:
        return False

    for word in text.split():
        if abs(len(word) - len(term)) > 2:
            continue
        if SequenceMatcher(None, term, word).ratio() >= 0.85:
            return True
    return False


def _fuzzy_term_matches(term: str, fields: dict[str, str]) -> bool:
    return any(_fuzzy_match_text(text, term) for text in fields.values())


def _term_matches(term: str, fields: dict[str, str]) -> bool:
    if any(
        _contains(text, variant)
        for text in fields.values()
        for variant in _variants(term)
    ):
        return True
    return _fuzzy_term_matches(term, fields)


def _is_relevant(tokens: list[str], fields: dict[str, str]) -> bool:
    """Reject weak matches so unrelated facilities are not returned."""

    if not tokens:
        return True
    if len(tokens) == 1:
        return _term_matches(tokens[0], fields)

    specific = [token for token in tokens if token not in GENERIC_TERMS]
    if specific:
        return any(_term_matches(token, fields) for token in specific)
    return all(_term_matches(token, fields) for token in tokens)


def _score(fields: dict[str, str], tokens: list[str], query: str) -> int:
    if not _is_relevant(tokens, fields):
        return 0

    token_variants = {token: _variants(token) - {token} for token in tokens}
    query_variants = RELATED_TERMS.get(query, ())

    score = 0
    for field_name, text in fields.items():
        if not text:
            continue
        weight = FIELD_WEIGHTS[field_name]

        if _equals(text, query):
            score += weight * 12
        elif _starts_with(text, query):
            score += weight * 8
        elif _contains(text, query):
            score += weight * 5

        for token in tokens:
            if _contains(text, token):
                score += weight * 2
            elif any(
                _contains(text, variant) for variant in token_variants[token]
            ):
                score += weight
            elif _fuzzy_match_text(text, token):
                score += max(1, weight // 2)

        for variant in query_variants:
            if _contains(text, variant):
                score += weight

    if all(_term_matches(token, fields) for token in tokens):
        score += 10

    return score


def search_facilities(queryset, query: str) -> list[Facility]:
    """Return relevant facilities ordered by relevance and then name."""

    normalized_query = normalize_text(query)
    facilities = list(queryset)
    if not normalized_query:
        return facilities

    tokens = normalized_query.split()
    scored: list[tuple[int, str, Facility]] = []
    for facility in facilities:
        fields = _normalized_fields(facility)
        score = _score(fields, tokens, normalized_query)
        if score > 0:
            scored.append((score, facility.name, facility))

    scored.sort(key=lambda item: (-item[0], item[1]))
    return [facility for _, _, facility in scored]
