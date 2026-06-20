"""
location_resolver_agent.py
--------------------------
Converts English/Arabic Qatar place mentions into structured location objects.

Agent input:
    place_name (str): a bare place name from agent_inputs["location"],
    e.g. "QCRI", "Qatar National Library", "الدوحة"

Agent output:
    {
        "status": "ok" | "error",
        "data": {"location": "...", "lat": 25.0, "lng": 51.0, ...},
        "error": "message when status is error"
    }

The low-level resolve_location() helper still returns
"resolved" | "ambiguous" | "unresolved" for diagnostics.

Coordinates are fetched from an online map geocoding API. The local JSON file
only stores aliases such as QCRI -> "Qatar Computing Research Institute..."
so short user mentions can be expanded before geocoding.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import unicodedata
from pathlib import Path
from typing import Any, Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

try:
    from .schema import LocationAgentResponse
    from .prompt import SELF_HEALING_PROMPT, SYSTEM_PROMPT
except ImportError:  # pragma: no cover - supports direct script execution
    from schema import LocationAgentResponse
    from prompt import SELF_HEALING_PROMPT, SYSTEM_PROMPT


ALIASES_PATH = Path(__file__).resolve().parent / "dataset" / "location_aliases.json"
NOMINATIM_BASE_URL = "https://nominatim.openstreetmap.org/search"
DEFAULT_FANAR_BASE_URL = "https://api.fanar.qa/v1"
DEFAULT_MODEL_NAME = "Fanar"
DEFAULT_USER_AGENT = (
    "fanar-subagents-location-resolver/0.1 "
    "(QCRI ALT Team; https://github.com/llm-lab-org/fanar-agents)"
)
OSM_ATTRIBUTION = "© OpenStreetMap contributors"

ARABIC_DIACRITICS_RE = re.compile(r"[\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06ed]")
PUNCTUATION_RE = re.compile(r"[^\w\s\u0600-\u06ff]", re.UNICODE)
SPACE_RE = re.compile(r"\s+")

LOCATION_WORD_PATTERNS = [
    r"\bclose to\b",
    r"\bnext to\b",
    r"\bnear\b",
    r"\baround\b",
    r"\binside\b",
    r"\bin\b",
    r"\bat\b",
    r"\bfrom\b",
    r"\bto\b",
    r"\bفي\b",
    r"\bقرب\b",
    r"\bحول\b",
    r"\bعند\b",
    r"\bالى\b",
    r"\bبالقرب من\b",
]


def normalize_text(text: str) -> str:
    """Normalize English/Arabic text for matching."""
    text = unicodedata.normalize("NFKC", text or "")
    text = ARABIC_DIACRITICS_RE.sub("", text)
    text = text.replace("\u0640", "")
    text = text.translate(
        str.maketrans(
            {
                "أ": "ا",
                "إ": "ا",
                "آ": "ا",
                "ى": "ي",
                "ة": "ه",
                "ؤ": "و",
                "ئ": "ي",
            }
        )
    )
    text = PUNCTUATION_RE.sub(" ", text.casefold())
    return SPACE_RE.sub(" ", text).strip()


def _query_variants(text: str) -> list[str]:
    normalized = normalize_text(text)
    without_location_words = normalized
    for pattern in LOCATION_WORD_PATTERNS:
        without_location_words = re.sub(pattern, " ", without_location_words)
    variants = [normalized, SPACE_RE.sub(" ", without_location_words).strip()]
    return [value for index, value in enumerate(variants) if value and value not in variants[:index]]


def _load_aliases(aliases_path: str | Path | None = None) -> list[dict[str, Any]]:
    path = Path(aliases_path) if aliases_path else ALIASES_PATH
    with path.open("r", encoding="utf-8") as handle:
        aliases = json.load(handle)

    if not isinstance(aliases, list):
        raise ValueError(f"Location alias dataset must be a list: {path}")
    return aliases


def _search_terms(alias_record: dict[str, Any]) -> list[tuple[str, str]]:
    terms = [alias_record.get("canonical_name", "")]
    terms.extend(alias_record.get("aliases", []))

    normalized_terms = []
    for term in terms:
        normalized = normalize_text(str(term))
        if normalized:
            normalized_terms.append((str(term), normalized))
    return normalized_terms


def _contains_normalized_term(query: str, term: str) -> bool:
    return f" {term} " in f" {query} "


def _alias_specificity(alias_record: dict[str, Any]) -> float:
    try:
        radius = float(alias_record.get("default_radius_m"))
    except (TypeError, ValueError):
        radius = 1_000_000.0
    return -radius


def _find_alias_match(text: str, aliases: list[dict[str, Any]]) -> dict[str, Any] | None:
    variants = _query_variants(text)
    best_match: dict[str, Any] | None = None
    best_rank: tuple[float, int, float, int] | None = None

    for alias_record in aliases:
        for alias, term in _search_terms(alias_record):
            for query in variants:
                if query == term:
                    score = 1.0
                    exact_match = 1
                elif len(term) >= 3 and _contains_normalized_term(query, term):
                    score = 0.95
                    exact_match = 0
                else:
                    continue

                rank = (score, exact_match, _alias_specificity(alias_record), len(term))
                if best_rank is None or rank > best_rank:
                    best_match = {
                        "record": alias_record,
                        "matched_alias": alias,
                        "alias_confidence": score,
                    }
                    best_rank = rank

    return best_match


def _build_fallback_query(text: str, default_country: str) -> str:
    variants = _query_variants(text)
    query = variants[-1] if variants else text
    if default_country and default_country.casefold() not in query.casefold():
        query = f"{query}, {default_country}"
    return query


class NominatimProvider:
    """Minimal Nominatim search API client."""

    name = "nominatim"

    def __init__(
        self,
        *,
        base_url: str | None = None,
        user_agent: str | None = None,
        timeout: float = 10.0,
        country_codes: str = "qa",
    ) -> None:
        self.base_url = base_url or os.getenv("NOMINATIM_BASE_URL", NOMINATIM_BASE_URL)
        self.user_agent = user_agent or os.getenv(
            "LOCATION_RESOLVER_USER_AGENT",
            DEFAULT_USER_AGENT,
        )
        self.timeout = timeout
        self.country_codes = country_codes

    def search(self, query: str, *, limit: int = 5) -> list[dict[str, Any]]:
        params = {
            "q": query,
            "format": "jsonv2",
            "addressdetails": "1",
            "namedetails": "1",
            "dedupe": "1",
            "limit": str(limit),
            "countrycodes": self.country_codes,
            "accept-language": "en",
        }
        url = f"{self.base_url}?{urlencode(params)}"
        request = Request(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": self.user_agent,
            },
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                payload = response.read().decode("utf-8")
        except HTTPError as exc:
            raise RuntimeError(f"Nominatim HTTP error {exc.code}: {exc.reason}") from exc
        except URLError as exc:
            raise RuntimeError(f"Nominatim connection error: {exc.reason}") from exc
        except TimeoutError as exc:
            raise RuntimeError("Nominatim request timed out") from exc

        data = json.loads(payload)
        if not isinstance(data, list):
            raise RuntimeError("Nominatim returned an unexpected response shape")
        return data


def _provider_confidence(result: dict[str, Any], alias_confidence: float) -> float:
    importance = result.get("importance")
    try:
        importance_score = max(0.0, min(float(importance), 1.0))
    except (TypeError, ValueError):
        importance_score = 0.5

    return round(min(0.99, (alias_confidence * 0.82) + (importance_score * 0.17)), 3)


def _candidate_from_provider(
    result: dict[str, Any],
    raw_text: str,
    query: str,
    confidence: float,
    alias_match: dict[str, Any] | None,
) -> dict[str, Any]:
    address = result.get("address") if isinstance(result.get("address"), dict) else {}
    alias_record = alias_match["record"] if alias_match else {}
    matched_alias = alias_match["matched_alias"] if alias_match else None
    canonical_name = alias_record.get("canonical_name") or result.get("display_name")

    return {
        "raw_text": raw_text,
        "query": query,
        "place_id": f"osm_{result.get('osm_type')}_{result.get('osm_id')}",
        "normalized_name": canonical_name,
        "display_name": result.get("display_name"),
        "lat": float(result["lat"]),
        "lng": float(result["lon"]),
        "confidence": confidence,
        "place_type": alias_record.get("place_type_hint") or result.get("type"),
        "city": address.get("city") or address.get("town") or address.get("municipality"),
        "country": address.get("country_code", "qa").upper(),
        "radius_m": alias_record.get("default_radius_m"),
        "matched_alias": matched_alias,
        "source": "OpenStreetMap Nominatim",
        "source_attribution": OSM_ATTRIBUTION,
        "osm_type": result.get("osm_type"),
        "osm_id": result.get("osm_id"),
        "provider_class": result.get("category") or result.get("class"),
        "provider_type": result.get("type"),
    }


def _search_with_fallback(
    provider: NominatimProvider,
    query: str,
    fallback_query: str | None,
    *,
    limit: int,
) -> tuple[str, list[dict[str, Any]]]:
    results = provider.search(query, limit=limit)
    if results or not fallback_query or fallback_query == query:
        return query, results
    return fallback_query, provider.search(fallback_query, limit=limit)


def _same_location_family(first: dict[str, Any], second: dict[str, Any]) -> bool:
    """Treat alternate OSM geometries for the same named place as non-ambiguous."""
    first_name = normalize_text(first.get("normalized_name", ""))
    second_name = normalize_text(second.get("normalized_name", ""))
    first_display = normalize_text(first.get("display_name", ""))
    second_display = normalize_text(second.get("display_name", ""))
    return bool(first_name and first_name == second_name) or bool(
        first_display and first_display == second_display
    )


def resolve_location(
    text: str,
    *,
    aliases_path: str | Path | None = None,
    provider: NominatimProvider | None = None,
    min_confidence: float = 0.55,
    ambiguity_margin: float = 0.05,
    max_candidates: int = 3,
    default_country: str = "Qatar",
) -> dict[str, Any]:
    """
    Resolve one location mention into a structured location object.

    Args:
        text: Place mention or short user phrase.
        aliases_path: Optional path to a JSON alias file.
        provider: Optional online geocoding provider.
        min_confidence: Minimum score needed for resolved status.
        ambiguity_margin: Top-two score distance that counts as ambiguous.
        max_candidates: Number of candidates to return for diagnostics.
        default_country: Country appended to free-form fallback queries.
    """
    raw_text = text or ""
    active_provider = provider or NominatimProvider()
    if not raw_text.strip():
        return {
            "status": "unresolved",
            "raw_text": raw_text,
            "provider": active_provider.name,
            "locations": [],
            "candidates": [],
            "errors": ["empty location text"],
        }

    aliases = _load_aliases(aliases_path)
    alias_match = _find_alias_match(raw_text, aliases)
    if alias_match:
        alias_record = alias_match["record"]
        query = alias_record["query"]
        fallback_query = alias_record.get("fallback_query")
        alias_confidence = alias_match["alias_confidence"]
    else:
        query = _build_fallback_query(raw_text, default_country)
        fallback_query = None
        alias_confidence = 0.72

    try:
        used_query, provider_results = _search_with_fallback(
            active_provider,
            query,
            fallback_query,
            limit=max_candidates,
        )
    except RuntimeError as exc:
        return {
            "status": "unresolved",
            "raw_text": raw_text,
            "provider": active_provider.name,
            "query": query,
            "locations": [],
            "candidates": [],
            "errors": [str(exc)],
        }

    candidates = [
        _candidate_from_provider(
            result,
            raw_text,
            used_query,
            _provider_confidence(result, alias_confidence),
            alias_match,
        )
        for result in provider_results
        if result.get("lat") and result.get("lon")
    ][:max_candidates]

    if not candidates or candidates[0]["confidence"] < min_confidence:
        return {
            "status": "unresolved",
            "raw_text": raw_text,
            "provider": active_provider.name,
            "query": used_query,
            "locations": [],
            "candidates": candidates,
            "errors": ["no confident online geocoding match"],
        }

    top = candidates[0]
    if (
        len(candidates) > 1
        and top["confidence"] - candidates[1]["confidence"] <= ambiguity_margin
        and not _same_location_family(top, candidates[1])
    ):
        return {
            "status": "ambiguous",
            "raw_text": raw_text,
            "provider": active_provider.name,
            "query": used_query,
            "locations": [],
            "candidates": candidates,
            "errors": ["multiple location candidates are similarly likely"],
        }

    return {
        "status": "resolved",
        "raw_text": raw_text,
        "provider": active_provider.name,
        "query": used_query,
        "locations": [top],
        "candidates": [],
        "errors": [],
    }


def resolve_locations(
    location_mentions: Iterable[str],
    *,
    aliases_path: str | Path | None = None,
    provider: NominatimProvider | None = None,
    min_confidence: float = 0.55,
) -> dict[str, Any]:
    """Resolve multiple location mentions and collect their best locations."""
    active_provider = provider or NominatimProvider()
    results = [
        resolve_location(
            mention,
            aliases_path=aliases_path,
            provider=active_provider,
            min_confidence=min_confidence,
        )
        for mention in location_mentions
    ]
    locations = [result["locations"][0] for result in results if result["status"] == "resolved"]
    unresolved = [result for result in results if result["status"] != "resolved"]

    if not results:
        status = "unresolved"
    elif unresolved and locations:
        status = "partial"
    elif unresolved:
        status = "unresolved"
    else:
        status = "resolved"

    return {
        "status": status,
        "provider": active_provider.name,
        "locations": locations,
        "results": results,
        "errors": [error for result in unresolved for error in result["errors"]],
    }


def _location_data(resolver_result: dict[str, Any]) -> dict[str, Any]:
    location = resolver_result["locations"][0]
    keys = [
        "normalized_name",
        "display_name",
        "lat",
        "lng",
        "confidence",
        "place_type",
        "city",
        "country",
        "radius_m",
        "matched_alias",
        "source",
        "source_attribution",
        "osm_type",
        "osm_id",
        "provider_class",
        "provider_type",
    ]
    data = {
        "location": location.get("normalized_name") or location.get("display_name"),
        "query": resolver_result.get("query"),
        "resolver_status": resolver_result.get("status"),
    }
    data.update({key: location.get(key) for key in keys})
    return {key: value for key, value in data.items() if value is not None}


def _agent_response_from_resolver(resolver_result: dict[str, Any]) -> LocationAgentResponse:
    if resolver_result["status"] == "resolved" and resolver_result.get("locations"):
        return LocationAgentResponse(status="ok", data=_location_data(resolver_result))

    errors = resolver_result.get("errors") or [f"location {resolver_result['status']}"]
    data = {
        "resolver_status": resolver_result.get("status"),
        "query": resolver_result.get("query"),
        "candidates": resolver_result.get("candidates", []),
    }
    return LocationAgentResponse(
        status="error",
        data={key: value for key, value in data.items() if value not in (None, [])},
        error="; ".join(errors),
    )


def resolve_location_for_agent(
    place_name: str,
    *,
    context: dict[str, Any] | None = None,
    provider: NominatimProvider | None = None,
) -> LocationAgentResponse:
    """Resolve a bare place name into the uniform agent envelope."""
    context = context or {}
    resolver_result = resolve_location(
        place_name,
        aliases_path=context.get("aliases_path"),
        provider=provider or context.get("provider"),
        min_confidence=context.get("min_confidence", 0.55),
        ambiguity_margin=context.get("ambiguity_margin", 0.05),
        max_candidates=context.get("max_candidates", 3),
        default_country=context.get("default_country", "Qatar"),
    )
    return _agent_response_from_resolver(resolver_result)


def _response_to_dict(response: LocationAgentResponse) -> dict[str, Any]:
    if hasattr(response, "model_dump"):
        return response.model_dump(exclude_none=True)
    return response.dict(exclude_none=True)


class LocationResolverAgent:
    """
    Agent wrapper that matches the constructor/run shape used by routed agents.

    The location contract already provides a bare place name, so this class does
    not call the language model for extraction. The OpenAI client is still kept
    on the instance for interface compatibility with Fanar-backed agents.
    """

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL_NAME,
        base_url: str = DEFAULT_FANAR_BASE_URL,
        api_key: str | None = None,
    ) -> None:
        from openai import OpenAI

        self.model_name = model_name
        self.system_prompt = SYSTEM_PROMPT
        self.self_healing_prompt = SELF_HEALING_PROMPT
        self.client = OpenAI(
            base_url=base_url,
            api_key=api_key or os.getenv("FANAR_API_KEY") or "not-used",
        )

    def run(
        self,
        place_name: str,
        context: dict[str, Any] | None = None,
    ) -> LocationAgentResponse:
        last_error: Exception | None = None
        for _ in range(3):
            try:
                return resolve_location_for_agent(place_name, context=context)
            except Exception as exc:  # validation/configuration errors are rare but recoverable
                last_error = exc

        return LocationAgentResponse(
            status="error",
            data={},
            error=f"Location resolver failed: {last_error}",
        )


def run(place_name: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    """Module-level entry point for supervisors that import agent.run(...)."""
    return _response_to_dict(resolve_location_for_agent(place_name, context=context))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Resolve a Qatar place name via online geocoding.")
    parser.add_argument("text", nargs="+", help="Bare place name, such as Doha or QCRI")
    parser.add_argument("--aliases", default=None, help="Optional path to location_aliases.json")
    parser.add_argument("--user-agent", default=None, help="User-Agent for the Nominatim request")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    provider = NominatimProvider(user_agent=args.user_agent)
    response = resolve_location_for_agent(
        " ".join(args.text),
        context={"aliases_path": args.aliases},
        provider=provider,
    )
    print(json.dumps(_response_to_dict(response), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
