import logging.config
import connexion
import yaml
import json
from pykafka import KafkaClient
from pykafka.common import OffsetType
from threading import Thread
from models import init_db, Session, PlayerPerformance, AudienceInteraction
import datetime

# Load service configuration
with open("app_conf.yml", "r") as f:
    app_config = yaml.safe_load(f.read())

# Load logging configuration
with open("log_conf.yml", "r") as f:
    LOG_CONFIG = yaml.safe_load(f.read())
    logging.config.dictConfig(LOG_CONFIG)
logger = logging.getLogger('basicLogger')

def process_messages():
    # Consume messages from Kafka and store them in the database
    kafka_host = f"{app_config['events']['hostname']}:{app_config['events']['port']}"
    client = KafkaClient(hosts=kafka_host)
    topic = client.topics[str.encode(app_config['events']['topic'])]
    
    # This creates a consumer in a specified consumer group so that Kafka can track offsets.
    # Using auto_offset_reset=LATEST ensures that only new messages are processed.
    consumer = topic.get_simple_consumer(
        consumer_group=b'event_group',
        reset_offset_on_start=False,
        auto_offset_reset=OffsetType.LATEST
    )
    
    # The consumer enters a loop
    # Every message is decoded and parsed from JSON. 
    # The log output confirms that messages are received.
    for msg in consumer:
        if msg is None:
            continue
        try:
            msg_str = msg.value.decode('utf-8')
            message = json.loads(msg_str)
            logger.info("Consumed message: %s", message)
            payload = message["payload"]
            # The code then checks the "type" field in the message
            # Depending on the event type, the corresponding function is called to store the event in the database.
            if message["type"] == "player-performance":
                store_player_performance(payload)
            elif message["type"] == "audience-interaction":
                store_audience_interaction(payload)
            # After processing each message, the consumer commits the offset
            # This ensures that once a message is processed, it won’t be re-read on a restart
            consumer.commit_offsets()
        except Exception as e:
            logger.error("Error processing message: %s", e)

def store_player_performance(payload):
    # uses SQLAlchemy to create a new session, instantiate a new model object, add it to the session, and commit the changes
    # handles inserting the event into the MySQL database
    session = Session()
    try:
        event = PlayerPerformance(payload['playerId'],
                                  payload['score'],
                                  payload['uuid'],
                                  payload['numeric_value'],
                                  payload['trace_id'])
        session.add(event)
        session.commit()
        logger.info("Stored PlayerPerformance event with trace_id: %s", payload['trace_id'])
    except Exception as e:
        logger.error("Error storing PlayerPerformance: %s", e)
        session.rollback()
    finally:
        session.close()

def store_audience_interaction(payload):
    session = Session()
    try:
        event = AudienceInteraction(payload['interactionType'],
                                    payload['trace_id'],
                                    payload['uuid'],
                                    payload['numeric_value'])
        session.add(event)
        session.commit()
        logger.info("Stored AudienceInteraction event with trace_id: %s", payload['trace_id'])
    except Exception as e:
        logger.error("Error storing AudienceInteraction: %s", e)
        session.rollback()
    finally:
        session.close()

# To run the consumer continuously alongside serving API endpoints
def setup_kafka_thread():
    t = Thread(target=process_messages)
    t.daemon = True
    t.start()

# GET endpoints to query stored events
def get_player_performance(start_timestamp, end_timestamp):
    from datetime import datetime
    # shows how events are filtered by their creation timestamp and returned to the user via the GET endpoint.
    try:
        start = datetime.fromisoformat(start_timestamp.replace("Z", "+00:00"))
        end = datetime.fromisoformat(end_timestamp.replace("Z", "+00:00"))
    except Exception as e:
        logger.error("Invalid timestamp format: %s", e)
        return {"error": "Invalid timestamp format"}, 400
    session = Session()
    events = session.query(PlayerPerformance).filter(
        PlayerPerformance.date_created >= start,
        PlayerPerformance.date_created < end
    ).all()
    session.close()
    return [event.to_dict() for event in events], 200

def get_audience_interaction(start_timestamp, end_timestamp):
    from datetime import datetime
    try:
        start = datetime.fromisoformat(start_timestamp.replace("Z", "+00:00"))
        end = datetime.fromisoformat(end_timestamp.replace("Z", "+00:00"))
    except Exception as e:
        logger.error("Invalid timestamp format: %s", e)
        return {"error": "Invalid timestamp format"}, 400
    session = Session()
    events = session.query(AudienceInteraction).filter(
        AudienceInteraction.date_created >= start,
        AudienceInteraction.date_created < end
    ).all()
    session.close()
    return [event.to_dict() for event in events], 200

app = connexion.FlaskApp(__name__, specification_dir='')
app.add_api("storage_openapi.yaml", strict_validation=True, validate_responses=True)

if __name__ == "__main__":
    init_db()
    setup_kafka_thread()
    app.run(port=8090, host="0.0.0.0", debug=True)
