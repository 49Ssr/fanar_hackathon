# Location Resolver Documentation

## 1. Module Goal

Location Resolver converts a bare place name from `agent_inputs["location"]`
into a structured location envelope for the responder, SQL generator, or
retrieval tools.

It does not:

- classify user intent
- generate SQL
- answer the user directly
- manage database records

It only handles:

The supervisor is responsible for routing and extraction. This agent expects an
already-isolated location string such as `"Doha"`, `"QCRI"`, or
`"Qatar National Library"`.

The public agent response uses the shared envelope:

```json
{
  "status": "ok",
  "data": {
    "location": "Qatar Computing Research Institute",
    "lat": 25.3175345,
    "lng": 51.436233
  }
}
```

When the place cannot be resolved, the envelope returns `status: "error"` and
an explanatory `error` string. The low-level resolver still records
`resolver_status` values such as `resolved`, `ambiguous`, and `unresolved`
inside `data` for diagnostics.

## 2. Data Source

The current version uses an online map geocoding API.

Default provider:

```text
OpenStreetMap Nominatim API
https://nominatim.openstreetmap.org/search
```

This means latitude and longitude are resolved from online geocoding results, not from locally hard-coded coordinates.

Official documentation:

- Nominatim Search API: https://nominatim.org/release-docs/latest/api/Search/
- Nominatim Usage Policy: https://operations.osmfoundation.org/policies/nominatim/

Nominatim uses OpenStreetMap data, so returned results should preserve attribution:

```text
© OpenStreetMap contributors
```

## 3. Local Alias File

The resolver still keeps a local alias file:

```text
dataset/location_aliases.json
```

This file does not store coordinates. It stores:

- canonical names
- full geocoding queries
- common aliases and abbreviations
- Arabic aliases
- default radius hints

Example:

```json
{
  "canonical_name": "Qatar Computing Research Institute",
  "query": "Qatar Computing Research Institute, Education City, Al Rayyan, Qatar",
  "fallback_query": "Education City, Al Rayyan, Qatar",
  "aliases": [
    "QCRI",
    "Qatar Computing Research Institute",
    "معهد قطر لبحوث الحوسبة"
  ],
  "place_type_hint": "organization",
  "default_radius_m": 300
}
```

The alias file is needed because abbreviations such as `QCRI`, `QNL`, `HIA`,
and `QU` may not be understood directly by the geocoding API. The resolver
first expands them into a more precise query, then calls the online API.

## 4. Resolution Flow

Example input:

```text
QCRI
```

Flow:

```text
agent_inputs["location"]
  ↓
Normalize text
  ↓
Match local alias
  ↓
QCRI -> Education City, Al Rayyan, Qatar
  ↓
Call Nominatim online API
  ↓
Return uniform agent envelope
```

Example output:

```json
{
  "status": "ok",
  "data": {
    "location": "Qatar Computing Research Institute",
    "query": "Education City, Al Rayyan, Qatar",
    "resolver_status": "resolved",
    "normalized_name": "Qatar Computing Research Institute",
    "display_name": "Education City, Al Rayyan, Qatar",
    "lat": 25.3175345,
    "lng": 51.436233,
    "confidence": 0.883,
    "place_type": "organization",
    "city": "Al Rayyan",
    "country": "QA",
    "radius_m": 300,
    "matched_alias": "QCRI",
    "source": "OpenStreetMap Nominatim",
    "source_attribution": "© OpenStreetMap contributors"
  }
}
```

## 5. API Usage Notes

Nominatim's public API is intended for light use, not large-scale production geocoding.

Important rules:

- send a clear User-Agent
- avoid high-frequency requests
- keep public endpoint usage around one request per second
- preserve OpenStreetMap attribution
- respect the OpenStreetMap ODbL license

The code includes a default User-Agent:

```python
DEFAULT_USER_AGENT = (
    "fanar-subagents-location-resolver/0.1 "
    "(QCRI ALT Team; https://github.com/llm-lab-org/fanar-agents)"
)
```

It can be overridden:

