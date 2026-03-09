"""
RabbitMQ topology for BPM events (Option A: single topic exchange + one queue per event type + DLQ).

Call ensure_topology() at worker startup to declare exchange, queues, and bindings.
"""

from __future__ import annotations

import logging
from typing import Any

import pika

from app.core.config import get_settings

logger = logging.getLogger("app_logger")

EXCHANGE = "bpm.events"
ROUTING_KEY_STORAGE_OBJECT_CREATED = "storage.object.created"
QUEUE_STORAGE_OBJECT_CREATED = "queue.storage.object.created"
QUEUE_DLQ = "queue.dlq"
ROUTING_KEY_DLQ = "queue.dlq"


def ensure_topology(rabbitmq_url: str | None = None) -> None:
    settings = get_settings()
    url = rabbitmq_url or settings.rabbitmq_url
    parameters = pika.URLParameters(url)
    connection = pika.BlockingConnection(parameters)
    try:
        channel = connection.channel()
        channel.exchange_declare(
            exchange=EXCHANGE,
            exchange_type="topic",
            durable=True,
        )
        channel.queue_declare(
            queue=QUEUE_DLQ,
            durable=True,
        )
        channel.queue_bind(
            exchange=EXCHANGE,
            queue=QUEUE_DLQ,
            routing_key=ROUTING_KEY_DLQ,
        )
        channel.queue_declare(
            queue=QUEUE_STORAGE_OBJECT_CREATED,
            durable=True,
            arguments={
                "x-dead-letter-exchange": EXCHANGE,
                "x-dead-letter-routing-key": ROUTING_KEY_DLQ,
            },
        )
        channel.queue_bind(
            exchange=EXCHANGE,
            queue=QUEUE_STORAGE_OBJECT_CREATED,
            routing_key=ROUTING_KEY_STORAGE_OBJECT_CREATED,
        )
        logger.info(
            "RabbitMQ topology ensured: exchange=%s, queues=%s, %s",
            EXCHANGE,
            QUEUE_STORAGE_OBJECT_CREATED,
            QUEUE_DLQ,
        )
    finally:
        connection.close()


def declare_event_queue(channel: Any, routing_key: str) -> str:
    queue_name = f"queue.{routing_key}"
    channel.queue_declare(
        queue=queue_name,
        durable=True,
        arguments={
            "x-dead-letter-exchange": EXCHANGE,
            "x-dead-letter-routing-key": ROUTING_KEY_DLQ,
        },
    )
    channel.queue_bind(
        exchange=EXCHANGE,
        queue=queue_name,
        routing_key=routing_key,
    )
    return queue_name
