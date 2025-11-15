"""Base Worker for RabbitMQ message consumption."""

import json
import signal
import sys
from abc import ABC, abstractmethod
from typing import Any, Dict

import pika
from pika.adapters.blocking_connection import BlockingChannel
from pika.exceptions import AMQPConnectionError, AMQPChannelError

from src.lib.config import settings
from src.lib.exceptions import QueueError
from src.lib.logger import get_logger

logger = get_logger(__name__)


class BaseWorker(ABC):
    """
    Base class for RabbitMQ workers.

    Provides connection management, message consumption, and error handling.
    Subclasses must implement the process_message() method.
    """

    def __init__(
        self,
        queue_name: str,
        prefetch_count: int | None = None,
        auto_ack: bool = False,
    ):
        """
        Initialize base worker.

        Args:
            queue_name: Name of the queue to consume from
            prefetch_count: Number of messages to prefetch (default: from settings)
            auto_ack: Whether to auto-acknowledge messages (default: False)
        """
        self.queue_name = queue_name
        self.prefetch_count = prefetch_count or settings.rabbitmq_prefetch_count
        self.auto_ack = auto_ack

        self.connection = None
        self.channel = None
        self.should_stop = False

        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        logger.info(
            f"Initialized {self.__class__.__name__} "
            f"(queue={queue_name}, prefetch={self.prefetch_count})"
        )

    def _signal_handler(self, signum, frame):
        """
        Handle shutdown signals (SIGINT, SIGTERM).

        Args:
            signum: Signal number
            frame: Current stack frame
        """
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.should_stop = True

        if self.channel and self.channel.is_open:
            self.channel.stop_consuming()

    def _connect(self) -> None:
        """
        Establish connection to RabbitMQ.

        Raises:
            QueueError: If connection fails
        """
        try:
            logger.info(f"Connecting to RabbitMQ: {settings.rabbitmq_url.split('@')[1] if '@' in settings.rabbitmq_url else 'localhost'}")

            parameters = pika.URLParameters(settings.rabbitmq_url)
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()

            # Set QoS (prefetch count)
            self.channel.basic_qos(prefetch_count=self.prefetch_count)

            # Declare queue (idempotent)
            self.channel.queue_declare(queue=self.queue_name, durable=True)

            logger.info(f"Connected to RabbitMQ, consuming from queue '{self.queue_name}'")

        except AMQPConnectionError as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise QueueError(f"Connection failed: {e}")

    def _disconnect(self) -> None:
        """Close RabbitMQ connection."""
        try:
            if self.channel and self.channel.is_open:
                self.channel.close()
                logger.info("Channel closed")

            if self.connection and self.connection.is_open:
                self.connection.close()
                logger.info("Connection closed")

        except Exception as e:
            logger.error(f"Error during disconnect: {e}")

    def _on_message(
        self,
        channel: BlockingChannel,
        method: pika.spec.Basic.Deliver,
        properties: pika.spec.BasicProperties,
        body: bytes,
    ) -> None:
        """
        Callback for incoming messages.

        Args:
            channel: Channel object
            method: Delivery method
            properties: Message properties
            body: Message body (bytes)
        """
        try:
            # Decode message
            message_str = body.decode("utf-8")
            message_data = json.loads(message_str)

            logger.info(
                f"Received message (delivery_tag={method.delivery_tag}, "
                f"message_id={message_data.get('message_id', 'N/A')})"
            )
            logger.debug(f"Message data: {message_data}")

            # Process message (implemented by subclass)
            result = self.process_message(message_data)

            # Acknowledge message if not auto-ack
            if not self.auto_ack:
                channel.basic_ack(delivery_tag=method.delivery_tag)
                logger.debug(f"Acknowledged message (delivery_tag={method.delivery_tag})")

            logger.info(
                f"Successfully processed message (delivery_tag={method.delivery_tag})"
            )

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in message: {e}")
            # Reject and don't requeue invalid messages
            if not self.auto_ack:
                channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)

            # Requeue message for retry (or use dead letter queue)
            if not self.auto_ack:
                # TODO: Implement retry logic with max_retries
                channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

    @abstractmethod
    def process_message(self, message: Dict[str, Any]) -> Any:
        """
        Process a message from the queue.

        This method must be implemented by subclasses.

        Args:
            message: Parsed message data (dict)

        Returns:
            Processing result (any type)

        Raises:
            Exception: If processing fails
        """
        pass

    def start(self) -> None:
        """
        Start consuming messages from the queue.

        This is a blocking operation that runs until stopped.
        """
        logger.info(f"Starting {self.__class__.__name__}...")

        attempt = 0
        max_attempts = settings.rabbitmq_connection_attempts

        while not self.should_stop and attempt < max_attempts:
            try:
                attempt += 1

                # Connect to RabbitMQ
                self._connect()

                # Start consuming
                logger.info(f"Waiting for messages on queue '{self.queue_name}'...")
                self.channel.basic_consume(
                    queue=self.queue_name,
                    on_message_callback=self._on_message,
                    auto_ack=self.auto_ack,
                )

                # Start consuming (blocking)
                self.channel.start_consuming()

            except AMQPConnectionError as e:
                logger.error(f"Connection error (attempt {attempt}/{max_attempts}): {e}")

                if attempt < max_attempts and not self.should_stop:
                    import time
                    retry_delay = settings.rabbitmq_retry_delay
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
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
                self._disconnect()

        logger.info(f"{self.__class__.__name__} stopped")

    def stop(self) -> None:
        """Stop the worker gracefully."""
        logger.info(f"Stopping {self.__class__.__name__}...")
        self.should_stop = True

        if self.channel and self.channel.is_open:
            self.channel.stop_consuming()
