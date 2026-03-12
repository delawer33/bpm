from __future__ import annotations

import asyncio
import logging

import aio_pika
from aio_pika import IncomingMessage

from app.core.config import get_settings
from app.core.db import async_session_factory
from app.core.rabbitmq import (
    QUEUE_STORAGE_OBJECT_CREATED,
    ensure_topology,
)
from app.worker.handlers import handle_track_file_upload
from app.worker.parsers import parse_storage_event

# logger = logging.getLogger("app_logger")
from app.logger_settings import logger

PREFIX_TRACK_FILES = "tmp/"


async def on_message(message: IncomingMessage) -> None:
    async with message.process(ignore_processed=True):
        body = message.body
        parsed = parse_storage_event(body)
        if not parsed:
            logger.warning("Could not parse event body")
            return
        bucket, key = parsed
        if key.startswith(PREFIX_TRACK_FILES):
            async with async_session_factory() as session:
                try:
                    await handle_track_file_upload(session, bucket, key)
                except Exception as e:
                    if getattr(message, "redelivered", False):
                        logger.exception("Giving up after redelivery for %s: %s", key, e)
                        return
                    await message.nack(requeue=True)
                    raise
        else:
            logger.debug("No handler for key prefix: %s", key[:20])


async def run_worker() -> None:
    settings = get_settings()
    ensure_topology(settings.rabbitmq_url)
    connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=1)
    queue = await channel.get_queue(QUEUE_STORAGE_OBJECT_CREATED, ensure=True)
    await queue.consume(on_message)
    logger.info("Worker consuming from %s", QUEUE_STORAGE_OBJECT_CREATED)
    await asyncio.Future()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
