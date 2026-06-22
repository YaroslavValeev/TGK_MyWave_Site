"""PR53.1 evidence — boat summary markup + notification paths."""

def test_boat_slot_summary_markup(client):
    html = client.get("/").get_data(as_text=True)
    assert 'id="boatSlotSummary"' in html
    assert 'id="boatSlotSummaryCount"' in html
    assert 'id="boatSlotSummaryTotal"' in html
    assert 'id="confirmSlotBtn"' in html
