"""Simple CRM integration layer with adapters for AmoCRM and Bitrix24.

This module provides a thin facade `create_lead` which will try to send
lead data to a configured CRM provider. If no provider is configured or
the provider call fails, it will fall back to writing the lead to Google
Sheets via `app.services.sheets_writer.save_client_to_sheets` so data is
not lost during development or in test environments.

The implementations below are intentionally minimal and stubbed. They
should be replaced with full adapters when real credentials and API
clients are available.
"""
from typing import Optional, Dict
import logging

from flask import current_app

from app.services import sheets_writer

logger = logging.getLogger(__name__)


class BaseCRMAdapter:
    def create_lead(self, data: Dict) -> Dict:
        """Create lead in CRM. Should return a dict with at least an "id" key.

        Raise exceptions on failure to allow callers to handle retries.
        """
        raise NotImplementedError()


class AmoCRMAdapter(BaseCRMAdapter):
    def __init__(self, config: Dict):
        # config may contain token, domain, etc. For now store it for future use
        self.config = config

    def create_lead(self, data: Dict) -> Dict:
        # Minimal stub: log and return a fake id
        logger.info("[AmoCRM] create_lead stub called: %s", data)
        return {"id": "amo_12345", "status": "stub"}


class BitrixAdapter(BaseCRMAdapter):
    def __init__(self, config: Dict):
        self.config = config

    def create_lead(self, data: Dict) -> Dict:
        logger.info("[Bitrix] create_lead stub called: %s", data)
        return {"id": "bx_67890", "status": "stub"}


def _get_adapter() -> Optional[BaseCRMAdapter]:
    provider = current_app.config.get("CRM_PROVIDER")
    cfg = current_app.config.get("CRM_CONFIG") or {}
    if not provider:
        return None
    if provider == "amo":
        return AmoCRMAdapter(cfg)
    if provider == "bitrix":
        return BitrixAdapter(cfg)
    return None


def create_lead(data: Dict) -> Dict:
    """Create a lead in the configured CRM or fall back to Google Sheets.

    Input shape: at least `name` or `phone`/`email` should be provided.
    Returns: the CRM response dict or a fallback dict indicating sheets write.
    """
    adapter = None
    try:
        adapter = _get_adapter()
    except Exception as e:
        logger.exception("Error while obtaining CRM adapter: %s", e)

    if adapter:
        try:
            return adapter.create_lead(data)
        except Exception:
            logger.exception("CRM adapter failed to create lead, falling back to sheets")

    # fallback: save to Google Sheets (this function is safe in GOOGLE_MOCK/test env)
    try:
        sheets_writer.save_client_to_sheets(
            name=data.get("name"),
            phone=data.get("phone"),
            email=data.get("email"),
            telegram_user_id=data.get("telegram_user_id"),
            source=data.get("source"),
            status=data.get("status", "new")
        )
        return {"id": None, "status": "saved_to_sheets"}
    except Exception:
        logger.exception("Failed to save lead to sheets as a last resort")
        return {"id": None, "status": "failed"}
