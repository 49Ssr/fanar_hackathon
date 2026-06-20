# LocationResolver Agent

Bilingual Arabic/English location resolver for the Fanar national AI platform.
Developed at QCRI (Qatar Computing Research Institute), Summer 2026.
Developer: Chenyu Qiu

## What it does
Takes a bare place name from `agent_inputs["location"]` and returns the uniform
agent envelope:

- `status: "ok"` with useful location fields in free-form `data`
- `status: "error"` when the place is unresolved or ambiguous

The `data` object currently contains:
- Normalized English and Arabic place names
- Alias and abbreviation expansion (QCRI, HIA, QU, etc.)
- Online geocoding through OpenStreetMap Nominatim
- Latitude, longitude, confidence, source, and attribution
- low-level `resolver_status` for diagnostics

## Taxonomy

| Input type | Examples |
|---|---|
| City | Doha, Lusail, Al Wakrah |
| District | Education City, Msheireb |
| Organization | QCRI, Qatar University, Qatar National Library |
| Transport hub | Hamad Airport, HIA |
| Arabic alias | الدوحة, المدينة التعليمية, مكتبة قطر الوطنية |

## How to run
```bash
python location_resolver_agent.py "QCRI"
python test_location_resolver_agent.py
```

## Agent interface
```python
from location_resolver_agent import LocationResolverAgent

agent = LocationResolverAgent(model_name, base_url, api_key)
response = agent.run("Qatar National Library")
```

## Example

**English input:**
```
"QCRI"
```
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

**Arabic input:**
```
"الدوحة"
```
```json
{
  "status": "ok",
  "data": {
    "location": "Doha, Qatar",
    "query": "Doha, Qatar",
    "resolver_status": "resolved",
    "normalized_name": "Doha, Qatar",
    "lat": 25.3108807,
    "lng": 51.5081812,
    "place_type": "city",
    "country": "QA",
    "matched_alias": "الدوحة",
    "source": "OpenStreetMap Nominatim"
  }
}
```

## Folder structure
```
location_resolver_agent/
├── __init__.py                        ← package exports
├── README.md                         ← you are here
├── local_test_server.py               ← optional browser test UI
├── location_resolver_agent.py         ← entry point
├── prompt.py                          ← system + self-healing prompts
├── requirements.txt                   ← pydantic/openai dependencies
├── schema.py                          ← pydantic response envelope
├── test_location_resolver_agent.py    ← deterministic tests with a fake provider
├── LOCATION_RESOLVER_DOCUMENTATION.md ← implementation notes and API policy
└── dataset/
    └── location_aliases.json          ← aliases and query hints, no coordinates
```

## Dependencies
- `pydantic` for response validation
- `openai` for constructor compatibility with Fanar-backed agents
- OpenStreetMap Nominatim public API for live geocoding
