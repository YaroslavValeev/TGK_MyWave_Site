import re
import json


def test_events_jsonld_present_and_valid(client):
    resp = client.get('/events')
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)

    m = re.search(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html, re.S)
    assert m, "JSON-LD script tag not found on /events"

    js = m.group(1).strip()
    # Basic JSON parsing
    data = json.loads(js)
    assert isinstance(data, list) and len(data) >= 1

    ev = data[0]
    assert ev.get("@type") in {"Event", "SportsEvent"}
    if ev.get("@context"):
        assert ev.get("@context") == "https://schema.org"
    # Required-ish fields for our acceptance: name, startDate, location
    for k in ('name', 'startDate', 'location'):
        assert k in ev, f'Missing {k} in event schema'

    # Additional structural checks
    # startDate should look like an ISO date or datetime (basic check)
    import re as _re
    iso_re = _re.compile(r"^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}(:\d{2})?(Z|[+-]\d{2}:\d{2})?)?$")
    assert iso_re.match(ev.get('startDate', '')) , f"startDate is not ISO-like: {ev.get('startDate')!r}"

    # location must contain name and address
    loc = ev.get('location')
    assert isinstance(loc, dict)
    assert loc.get('name'), 'location.name missing'
    assert loc.get('address'), 'location.address missing'

    # image optional for YAML SportsEvent showcase schema
    imgs = ev.get("image")
    if imgs is not None:
        assert isinstance(imgs, list) and len(imgs) >= 1
        assert isinstance(imgs[0], str) and imgs[0].strip() != ""

    mode = ev.get("eventAttendanceMode")
    if mode:
        valid_modes = {
            "https://schema.org/OnlineEventAttendanceMode",
            "https://schema.org/OfflineEventAttendanceMode",
            "https://schema.org/MixedEventAttendanceMode",
        }
        assert mode in valid_modes, f"Unexpected eventAttendanceMode: {mode}"

    # url should be present and look like a path or absolute URL
    url = ev.get('url')
    assert url and isinstance(url, str)
    assert url.startswith('/') or url.startswith('http'), 'url looks invalid'
