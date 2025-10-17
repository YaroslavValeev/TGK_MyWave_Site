from flask import Blueprint, render_template, request

calculator_bp = Blueprint("calculator", __name__, template_folder="templates")


def _base_price(zone: str, package: str, days: int) -> int:
    central_prices = {
        "Base": {2: 79000, 3: 89000},
        "Pro": {2: 109000, 3: 119000},
        "Elite": {3: 139000},
    }
    zone_surcharge = {
        "Central": 0,
        "Ural": 10000,
        "Siberia": 20000,
        "Far East": 40000,
    }
    if package not in central_prices or days not in central_prices[package]:
        raise ValueError(f"No base price found for package {package} with {days} days")
    base_central = central_prices[package][days]
    surcharge = zone_surcharge.get(zone, 0)
    return base_central + surcharge


def _merch_price(items, participants: int) -> int:
    merch_catalog = {
        "tshirt": 4000,
        "hoodie": 8000,
        "poncho": 10000,
        "cap": 3000,
        "balance_board": 10000,
        "smooth_trainer": 6000,
    }
    total = 0
    for item in items:
        price = merch_catalog.get(item, 0)
        total += price * participants
    return total


@calculator_bp.route("/calculator", methods=["GET", "POST"])
def calculator():
    result = None
    breakdown = None
    if request.method == "POST":
        zone = request.form.get("zone", "Central")
        package = request.form.get("package", "Pro")
        days = int(request.form.get("days", 2))
        participants = int(request.form.get("participants", 1))
        extra_sets = int(request.form.get("extra_sets", 0))
        pilot_training_hours = float(request.form.get("pilot_hours", 0))
        personal_clip = request.form.get("personal_clip") == "on"
        drone_session = request.form.get("drone_session") == "on"
        merch_items = request.form.getlist("merch")

        base = _base_price(zone, package, days)
        base_total = base * participants

        extras_total = 0
        if extra_sets > 0:
            extras_total += extra_sets * 11000 * participants
        if pilot_training_hours > 0:
            extras_total += int(pilot_training_hours * 3500)
        if personal_clip:
            extras_total += 7000 * participants
        if drone_session:
            extras_total += 5000

        merch_total = _merch_price(merch_items, participants)
        total_cost = base_total + extras_total + merch_total

        breakdown = {
            "Базовая стоимость": f"{base_total:,d} ₽",
            "Дополнительные сеты": f"{extra_sets * 11000 * participants:,d} ₽" if extra_sets > 0 else None,
            "Обучение пилотированию": f"{int(pilot_training_hours * 3500):,d} ₽" if pilot_training_hours > 0 else None,
            "Персональный клип": f"{7000 * participants:,d} ₽" if personal_clip else None,
            "Сессия дрона": "5\u00A0000 ₽" if drone_session else None,
            "Мерч": f"{merch_total:,d} ₽" if merch_total > 0 else None,
        }
        result = f"{total_cost:,d} ₽"

    return render_template("calculator.html", result=result, breakdown=breakdown)
