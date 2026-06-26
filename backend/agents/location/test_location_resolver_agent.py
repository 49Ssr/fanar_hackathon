"""Basic checks for location_resolver_agent.py.

Run:
    python test_location_resolver_agent.py

These tests use a fake provider so the regular test suite is deterministic and
does not hit the public Nominatim service. Use the CLI for live checks.
"""

from location_resolver_agent import (
    LocationResolverAgent,
    resolve_location,
    resolve_location_for_agent,
    resolve_locations,
    run as run_location_agent,
)


class FakeProvider:
    name = "fake-nominatim"

    DATA = {
        "Doha, Qatar": [
            {
                "osm_type": "relation",
                "osm_id": 421316,
                "display_name": "Doha, Qatar",
                "lat": "25.2854",
                "lon": "51.5310",
                "importance": 0.82,
                "type": "city",
                "category": "boundary",
                "address": {"city": "Doha", "country_code": "qa"},
            }
        ],
        "Qatar Computing Research Institute, Education City, Al Rayyan, Qatar": [],
        "Education City, Al Rayyan, Qatar": [
            {
                "osm_type": "node",
                "osm_id": 1747528246,
                "display_name": "Education City, Al Rayyan, Qatar",
                "lat": "25.3175345",
                "lon": "51.436233",
                "importance": 0.7,
                "type": "locality",
                "category": "place",
                "address": {"city": "Al Rayyan", "country_code": "qa"},
            }
        ],
        "Hamad International Airport, Doha, Qatar": [
            {
                "osm_type": "way",
                "osm_id": 123,
                "display_name": "Hamad International Airport, Doha, Qatar",
                "lat": "25.2731",
                "lon": "51.6080",
                "importance": 0.79,
                "type": "aerodrome",
                "category": "aeroway",
                "address": {"city": "Doha", "country_code": "qa"},
            }
        ],
        "Qatar University, Doha, Qatar": [
            {
                "osm_type": "way",
                "osm_id": 234,
                "display_name": "Qatar University, Doha, Qatar",
                "lat": "25.3749",
                "lon": "51.4922",
                "importance": 0.74,
                "type": "university",
                "category": "amenity",
                "address": {"city": "Doha", "country_code": "qa"},
            }
        ],
        "Qatar National Library, Education City, Al Rayyan, Qatar": [
            {
                "osm_type": "way",
                "osm_id": 345,
                "display_name": "Qatar National Library, Education City, Al Rayyan, Qatar",
                "lat": "25.3167",
                "lon": "51.4413",
                "importance": 0.71,
                "type": "library",
                "category": "amenity",
                "address": {"city": "Al Rayyan", "country_code": "qa"},
            }
        ],
        "Msheireb Downtown Doha, Qatar": [
            {
                "osm_type": "node",
                "osm_id": 456,
                "display_name": "Msheireb Downtown Doha, Qatar",
                "lat": "25.2867",
                "lon": "51.5265",
                "importance": 0.68,
                "type": "neighbourhood",
                "category": "place",
                "address": {"city": "Doha", "country_code": "qa"},
            }
        ],
    }

    def search(self, query, *, limit=5):
        return self.DATA.get(query, [])[:limit]


PROVIDER = FakeProvider()


def _first_location(text):
    result = resolve_location(text, provider=PROVIDER)
    assert result["status"] == "resolved", result
    return result["locations"][0]


def test_resolves_doha():
    location = _first_location("Doha")
    assert location["source"] == "OpenStreetMap Nominatim"
    assert location["lat"] is not None
    assert location["lng"] is not None


def test_resolves_arabic_doha():
    location = _first_location("الدوحة")
    assert location["normalized_name"] == "Doha, Qatar"


def test_resolves_qcri_alias():
    location = _first_location("QCRI")
    assert location["query"] == "Education City, Al Rayyan, Qatar"
    assert location["normalized_name"] == "Qatar Computing Research Institute"


def test_prefers_specific_alias_over_city_context():
    location = _first_location("QCRI, Doha")
    assert location["query"] == "Education City, Al Rayyan, Qatar"
    assert location["normalized_name"] == "Qatar Computing Research Institute"


def test_prefers_qatar_university_over_doha_context():
    location = _first_location("Qatar University, Doha")
    assert location["query"] == "Qatar University, Doha, Qatar"
    assert location["normalized_name"] == "Qatar University"


def test_resolves_education_city():
    location = _first_location("Education City")
    assert location["normalized_name"] == "Education City"


def test_resolves_hamad_airport_alias():
    location = _first_location("Hamad Airport")
    assert location["normalized_name"] == "Hamad International Airport"


def test_resolves_qatar_national_library_alias():
    location = _first_location("QNL")
    assert location["query"] == "Qatar National Library, Education City, Al Rayyan, Qatar"
    assert location["normalized_name"] == "Qatar National Library"


def test_unknown_place_is_unresolved():
    result = resolve_location("Unknown Place XYZ", provider=PROVIDER)
    assert result["status"] == "unresolved"
    assert result["locations"] == []


def test_agent_envelope_ok():
    response = resolve_location_for_agent("QNL", provider=PROVIDER)
    assert response.status == "ok"
    assert response.data["location"] == "Qatar National Library"
    assert response.data["lat"] == 25.3167


def test_agent_envelope_error():
    response = resolve_location_for_agent("Unknown Place XYZ", provider=PROVIDER)
    assert response.status == "error"
    assert response.error == "no confident online geocoding match"


def test_agent_class_interface():
    agent = LocationResolverAgent("Fanar", "https://api.fanar.qa/v1", "test-key")
    response = agent.run("Doha", context={"provider": PROVIDER})
    assert response.status == "ok"
    assert response.data["location"] == "Doha, Qatar"
    assert agent.system_prompt
    assert agent.self_healing_prompt


def test_module_run_returns_dict_envelope():
    response = run_location_agent("Doha", context={"provider": PROVIDER})
    assert response["status"] == "ok"
    assert response["data"]["location"] == "Doha, Qatar"


def test_resolve_multiple_mentions():
    result = resolve_locations(["QCRI", "Msheireb"], provider=PROVIDER)
    assert result["status"] == "resolved"
    assert [item["normalized_name"] for item in result["locations"]] == [
        "Qatar Computing Research Institute",
        "Msheireb Downtown Doha",
    ]


def main():
    tests = [
        test_resolves_doha,
        test_resolves_arabic_doha,
        test_resolves_qcri_alias,
        test_prefers_specific_alias_over_city_context,
        test_prefers_qatar_university_over_doha_context,
        test_resolves_education_city,
        test_resolves_hamad_airport_alias,
        test_resolves_qatar_national_library_alias,
        test_unknown_place_is_unresolved,
        test_agent_envelope_ok,
        test_agent_envelope_error,
        test_agent_class_interface,
        test_module_run_returns_dict_envelope,
        test_resolve_multiple_mentions,
    ]

    for test in tests:
        test()
        print(f"PASS {test.__name__}")

    print(f"\n{len(tests)}/{len(tests)} tests passed.")


if __name__ == "__main__":
    main()
