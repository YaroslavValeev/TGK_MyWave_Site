from app.services import showcases


def test_project_cards_have_required_fields(app):
    with app.test_request_context():
        cards = showcases.get_project_cards()
        assert cards, 'expected showcase cards'
        card = cards[0]
        assert {'name', 'summary', 'slug'}.issubset(card.keys())


def test_project_cards_have_valid_cover(app):
    """Верификация: у каждой карточки есть обложка."""
    with app.test_request_context():
        cards = showcases.get_project_cards()
        for card in cards:
            cover = card.get('cover')
            assert cover, f"карточка {card.get('name')} без обложки"


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


def test_checklist_card_prefers_check1_cover(app):
    with app.test_request_context():
        cards = showcases.get_project_cards()
        checklist = next(c for c in cards if c.get('id') == 'checklist')
        cover = (checklist.get('cover') or '').rsplit('/', 1)[-1]
        assert cover.lower() == 'check1.png', checklist.get('cover')
