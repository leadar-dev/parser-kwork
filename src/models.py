from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TypedDict


class WantUserData(TypedDict):
    wants_count: str
    wants_hired_percent: str


class WantUser(TypedDict):
    USERID: int
    username: str
    data: WantUserData


class RawWant(TypedDict):
    id: int
    name: str
    description: str
    priceLimit: str
    possiblePriceLimit: int
    category_id: str
    max_days: str
    status: str
    kwork_count: int
    date_create: str
    date_expire: str
    views_dirty: str
    user: WantUser


@dataclass
class KworkWant:
    want_id: int
    name: str
    description: str
    price_limit: float
    possible_price_limit: float | None
    category_id: int
    max_days: int
    status: str
    kwork_count: int
    views: int
    hired_percent: float | None
    url: str
    date_create: datetime
    date_expire: datetime | None


@dataclass
class KworkWantDetail(KworkWant):
    tags: list[str]


class KworkWantPayload(TypedDict):
    source: str
    want_id: int
    name: str
    description: str
    price_limit: float
    possible_price_limit: float | None
    category_id: int
    max_days: int
    status: str
    kwork_count: int
    views: int
    hired_percent: float | None
    url: str
    date_create: str
    date_expire: str | None


class KworkCategory(TypedDict):
    external_id: int
    name: str
    parent_external_id: int | None


class KworkCategoriesPayload(TypedDict):
    source: str
    categories: list[KworkCategory]


class MessageEnvelope(TypedDict):
    event: str
    version: int
    timestamp: str
    payload: KworkWantPayload | KworkCategoriesPayload
