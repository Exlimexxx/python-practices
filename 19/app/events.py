"""Публикация события BookingCreated через RabbitMQ (или локальный адаптер в тестах)."""
from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)
_local_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()


async def publish_event(event: dict[str, Any]) -> None:
    """Если задан RABBITMQ_URL, публикует durable-событие в fanout exchange."""
    broker_url = os.getenv("RABBITMQ_URL")
    if not broker_url:
        await _local_queue.put(event)
        logger.info("Локально опубликовано событие %s", event.get("event_type"))
        return
    import aio_pika

    connection = await aio_pika.connect_robust(broker_url)
    async with connection:
        channel = await connection.channel()
        exchange = await channel.declare_exchange("hotel.events", aio_pika.ExchangeType.FANOUT, durable=True)
        message = aio_pika.Message(
            body=json.dumps(event, ensure_ascii=False).encode("utf-8"),
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            content_type="application/json",
        )
        await exchange.publish(message, routing_key="")
        logger.info("Опубликовано событие %s в RabbitMQ", event.get("event_type"))


async def receive_local_event() -> dict[str, Any]:
    """Адаптер для изолированного теста брокерного сценария."""
    return await _local_queue.get()
