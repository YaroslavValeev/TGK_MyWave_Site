def save_user(user_data: dict) -> bool:
    """Minimal shim used by tests to simulate user persistence."""
    return True


def create_user(user_data: dict) -> dict:
    """Create a user record using the persistence shim.

    Returns a dict with a success flag for compatibility with tests.
    """
    ok = save_user(user_data)
    return {"success": bool(ok)}
