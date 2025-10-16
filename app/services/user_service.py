def create_user(data: dict):
    if not isinstance(data, dict):
        return {"success": False}
    # attempt to save user (save_user may be patched in tests)
    ok = save_user(data)
    return {"success": bool(ok), "id": 1 if ok else None}


def save_user(user):
    return True
