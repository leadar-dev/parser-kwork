from __future__ import annotations

from datetime import UTC, datetime

from faststream.rabbit import ExchangeType, RabbitBroker, RabbitExchange

from .config import cfg
from .logger import get_logger
from .models import KworkWant, KworkWantPayload, MessageEnvelope

logger = get_logger().bind(service="parser-kwork", module=__name__)

_EXCHANGE_NAME = "leadar.events"
_ROUTING_KEY = "parser.kwork.want"

_exchange = RabbitExchange(
    _EXCHANGE_NAME,
    type=ExchangeType.TOPIC,
    durable=True,
)


class KworkPublisher:
    def __init__(self) -> None:
        self._broker = RabbitBroker(cfg.rabbitmq.url)
        self.log = logger.bind(component="KworkPublisher")

    async def start(self) -> None:
        await self._broker.start()
        self.log.info("connected", url=cfg.rabbitmq.url)

    async def stop(self) -> None:
        await self._broker.stop()
        self.log.info("disconnected")

    async def publish(self, want: KworkWant) -> None:
        log = self.log.bind(func="publish", want_id=want.want_id)
        log.debug("start")

        payload: KworkWantPayload = {
            "source": "kwork",
            "want_id": want.want_id,
            "name": want.name,
            "description": want.description,
            "price_limit": want.price_limit,
            "possible_price_limit": want.possible_price_limit,
            "category_id": want.category_id,
            "max_days": want.max_days,
            "status": want.status,
            "kwork_count": want.kwork_count,
            "views": want.views,
            "hired_percent": want.hired_percent,
            "url": want.url,
            "date_create": want.date_create.isoformat(),
            "date_expire": want.date_expire.isoformat()
            if want.date_expire
            else None,
        }

        envelope: MessageEnvelope = {
            "event": _ROUTING_KEY,
            "version": 1,
            "timestamp": datetime.now(UTC).isoformat(),
            "payload": payload,
        }

        await self._broker.publish(
            envelope,
            routing_key=_ROUTING_KEY,
            exchange=_exchange,
        )
        log.info("done", routing_key=_ROUTING_KEY, name=want.name)
