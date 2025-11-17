from app.services import showcases


def test_project_cards_have_required_fields(app):
    with app.test_request_context():
        cards = showcases.get_project_cards()
        assert cards, 'expected showcase cards'
        card = cards[0]
        assert {'name', 'summary', 'slug'}.issubset(card.keys())


def test_projects_graph_structure(app):
    with app.test_request_context():
        graph = showcases.get_projects_graph()
        assert graph.get('@context') == 'https://schema.org'
        assert '@graph' in graph
        assert any(node.get('@type') == 'ItemList' for node in graph['@graph'])


def test_events_schema_list(app):
    with app.test_request_context():
        events = showcases.get_events_schema()
        assert isinstance(events, list)
        assert events[0]['@type'] in {'Event', 'SportsEvent', 'TouristTrip'}


def test_itinerary_fetch(app):
    with app.test_request_context():
        data = showcases.get_showcase_itinerary('wakesurf_safari')
        assert data['showcase_id'] == 'wakesurf_safari'
        assert isinstance(data['itinerary'], list)
