from __future__ import annotations

import asyncio
import dataclasses
import json
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any, cast

import httpx

from .config import cfg
from .logger import get_logger
from .models import KworkWant, KworkWantDetail, RawWant

logger = get_logger().bind(service="parser-kwork", module=__name__)

STATE_DATA_MARKER = "window.stateData="


def _extract_state_data(html: str) -> dict[str, Any]:
    log = logger.bind(func="_extract_state_data")
    log.debug("start")

    idx = html.find(STATE_DATA_MARKER)
    if idx == -1:
        raise ValueError("window.stateData not found in HTML")

    start = idx + len(STATE_DATA_MARKER)
    depth = 0
    end = start
    for i, ch in enumerate(html[start:], start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    else:
        raise ValueError("Could not find end of window.stateData JSON")

    data = cast(dict[str, Any], json.loads(html[start:end]))
    log.debug("done", keys=list(data.keys())[:5])
    return data


def _parse_cookies(raw: str) -> dict[str, str]:
    if not raw:
        return {}
    cookies: dict[str, str] = {}
    for part in raw.split(";"):
        part = part.strip()
        if "=" in part:
            k, _, v = part.partition("=")
            cookies[k.strip()] = v.strip()
    return cookies


def _to_want(raw: RawWant) -> KworkWant | None:
    log = logger.bind(func="_to_want", want_id=raw.get("id"))
    try:
        user_data = (raw.get("user") or {}).get("data") or {}
        hired_str = user_data.get("wants_hired_percent")

        date_create = datetime.fromisoformat(raw["date_create"]).replace(
            tzinfo=UTC,
        )
        date_expire_str = raw.get("date_expire") or ""
        date_expire = (
            datetime.fromisoformat(date_expire_str).replace(tzinfo=UTC)
            if date_expire_str
            else None
        )

        want = KworkWant(
            want_id=int(raw["id"]),
            name=raw.get("name") or "",
            description=raw.get("description") or "",
            price_limit=float(raw.get("priceLimit") or 0),
            possible_price_limit=float(raw["possiblePriceLimit"])
            if raw.get("possiblePriceLimit")
            else None,
            category_id=int(raw.get("category_id") or 0),
            max_days=int(raw.get("max_days") or 0),
            status=raw.get("status") or "",
            kwork_count=int(raw.get("kwork_count") or 0),
            views=int(raw.get("views_dirty") or 0),
            hired_percent=float(hired_str) if hired_str else None,
            url=f"{cfg.kwork.base_url}/projects/{raw['id']}/view",
            date_create=date_create,
            date_expire=date_expire,
        )
        log.debug("done", name=want.name, price=want.price_limit)
        return want
    except Exception as e:
        log.error("parse failed", error=str(e), exc_info=True)
        return None


def _to_want_detail(raw: RawWant, tags: list[str]) -> KworkWantDetail | None:
    log = logger.bind(func="_to_want_detail", want_id=raw.get("id"))
    base = _to_want(raw)
    if base is None:
        return None
    try:
        return KworkWantDetail(**dataclasses.asdict(base), tags=tags)
    except Exception as e:
        log.error("detail build failed", error=str(e), exc_info=True)
        return None


class KworkParser:
    def __init__(self, category_id: int | None = None) -> None:
        self.category_id = category_id
        self.log = logger.bind(
            component="KworkParser",
            category_id=category_id,
        )
        self._cookies = _parse_cookies(cfg.kwork.cookies)
        self._headers = {
            "User-Agent": cfg.kwork.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ru-RU,ru;q=0.9",
        }

    def _build_url(self, page: int) -> str:
        params = f"page={page}"
        if self.category_id:
            params += f"&c={self.category_id}"
        return f"{cfg.kwork.base_url}/projects?{params}"

    async def fetch_want_detail(
        self,
        client: httpx.AsyncClient,
        want_id: int,
    ) -> KworkWantDetail | None:
        url = f"{cfg.kwork.base_url}/projects/{want_id}/view"
        log = self.log.bind(func="fetch_want_detail", want_id=want_id, url=url)
        log.debug("request")

        try:
            response = await client.get(url, follow_redirects=True)
            log.info(
                "response",
                status=response.status_code,
                size=len(response.content),
            )
            response.raise_for_status()
            state = _extract_state_data(response.text)
        except Exception as e:
            log.error("fetch failed", error=str(e), exc_info=True)
            return None

        raw_want = state.get("want")
        if not raw_want:
            log.warning("no want in stateData", keys=list(state.keys())[:10])
            return None

        raw_tags: list[Any] = raw_want.get("tags") or []
        tags: list[str] = [
            t["name"] if isinstance(t, dict) else str(t) for t in raw_tags if t
        ]

        return _to_want_detail(cast(RawWant, raw_want), tags)

    async def _fetch_page(
        self,
        client: httpx.AsyncClient,
        page: int,
    ) -> dict[str, Any]:
        url = self._build_url(page)
        log = self.log.bind(
            func="_fetch_page",
            url=url,
            method="GET",
            page=page,
        )
        log.debug("request")

        response = await client.get(url, follow_redirects=True)
        log.info(
            "response",
            status=response.status_code,
            size=len(response.content),
        )

        response.raise_for_status()
        return _extract_state_data(response.text)

    async def iter_wants(self) -> AsyncGenerator[KworkWant]:
        log = self.log.bind(func="iter_wants")
        log.info("start")

        async with httpx.AsyncClient(
            headers=self._headers,
            cookies=self._cookies,
            timeout=30,
        ) as client:
            try:
                state = await self._fetch_page(client, page=1)
            except Exception as e:
                log.error(
                    "failed to fetch page 1",
                    error=str(e),
                    exc_info=True,
                )
                return

            pagination = state.get("pagination") or {}
            last_page: int = pagination.get("last_page", 1)
            log.info(
                "listing info",
                pages=last_page,
                total=pagination.get("total", 0),
            )

            for raw in state.get("wants") or []:
                want = _to_want(cast(RawWant, raw))
                if want:
                    yield want

            for page in range(2, last_page + 1):
                page_log = log.bind(page=page, total=last_page)
                await asyncio.sleep(cfg.kwork.request_delay)

                try:
                    state = await self._fetch_page(client, page)
                except Exception as e:
                    page_log.error("page failed", error=str(e), exc_info=True)
                    continue

                wants = state.get("wants") or []
                if not wants:
                    page_log.warning("empty page, stopping")
                    break

                for raw in wants:
                    want = _to_want(cast(RawWant, raw))
                    if want:
                        yield want

                page_log.info("page done", count=len(wants))

        log.info("done")
