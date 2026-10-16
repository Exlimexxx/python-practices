"""Отдельный потребитель событий RabbitMQ; действует на событие BookingCreated."""
from __future__ import annotations
import asyncio
import json
import logging
import os
import aio_pika

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("hotel.notifications")


async def main() -> None:
    url = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")
    connection = await aio_pika.connect_robust(url)
    async with connection:
        channel = await connection.channel()
        exchange = await channel.declare_exchange("hotel.events", aio_pika.ExchangeType.FANOUT, durable=True)
        queue = await channel.declare_queue("hotel.notifications", durable=True)
        await queue.bind(exchange)
        logger.info("Notification Service ожидает события hotel.events")
        async with queue.iterator() as iterator:
            async for message in iterator:
                async with message.process():
                    event = json.loads(message.body.decode("utf-8"))
                    if event.get("event_type") == "BookingCreated":
                        booking = event.get("booking", {})
                        logger.info("Уведомление: создано бронирование id=%s", booking.get("id"))


if __name__ == "__main__":
    asyncio.run(main())
