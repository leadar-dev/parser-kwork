from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import redis.asyncio as aioredis

from .config import cfg
from .logger import get_logger
from .models import KworkWant
from .parser import KworkParser
from .publisher import KworkPublisher

logger = get_logger().bind(service="parser-kwork", module=__name__)


def _dedup_ttl(want: KworkWant) -> int:
    if want.date_expire is not None:
        delta = want.date_expire - datetime.now(UTC)
        seconds = int(delta.total_seconds())
        if seconds > 0:
            return seconds
    return cfg.dragonfly.dedup_ttl_seconds


async def _is_new(dedup: aioredis.Redis, want: KworkWant) -> bool:
    key = f"kwork:want:{want.want_id}"
    result = await dedup.set(
        key,
        "1",
        ex=_dedup_ttl(want),
        nx=True,
    )
    return result is not None


async def _run_cycle(
    parser: KworkParser,
    publisher: KworkPublisher,
    dedup: aioredis.Redis,
) -> None:
    log = logger.bind(func="_run_cycle")
    log.info("start")

    total = 0
    published = 0

    async for want in parser.iter_wants():
        total += 1
        if await _is_new(dedup, want):
            await publisher.publish(want)
            published += 1

    log.info(
        "done",
        total=total,
        published=published,
        skipped=total - published,
    )


async def main() -> None:
    log = logger.bind(func="main")
    log.info("start", interval=cfg.parser.interval)

    parser = KworkParser()
    publisher = KworkPublisher()
    dedup: aioredis.Redis = aioredis.from_url(
        cfg.dragonfly.url,
        decode_responses=True,
    )

    await publisher.start()
    try:
        categories = await parser.fetch_categories()
        if categories:
            await publisher.publish_categories(categories)
        else:
            log.warning("no categories fetched, skipping publish")

        while True:
            try:
                await _run_cycle(parser, publisher, dedup)
            except Exception as e:
                log.error("cycle failed", error=str(e), exc_info=True)
            await asyncio.sleep(cfg.parser.interval)
    finally:
        await publisher.stop()
        await dedup.aclose()


if __name__ == "__main__":
    asyncio.run(main())
