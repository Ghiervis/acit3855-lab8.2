import logging.config
import connexion
import yaml
import json
from pykafka import KafkaClient
from pykafka.common import OffsetType

with open("app_conf.yml", "r") as f:
    app_config = yaml.safe_load(f)

with open("log_conf.yml", "r") as f:
    log_config = yaml.safe_load(f)
    logging.config.dictConfig(log_config)

logger = logging.getLogger('basicLogger')

# Extract Kafka details from the loaded config
KAFKA_HOST = app_config["kafka"]["hostname"]
KAFKA_PORT = app_config["kafka"]["port"]
KAFKA_TOPIC = app_config["kafka"]["topic"]

def get_kafka_messages():
    # Connects to Kafka, read all messages in the topic (using a short timeout),
    # and return a list of parsed JSON messages.
    kafka_host = f"{KAFKA_HOST}:{KAFKA_PORT}"
    # Create a Kafka client (assumes connection is successful)
    client = KafkaClient(hosts=kafka_host)
    # Referencing the configured topic (encode the topic string)
    topic = client.topics[KAFKA_TOPIC.encode()]
    # Creates a simple consumer that starts at the earliest offset
    # and times out after 1 second if no new messages appear
    consumer = topic.get_simple_consumer(
        reset_offset_on_start=True,
        auto_offset_reset=OffsetType.EARLIEST,
        consumer_timeout_ms=1000
    )
    # Read and decode messages directly
    messages = [json.loads(msg.value.decode("utf-8")) for msg in consumer]
    # Stop the consumer to clean up
    consumer.stop()
    logger.debug("Total messages fetched from Kafka: %d", len(messages))
    return messages

def get_player_performance_event(index):
    # Returns the player-performance event at the given index among the events in Kafka.
    # Gets all messages
    messages = get_kafka_messages()
    # Filter by type == "player-performance"
    filtered = [m for m in messages if m.get("type") == "player-performance"]
    # Check if the index is within range
    if index < len(filtered):
        logger.info("Found player-performance event at index %d", index)
        return filtered[index], 200
    else:
        logger.info("No event of type 'player-performance' found at index %d", index)
        return {"message": f"No event of type 'player-performance' found at index {index}"}, 404

def get_audience_interaction_event(index):
    # Returns the audience-interaction event at the given index among the events in Kafka.
    # Gets all messages
    messages = get_kafka_messages()
    # Filter by type == "audience-interaction"
    filtered = [m for m in messages if m.get("type") == "audience-interaction"]
    # Check if the index is within range
    if index < len(filtered):
        logger.info("Found audience-interaction event at index %d", index)
        return filtered[index], 200
    else:
        logger.info("No event of type 'audience-interaction' found at index %d", index)
        return {"message": f"No event of type 'audience-interaction' found at index {index}"}, 404

def get_event_stats():
    # Gets all messages
    messages = get_kafka_messages()
    # Computes statistics on the events in Kafka.
    # Returns a JSON object with counts of each event type.
    # Count how many are of each type
    num_player_performance = sum(1 for m in messages if m.get("type") == "player-performance")
    num_audience_interaction = sum(1 for m in messages if m.get("type") == "audience-interaction")
    stats = {
        "num_player_performance": num_player_performance,
        "num_audience_interaction": num_audience_interaction
    }
    logger.info("Event stats computed: %s", stats)
    return stats, 200

app = connexion.FlaskApp(__name__, specification_dir="")
app.add_api("openapi.yaml", strict_validation=True, validate_responses=True)

if __name__ == "__main__":
    app.run(port=8110, host="0.0.0.0", debug=True)

# If stats are the same this means that the Processing Service 
# has successfully consumed and stored all events from Kafka without missing any.

# If stats are different it means that the Processing Service 
# has not yet consumed or processed some Kafka messages.
# Reasons: delay in processing events, processing service crashed, filter mech ignored some events.
