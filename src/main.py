from __future__ import annotations

import asyncio

import redis.asyncio as aioredis

from .config import cfg
from .logger import get_logger
from .parser import KworkParser
from .publisher import KworkPublisher

logger = get_logger().bind(service="parser-kwork", module=__name__)


async def _is_new(dedup: aioredis.Redis, want_id: int) -> bool:
    key = f"kwork:want:{want_id}"
    result = await dedup.set(
        key,
        "1",
        ex=cfg.dragonfly.dedup_ttl_seconds,
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
        if await _is_new(dedup, want.want_id):
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