```bash
LOCATION_RESOLVER_USER_AGENT="my-app/0.1 (contact@example.com)" \
python location_resolver_agent.py "Doha"
```

## 6. Local Tests

Test file:

```text
test_location_resolver_agent.py
```

Package layout:

```text
location_resolver_agent/
├── __init__.py
├── location_resolver_agent.py
├── prompt.py
├── schema.py
└── test_location_resolver_agent.py
```

Run from the repository root:

```bash
cd fanar-agents
python agents/location_resolver_agent/test_location_resolver_agent.py
```

Expected result:

```text
PASS test_resolves_doha
PASS test_resolves_arabic_doha
PASS test_resolves_qcri_alias
PASS test_prefers_specific_alias_over_city_context
PASS test_prefers_qatar_university_over_doha_context
PASS test_resolves_education_city
PASS test_resolves_hamad_airport_alias
PASS test_resolves_qatar_national_library_alias
PASS test_unknown_place_is_unresolved
PASS test_agent_envelope_ok
PASS test_agent_envelope_error
PASS test_agent_class_interface
PASS test_module_run_returns_dict_envelope
PASS test_resolve_multiple_mentions

14/14 tests passed.
```

The unit tests use a fake provider so the regular test suite is deterministic and does not repeatedly call the public Nominatim API.

## 7. Live Online Test

A light live test was also run against Nominatim:

```json
[
  {
    "input": "Doha",
    "status": "resolved",
    "provider": "nominatim",
    "query": "Doha, Qatar",
    "name": "Doha, Qatar",
    "display_name": "Doha, Qatar",
    "lat": 25.3108807,
    "lng": 51.5081812,
    "source": "OpenStreetMap Nominatim",
    "matched_alias": "Doha"
  },
  {
    "input": "Education City",
    "status": "resolved",
    "provider": "nominatim",
    "query": "Education City, Al Rayyan, Qatar",
    "name": "Education City",
    "display_name": "Education City, Al Rayyan, Qatar",
    "lat": 25.3175345,
    "lng": 51.436233,
    "source": "OpenStreetMap Nominatim",
    "matched_alias": "Education City"
  },
  {
    "input": "QCRI",
    "status": "resolved",
    "provider": "nominatim",
    "query": "Education City, Al Rayyan, Qatar",
    "name": "Qatar Computing Research Institute",
    "display_name": "Education City, Al Rayyan, Qatar",
    "lat": 25.3175345,
    "lng": 51.436233,
    "source": "OpenStreetMap Nominatim",
    "matched_alias": "QCRI"
  }
]
```

## 8. Supported Aliases

The current alias file supports:

- Doha
- QCRI / Qatar Computing Research Institute
- Education City
- Qatar University / QU
- Qatar National Library / QNL
- Hamad International Airport / Hamad Airport / HIA
- Lusail
- Al Wakrah / Al Wakra
- Msheireb
- City Center Doha / City Centre

To add more places, update `dataset/location_aliases.json`. Coordinates should still come from the online geocoding provider.

## 9. Output Fields

| Field | Meaning |
|---|---|
| `status` | Agent envelope status: `ok` or `error` |
| `data` | Free-form object consumed by the responder when `status == "ok"` |
| `error` | Error message used when `status == "error"` |
| `resolver_status` | Low-level resolver status: `resolved`, `ambiguous`, or `unresolved` |
| `query` | query sent to the online API |
| `normalized_name` | canonical name used by the system |
| `display_name` | name returned by the map API |
| `lat` / `lng` | coordinates returned by the online API |
| `confidence` | resolver confidence score |
| `place_type` | location type, such as city, district, or airport |
| `radius_m` | default search radius hint |
| `matched_alias` | alias matched before geocoding |
| `source` | data source |
| `source_attribution` | map data attribution |

## 10. Future Improvements

Possible next steps:

- add caching to avoid repeated API calls
- add Mapbox or Google Maps provider support
- expose ambiguous candidates to the supervisor agent
- support reverse geocoding
- add a shared provider interface for switching services
- add rate limiting for batch requests
