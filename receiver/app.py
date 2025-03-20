import logging.config
import connexion
from connexion import NoContent
import yaml
import json
import datetime
import uuid
from pykafka import KafkaClient

# Load logging configuration
with open("log_conf.yml", "r") as f:
    LOG_CONFIG = yaml.safe_load(f.read())
    logging.config.dictConfig(LOG_CONFIG)
logger = logging.getLogger('basicLogger')

# Load service configuration
with open("app_conf.yml", "r") as f:
    app_config = yaml.safe_load(f.read())

def post_player_performance_event(body):
    # Generate trace_id and uuid for the event
    body["trace_id"] = str(uuid.uuid4())
    body["uuid"] = str(uuid.uuid4())
    # uses the configuration values to connect to Kafka and select the “events” topic
    client = KafkaClient(hosts=f"{app_config['events']['hostname']}:{app_config['events']['port']}")
    topic = client.topics[str.encode(app_config['events']['topic'])]
    producer = topic.get_sync_producer()
    # JSON message
    msg = {
        "type": "player-performance",
        "datetime": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "payload": body
    }
    # The event is serialized to JSON and encoded as UTF-8 before being sent. A log statement is recorded 
    msg_str = json.dumps(msg)
    producer.produce(msg_str.encode('utf-8'))
    logger.info(f"Produced player-performance event with trace_id {body['trace_id']}")
    return NoContent, 201 # returns and HTTP 201 response

def post_audience_interaction_event(body):
    # Generate trace_id and uuid for the event
    body["trace_id"] = str(uuid.uuid4())
    body["uuid"] = str(uuid.uuid4())
    
    client = KafkaClient(hosts=f"{app_config['events']['hostname']}:{app_config['events']['port']}")
    topic = client.topics[str.encode(app_config['events']['topic'])]
    producer = topic.get_sync_producer()
    msg = {
        "type": "audience-interaction",
        "datetime": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "payload": body
    }
    msg_str = json.dumps(msg)
    producer.produce(msg_str.encode('utf-8'))
    logger.info(f"Produced audience-interaction event with trace_id {body['trace_id']}")
    return NoContent, 201

app = connexion.FlaskApp(__name__, specification_dir='')
app.add_api("receiver_openapi.yaml", strict_validation=True, validate_responses=True)

if __name__ == "__main__":
    app.run(port=8080, host="0.0.0.0", debug=True)
