"""Test script to verify RabbitMQ CloudAMQP connection."""

import pika

# RabbitMQ CloudAMQP credentials
rabbitmq_url = "amqps://cfxctijp:QSkl7_O1A50WgFmAwvM6SyKS7mke_SB6@duck.lmq.cloudamqp.com/cfxctijp"

try:
    print("Testing RabbitMQ CloudAMQP connection...")
    print(f"Instance: duck.lmq.cloudamqp.com")
    print(f"Vhost: cfxctijp")
    print()

    # Parse URL and create connection
    parameters = pika.URLParameters(rabbitmq_url)
    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()

    print("SUCCESS: Connected to RabbitMQ CloudAMQP!")
    print()

    # Test queue declaration
    test_queue = "test_connection_queue"
    channel.queue_declare(queue=test_queue, durable=True)
    print(f"SUCCESS: Declared test queue '{test_queue}'")

    # Delete test queue
    channel.queue_delete(queue=test_queue)
    print(f"SUCCESS: Deleted test queue '{test_queue}'")

    # Close connection
    connection.close()
    print()
    print("All RabbitMQ connection tests passed!")

except pika.exceptions.AMQPConnectionError as e:
    print(f"ERROR: Connection failed: {e}")
    print()
    print("Possible issues:")
    print("  - Check if credentials are correct")
    print("  - Verify CloudAMQP instance is active")
    print("  - Check network connectivity")

except Exception as e:
    print(f"ERROR: Unexpected error: {e}")
