import logging.config
import connexion
import yaml
import logging.config
import json
import httpx
from datetime import datetime, timezone
from apscheduler.schedulers.background import BackgroundScheduler

# Load logging configuration
with open("log_conf.yml", "r") as f:
    LOG_CONFIG = yaml.safe_load(f.read())
    logging.config.dictConfig(LOG_CONFIG)

# Load processing service configuration
with open("app_conf.yml", "r") as f:
    app_config = yaml.safe_load(f.read())

DATA_FILE = app_config["datastore"]["filename"]

logger = logging.getLogger('basicLogger')

def get_stats():
    logger.info("Request for stats received")
    try:
        with open(DATA_FILE, "r") as fd:
            stats = json.load(fd)
            logger.debug(stats)
            logger.info("Request for stats completed")
    except Exception as e:
        logger.error("Failed to get statistics: " + str(e))
        return {"message": "Statistics do not exist"}, 404
    return stats, 200

def populate_stats():
    logger.info("Periodic processing started")
    # Load current stats from JSON file or initialize defaults
    try:
        with open(DATA_FILE, "r") as fd:
            stats = json.load(fd)
    except Exception:
        stats = {
            "num_player_performance": 0,
            "max_score": 0,
            "num_audience_interaction": 0,
            "max_numeric_value": 0,
            "last_updated": None
        }
    # Determine start timestamp: use last_updated if available; otherwise use a default date
    if stats.get("last_updated"):
        start_timestamp = stats["last_updated"]
    else:
        start_timestamp = "1970-01-01T00:00:00.000Z"
    # End timestamp is now (in UTC) in ISO format
    end_timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    # Query player performance events from storage service
    pp_url = app_config["eventstores"]["player_performance"]["url"]
    pp_response = httpx.get(f"{pp_url}?start_timestamp={start_timestamp}&end_timestamp={end_timestamp}")
    if pp_response.status_code != 200:
        logger.error(f"Request for player performance events failed: {pp_response.status_code}")
        pp_events = []
    else:
        pp_events = pp_response.json()
        logger.info(f"Received {len(pp_events)} player performance events")

    # Query audience interaction events from storage service
    ai_url = app_config["eventstores"]["audience_interaction"]["url"]
    ai_response = httpx.get(f"{ai_url}?start_timestamp={start_timestamp}&end_timestamp={end_timestamp}")
    if ai_response.status_code != 200:
        logger.error(f"Request for audience interaction events failed: {ai_response.status_code}")
        ai_events = []
    else:
        ai_events = ai_response.json()
        logger.info(f"Received {len(ai_events)} audience interaction events")

    # Update cumulative statistics
    stats["num_player_performance"] += len(pp_events)
    # Update maximum score from player performance events
    for event in pp_events:
        score = event.get("score", 0)
        if score > stats["max_score"]:
            stats["max_score"] = score

    stats["num_audience_interaction"] += len(ai_events)
    # Update maximum numeric_value from audience interaction events
    for event in ai_events:
        value = event.get("numeric_value", 0)
        if value > stats["max_numeric_value"]:
            stats["max_numeric_value"] = value

    # Update the last_updated timestamp
    stats["last_updated"] = end_timestamp

    # Write updated stats to the JSON file
    with open(DATA_FILE, "w") as fd:
        json.dump(stats, fd, indent=4)

    logger.debug(f"Updated stats: {stats}")
    logger.info("Periodic processing ended")

# Scheduler runs every few secs to get new events from storage using get request
def init_scheduler():
    sched = BackgroundScheduler(daemon=True)
    interval = app_config["scheduler"]["interval"]
    sched.add_job(populate_stats, 'interval', seconds=interval)
    sched.start()

app = connexion.FlaskApp(__name__, specification_dir='')
app.add_api("stats.yaml", strict_validation=True, validate_responses=True)

if __name__ == "__main__":
    init_scheduler()
    app.run(port=8100, host="0.0.0.0", debug=True)
