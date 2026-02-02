from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def register_core_tools(gateway) -> None:
    """Core tools that are always safe to register (currently none)."""
    return


def register_booking_tools(gateway) -> None:
    """Booking tools are registered elsewhere in the app/services; keep stub for future wiring."""
    return


def register_safari_tools(gateway) -> None:
    """
    Optional: register Safari tools if the implementation exists.
    This file intentionally avoids hard imports so the site can run without these modules.
    """
    try:
        from app.services.safari_booking_service import (
            get_routes,
            get_available_packages,
            create_booking as safari_create_booking,
        )
    except Exception:
        logger.info("[AI tools] safari tools module not present; skipping")
        return

    gateway.register_tool(
        "safari_get_routes",
        lambda payload: get_routes(
            city=payload.get("city"),
            date_from=payload.get("date_from"),
            date_to=payload.get("date_to"),
            level=payload.get("level"),
        ),
    )

    gateway.register_tool(
        "safari_get_packages",
        lambda payload: get_available_packages(
            route_id=payload.get("route_id"),
            group_type=payload.get("group_type"),
        ),
    )

    gateway.register_tool(
        "safari_create_booking", lambda payload: safari_create_booking(payload)
    )


def register_challenge_tools(gateway) -> None:
    """Optional: register Challenge tools if the implementation exists."""
    try:
        from app.services.challenge_service import (
            get_rules,
            get_stage_deadlines,
            get_participant_info,
            get_score,
            submit_score,
            get_results,
        )
    except Exception:
        logger.info("[AI tools] challenge tools module not present; skipping")
        return

    gateway.register_tool(
        "challenge_get_rules", lambda p: get_rules(criteria=p.get("criteria"))
    )
    gateway.register_tool(
        "challenge_get_stage_deadlines",
        lambda p: get_stage_deadlines(stage=p.get("stage")),
    )
    gateway.register_tool(
        "challenge_get_participant_info",
        lambda p: get_participant_info(participant_id=p.get("participant_id")),
    )
    gateway.register_tool(
        "challenge_get_score",
        lambda p: get_score(participant_id=p.get("participant_id")),
    )
    gateway.register_tool(
        "challenge_submit_score",
        lambda p: submit_score(
            judge_id=p.get("judge_id"), participant_id=p.get("participant_id")
        ),
    )
    gateway.register_tool(
        "challenge_get_results", lambda p: get_results(stage=p.get("stage"))
    )


def register_sponsor_tools(gateway) -> None:
    """Optional: sponsor KPI tool (skeleton)."""
    try:
        from app.services.sponsor_analytics import get_sponsor_kpi
    except Exception:
        logger.info("[AI tools] sponsor analytics module not present; skipping")
        return

    gateway.register_tool(
        "sponsor_get_kpi",
        lambda p: get_sponsor_kpi(project=p.get("project") or "safari"),
    )


def register_all_tools(gateway) -> None:
    register_core_tools(gateway)
    register_booking_tools(gateway)
    register_safari_tools(gateway)
    register_challenge_tools(gateway)
    register_sponsor_tools(gateway)
