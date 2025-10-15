from typing import Dict


def save_to_db(data: Dict) -> bool:
    """Minimal shim for tests: pretend to save booking to DB."""
    # Real implementation lives in booking_orchestrator / app.routes.booking
    return True


def create_booking(data: Dict) -> Dict:
    """Create booking shim used by unit tests."""
    ok = save_to_db(data)
    return {"success": bool(ok), "data": data}
