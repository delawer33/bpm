from __future__ import annotations

import asyncio
import logging
import signal
from typing import Callable

import aio_pika
from aio_pika import IncomingMessage

from app.core.config import get_settings
from app.core.db import async_session_factory
from app.core.rabbitmq import (
    QUEUE_STORAGE_OBJECT_CREATED,
    ensure_topology,
)
from app.logger_settings import logger
from app.worker.constants import PREFIX_TRACK_FILES
from app.worker.storage_client import init_storage_client, reset_storage_client
from app.worker.handlers import handle_track_file_upload
from app.worker.parsers import parse_storage_event

# (prefix, handler) in dispatch order
KEY_PREFIX_HANDLERS: list[tuple[str, Callable]] = [
    (PREFIX_TRACK_FILES, handle_track_file_upload),
]


async def on_message(message: IncomingMessage) -> None:
    async with message.process(ignore_processed=True):
        body = message.body
        parsed = parse_storage_event(body)
        if not parsed:
            logger.warning("Could not parse event body")
            return
        key = parsed.key
        bucket = parsed.bucket
        handled = False
        for prefix, handler in KEY_PREFIX_HANDLERS:
            if key.startswith(prefix):
                async with async_session_factory() as session:
                    try:
                        await handler(session, bucket, key)
                    except Exception as e:
                        if getattr(message, "redelivered", False):
                            logger.exception("Giving up after redelivery for %s: %s", key, e)
                            return
                        await message.nack(requeue=True)
                        raise
                handled = True
                break
        if not handled:
            logger.debug("No handler for key prefix: %s", key[:20])


async def run_worker() -> None:
    settings = get_settings()
    ensure_topology(settings.rabbitmq_url)
    init_storage_client()
    connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=1)
    queue = await channel.get_queue(QUEUE_STORAGE_OBJECT_CREATED, ensure=True)
    await queue.consume(on_message)
    logger.info("Worker consuming from %s", QUEUE_STORAGE_OBJECT_CREATED)

    stop = asyncio.Event()

    def on_signal() -> None:
        stop.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, on_signal)
        except (ValueError, OSError):
            pass
    try:
        await stop.wait()
    finally:
        await connection.close()
        reset_storage_client()
        logger.info("Worker stopped")


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
