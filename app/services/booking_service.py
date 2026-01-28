def create_booking(data: dict):
    # minimal stub used by unit tests
    if not isinstance(data, dict):
        return {"success": False, "error": "invalid data"}
    # pretend we saved booking
    return {"success": True, "id": 1}


def save_to_db(booking):
    # placeholder for mocking
    return True
