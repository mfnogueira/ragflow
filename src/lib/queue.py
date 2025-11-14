"""RabbitMQ connection and message queue operations."""

import json
from typing import Any, Callable

import pika
from pika.adapters.blocking_connection import BlockingChannel, BlockingConnection
from pika.exceptions import AMQPConnectionError

from .config import settings
from .exceptions import QueueError
from .logger import get_logger

logger = get_logger(__name__)


class QueueManager:
    """Manager for RabbitMQ connections and operations."""

    def __init__(self) -> None:
        """Initialize queue manager."""
        self.connection: BlockingConnection | None = None
        self.channel: BlockingChannel | None = None
        self._setup_connection()

    def _setup_connection(self) -> None:
        """Establish connection to RabbitMQ."""
        try:
            parameters = pika.URLParameters(settings.rabbitmq_url)
            parameters.connection_attempts = settings.rabbitmq_connection_attempts
            parameters.retry_delay = settings.rabbitmq_retry_delay

            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()

            # Set QoS for fair dispatch
            self.channel.basic_qos(prefetch_count=settings.rabbitmq_prefetch_count)

            # Declare queues
            self._declare_queues()

            logger.info("Connected to RabbitMQ successfully")

        except AMQPConnectionError as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise QueueError(f"RabbitMQ connection failed: {e}")

    def _declare_queues(self) -> None:
        """Declare all application queues with appropriate settings."""
        if not self.channel:
            raise QueueError("Channel not initialized")

        queues = {
            "ingest_queue": {
                "durable": True,
                "arguments": {
                    "x-message-ttl": 3600000,  # 1 hour
                    "x-max-length": 10000,
                    "x-dead-letter-exchange": "failed_exchange",
                }
            },
            "embed_queue": {
                "durable": True,
                "arguments": {
                    "x-message-ttl": 7200000,  # 2 hours
                    "x-max-length": 50000,
                    "x-dead-letter-exchange": "failed_exchange",
                }
            },
            "query_queue": {
                "durable": True,
                "arguments": {
                    "x-message-ttl": 300000,  # 5 minutes
                    "x-max-length": 20000,
                    "x-dead-letter-exchange": "failed_exchange",
                }
            },
            "audit_queue": {
                "durable": True,
                "arguments": {
                    "x-max-length": 100000,
                }
            },
            "failed_queue": {
                "durable": True,
                "arguments": {
                    "x-message-ttl": 604800000,  # 7 days
                }
            }
        }

        # Declare failed exchange
        self.channel.exchange_declare(
            exchange="failed_exchange",
            exchange_type="fanout",
            durable=True
        )

        # Bind failed queue to failed exchange
        self.channel.queue_declare(queue="failed_queue", **queues["failed_queue"])
        self.channel.queue_bind(
            queue="failed_queue",
            exchange="failed_exchange"
        )

        # Declare all queues
        for queue_name, queue_args in queues.items():
            if queue_name != "failed_queue":  # Already declared above
                self.channel.queue_declare(queue=queue_name, **queue_args)
                logger.info(f"Declared queue: {queue_name}")

    def publish(
        self,
        queue_name: str,
        message: dict[str, Any],
        routing_key: str | None = None,
    ) -> None:
        """
        Publish message to queue.

        Args:
            queue_name: Target queue name
            message: Message payload (will be JSON serialized)
            routing_key: Optional routing key (defaults to queue_name)
        """
        if not self.channel:
            raise QueueError("Channel not initialized")

        routing_key = routing_key or queue_name

        try:
            self.channel.basic_publish(
                exchange="",
                routing_key=routing_key,
                body=json.dumps(message),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Make message persistent
                    content_type="application/json",
                )
            )
            logger.debug(f"Published message to {queue_name}: {message.get('message_id')}")

        except Exception as e:
            logger.error(f"Failed to publish message to {queue_name}: {e}")
            raise QueueError(f"Failed to publish message: {e}")

    def consume(
        self,
        queue_name: str,
        callback: Callable[[dict[str, Any]], None],
        auto_ack: bool = False,
    ) -> None:
        """
        Consume messages from queue.

        Args:
            queue_name: Queue to consume from
            callback: Function to handle each message
            auto_ack: Whether to auto-acknowledge messages
        """
        if not self.channel:
            raise QueueError("Channel not initialized")

        def on_message(
            ch: BlockingChannel,
            method: pika.spec.Basic.Deliver,
            properties: pika.spec.BasicProperties,
            body: bytes,
        ) -> None:
            """Handle incoming message."""
            try:
                message = json.loads(body.decode())
                logger.debug(f"Received message from {queue_name}: {message.get('message_id')}")

                # Process message
                callback(message)

                # Acknowledge message if not auto-ack
                if not auto_ack:
                    ch.basic_ack(delivery_tag=method.delivery_tag)

            except Exception as e:
                logger.error(f"Error processing message from {queue_name}: {e}")

                # Negative acknowledgment - send to DLQ
                if not auto_ack:
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

        self.channel.basic_consume(
            queue=queue_name,
            on_message_callback=on_message,
            auto_ack=auto_ack,
        )

        logger.info(f"Started consuming from {queue_name}")
        self.channel.start_consuming()

    def close(self) -> None:
        """Close RabbitMQ connection."""
        if self.channel:
            self.channel.close()
        if self.connection:
            self.connection.close()
        logger.info("Closed RabbitMQ connection")

    def __enter__(self) -> "QueueManager":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.close()


# Global queue manager instance
_queue_manager: QueueManager | None = None


def get_queue_manager() -> QueueManager:
    """Get global queue manager instance."""
    global _queue_manager
    if _queue_manager is None:
        _queue_manager = QueueManager()
    return _queue_manager


def get_rabbitmq_channel() -> BlockingChannel:
    """
    Get a new RabbitMQ channel for one-off operations.

    Note: For long-running operations, use get_queue_manager() instead.
    Remember to close the channel after use.
    """
    try:
        parameters = pika.URLParameters(settings.rabbitmq_url)
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()
        return channel
    except AMQPConnectionError as e:
        logger.error(f"Failed to create RabbitMQ channel: {e}")
        raise QueueError(f"Failed to create channel: {e}")
