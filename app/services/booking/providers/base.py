"""Booking provider interface (YCLIENTS / internal)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class ProviderSlot:
    start_time: str
    duration_minutes: int
    available: bool = True


@dataclass
class ProviderBookingResult:
    external_id: str
    status: str
    raw: Dict[str, Any]


class BookingProvider(ABC):
    provider_name: str

    @abstractmethod
    def is_enabled(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def fetch_available_slots(self, date_str: str) -> List[ProviderSlot]:
        raise NotImplementedError

    @abstractmethod
    def create_booking(
        self,
        *,
        date_str: str,
        time_str: str,
        client_name: str,
        client_phone: str,
        service_id: Optional[str] = None,
    ) -> ProviderBookingResult:
        raise NotImplementedError

    @abstractmethod
    def cancel_booking(self, external_id: str) -> bool:
        raise NotImplementedError
