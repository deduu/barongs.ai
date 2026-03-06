from __future__ import annotations

import re

_LEADING_FILLER_PATTERNS = (
    r"^(?:please\s+)?(?:go\s+and\s+)?search(?:\s+for|\s+about)?\s+",
    r"^(?:please\s+)?look\s+up\s+",
    r"^(?:please\s+)?research\s+",
    r"^(?:please\s+)?find\s+information\s+about\s+",
    r"^(?:please\s+)?tell\s+me\s+about\s+",
    r"^(?:please\s+)?what\s+can\s+you\s+find\s+about\s+",
)
_QUERY_STOPWORDS = {
    "a",
    "about",
    "an",
    "and",
    "any",
    "concern",
    "concerns",
    "for",
    "go",
    "how",
    "i",
    "information",
    "into",
    "is",
    "me",
    "of",
    "on",
    "please",
    "regarding",
    "research",
    "search",
    "tell",
    "the",
    "to",
    "up",
    "what",
}
_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._+-]*")
_HIGH_SIGNAL_FOCUS_TERMS = ("safety", "risk", "hazard", "security", "cybersecurity")
_URL_PATTERN = re.compile(r"https?://[^\s<>\"'\)\]]+", re.IGNORECASE)


def strip_urls(query: str) -> str:
    """Return the query with URLs removed."""
    return _URL_PATTERN.sub("", query).strip()


def normalize_research_query(query: str) -> str:
    """Strip filler language from conversational prompts before search."""
    cleaned = strip_urls(query or "")
    cleaned = cleaned.strip()
    for pattern in _LEADING_FILLER_PATTERNS:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = cleaned.strip(" ,:;.-")
    return cleaned or (query or "").strip()


def _entity_tokens(entity_name: str) -> list[str]:
    return [token.lower() for token in _TOKEN_PATTERN.findall(entity_name)]


def _topic_terms(query: str, entity_name: str) -> list[str]:
    entity_tokens = set(_entity_tokens(entity_name))
    terms: list[str] = []
    seen: set[str] = set()
    for token in _TOKEN_PATTERN.findall(query):
        lowered = token.lower()
        if lowered in seen or lowered in _QUERY_STOPWORDS or lowered in entity_tokens:
            continue
        if len(lowered) < 3:
            continue
        seen.add(lowered)
        terms.append(token)
    return terms


def build_query_variants(raw_query: str, entity_name: str = "", *, limit: int = 4) -> list[str]:
    """Build a few tight query variants to improve recall on academic/web search."""
    normalized = normalize_research_query(raw_query)
    clean_entity = normalize_research_query(entity_name)
    topic_terms = _topic_terms(normalized, clean_entity)

    variants: list[str] = []
    seen: set[str] = set()

    def add(candidate: str) -> None:
        compact = re.sub(r"\s+", " ", candidate).strip()
        key = compact.lower()
        if not compact or key in seen:
            return
        seen.add(key)
        variants.append(compact)

    add(normalized)

    if clean_entity:
        quoted_entity = f"\"{clean_entity}\""
        topic_phrase = " ".join(topic_terms[:4])
        if topic_phrase:
            add(f"{quoted_entity} {topic_phrase}")
        add(clean_entity)
        for focus_term in _HIGH_SIGNAL_FOCUS_TERMS:
            if focus_term in {term.lower() for term in topic_terms}:
                add(f"{quoted_entity} {focus_term}")

    return variants[:limit]


def select_primary_query(raw_query: str, entity_name: str = "") -> str:
    """Pick the best single query string for tools that only support one search."""
    variants = build_query_variants(raw_query, entity_name, limit=4)
    if len(variants) > 1:
        return variants[1]
    if variants:
        return variants[0]
    return normalize_research_query(raw_query)


def source_mentions_entity(entity_name: str, *texts: str) -> bool:
    """Heuristic exact-name check used to avoid over-filtering obvious matches."""
    clean_entity = normalize_research_query(entity_name).lower()
    if not clean_entity:
        return False
    entity_tokens = _entity_tokens(clean_entity)
    combined = " ".join(text for text in texts if text).lower()
    if clean_entity in combined:
        return True
    return bool(entity_tokens) and all(token in combined for token in entity_tokens)


def source_mentions_query_focus(query: str, entity_name: str, *texts: str) -> bool:
    """Require overlap with the non-entity part of the user's query before retrying."""
    focus_terms = [term.lower() for term in _topic_terms(normalize_research_query(query), entity_name)]
    if not focus_terms:
        return False
    combined = " ".join(text for text in texts if text).lower()
    return any(term in combined for term in focus_terms)


def source_supports_entity_description(entity_description: str, *texts: str) -> bool:
    """Use non-generic description tokens as a secondary retry gate."""
    descriptor_terms = [
        token.lower()
        for token in _TOKEN_PATTERN.findall(entity_description)
        if token.lower() not in _QUERY_STOPWORDS and len(token) >= 4
    ]
    if not descriptor_terms:
        return False
    combined = " ".join(text for text in texts if text).lower()
    return any(term in combined for term in descriptor_terms)
