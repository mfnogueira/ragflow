"""Base Worker for RabbitMQ message consumption with async/await."""

import asyncio
import json
import signal
from abc import ABC, abstractmethod
from typing import Any, Dict

from aio_pika import connect_robust, Message, IncomingMessage
from aio_pika.abc import AbstractChannel, AbstractConnection, AbstractRobustConnection
from aio_pika.exceptions import AMQPConnectionError, AMQPChannelError

from src.lib.config import settings
from src.lib.exceptions import QueueError
from src.lib.logger import get_logger

logger = get_logger(__name__)


class BaseWorker(ABC):
    """
    Base class for async RabbitMQ workers.

    Provides async connection management, message consumption, and error handling.
    Subclasses must implement the async process_message() method.
    """

    def __init__(
        self,
        queue_name: str,
        prefetch_count: int | None = None,
    ):
        """
        Initialize base worker.

        Args:
            queue_name: Name of the queue to consume from
            prefetch_count: Number of messages to prefetch (default: from settings)
        """
        self.queue_name = queue_name
        self.prefetch_count = prefetch_count or settings.rabbitmq_prefetch_count

        self.connection: AbstractRobustConnection | None = None
        self.channel: AbstractChannel | None = None
        self.should_stop = False

        logger.info(
            f"Initialized {self.__class__.__name__} "
            f"(queue={queue_name}, prefetch={self.prefetch_count})"
        )

    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        loop = asyncio.get_event_loop()

        def signal_handler(signum):
            logger.info(f"Received signal {signum}, initiating graceful shutdown...")
            self.should_stop = True
            # Schedule stop coroutine
            asyncio.create_task(self.stop())

        # Register signal handlers
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda s=sig: signal_handler(s))

    async def _connect(self) -> None:
        """
        Establish connection to RabbitMQ.

        Raises:
            QueueError: If connection fails
        """
        try:
            logger.info(f"Connecting to RabbitMQ: {settings.rabbitmq_url.split('@')[1] if '@' in settings.rabbitmq_url else 'localhost'}")

            # Use connect_robust for automatic reconnection
            self.connection = await connect_robust(
                settings.rabbitmq_url,
                timeout=30,
            )

            self.channel = await self.connection.channel()

            # Set QoS (prefetch count)
            await self.channel.set_qos(prefetch_count=self.prefetch_count)

            # Declare queue (idempotent)
            queue = await self.channel.declare_queue(
                self.queue_name,
                durable=True,
            )

            logger.info(f"Connected to RabbitMQ, consuming from queue '{self.queue_name}'")

        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise QueueError(f"Connection failed: {e}")

    async def _disconnect(self) -> None:
        """Close RabbitMQ connection."""
        try:
            if self.channel and not self.channel.is_closed:
                await self.channel.close()
                logger.info("Channel closed")

            if self.connection and not self.connection.is_closed:
                await self.connection.close()
                logger.info("Connection closed")

        except Exception as e:
            logger.error(f"Error during disconnect: {e}")

    async def _on_message(self, message: IncomingMessage) -> None:
        """
        Callback for incoming messages.

        Args:
            message: Incoming message from RabbitMQ
        """
        async with message.process():
            try:
                # Decode message
                message_str = message.body.decode("utf-8")
                message_data = json.loads(message_str)

                logger.info(
                    f"Received message (delivery_tag={message.delivery_tag}, "
                    f"message_id={message_data.get('message_id', 'N/A')})"
                )
                logger.debug(f"Message data: {message_data}")

                # Process message (implemented by subclass)
                await self.process_message(message_data)

                logger.info(
                    f"Successfully processed message (delivery_tag={message.delivery_tag})"
                )

            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in message: {e}")
                # Message will be rejected (not requeued) by context manager
                await message.reject(requeue=False)

            except Exception as e:
                logger.error(f"Error processing message: {e}", exc_info=True)
                # Requeue message for retry
                # TODO: Implement retry logic with max_retries and dead letter queue
                await message.reject(requeue=True)

    @abstractmethod
    async def process_message(self, message: Dict[str, Any]) -> Any:
        """
        Process a message from the queue.

        This method must be implemented by subclasses as async.

        Args:
            message: Parsed message data (dict)

        Returns:
            Processing result (any type)

        Raises:
            Exception: If processing fails
        """
        pass

    async def start(self) -> None:
        """
        Start consuming messages from the queue.

        This is an async operation that runs until stopped.
        """
        logger.info(f"Starting {self.__class__.__name__}...")

        # Setup signal handlers
        self._setup_signal_handlers()

        attempt = 0
        max_attempts = settings.rabbitmq_connection_attempts

        while not self.should_stop and attempt < max_attempts:
            try:
                attempt += 1

                # Connect to RabbitMQ
                await self._connect()

                # Get queue
                queue = await self.channel.declare_queue(
                    self.queue_name,
                    durable=True,
                )

                # Start consuming
                logger.info(f"Waiting for messages on queue '{self.queue_name}'...")
                await queue.consume(self._on_message)

                # Keep running until stop signal
                while not self.should_stop:
                    await asyncio.sleep(1)

                # Break out of retry loop on graceful stop
                break

            except AMQPConnectionError as e:
                logger.error(f"Connection error (attempt {attempt}/{max_attempts}): {e}")

                if attempt < max_attempts and not self.should_stop:
                    retry_delay = settings.rabbitmq_retry_delay
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error("Max connection attempts reached, exiting")
                    break

            except AMQPChannelError as e:
                logger.error(f"Channel error: {e}")
                break

            except Exception as e:
                logger.error(f"Unexpected error: {e}", exc_info=True)
                break

            finally:
                await self._disconnect()

        logger.info(f"{self.__class__.__name__} stopped")

    async def stop(self) -> None:
        """Stop the worker gracefully."""
        logger.info(f"Stopping {self.__class__.__name__}...")
        self.should_stop = True
        await self._disconnect()
