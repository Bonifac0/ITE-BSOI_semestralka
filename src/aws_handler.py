from requests import get, post, HTTPError
from json import dumps, JSONDecodeError
import config as conf
import json
import os
from datetime import datetime, timezone, timedelta
from logger import log


def send_to_aws(massage: dict):
    """
    {'team_name': 'white', 'timestamp': '2020-03-24T15:26:05.336974', 'temperature': 25.72, 'humidity': 64.5, 'illumination': 1043}
    """
    for sense in ["temperature", "humidity", "illumination"]:
        if sense not in massage:  # skip if there is missing sensor
            continue
        data = {
            "sensor": conf.SENS_UUID[sense],
            "value": massage[sense],
            "timestamp": timestamp_refination(massage["timestamp"]),
        }

        measurement_to_aws(data)
        if is_alerting(data):  # podminka pro poslani alertu
            alert_to_aws(data)

    retry_failed_tasks()


def timestamp_refination(inp: str) -> str:
    """Convert UTC ISO timestamp to Prague winter time (UTC+1)."""
    # Parse input as UTC time
    dt_utc = datetime.fromisoformat(inp).replace(tzinfo=timezone.utc)
    # Convert to Prague winter time (CET = UTC+1)
    prague_winter = dt_utc.astimezone(timezone(timedelta(hours=1)))
    # Return ISO format with milliseconds
    return prague_winter.isoformat(timespec="milliseconds")


def _post_(ep, body):
    try:
        response = post(ep, dumps(body), headers=conf.HEADERS)

        if response.status_code == 200:
            try:
                return response.json()
            except JSONDecodeError:
                log(
                    f"Response is not of JSON format: {response}",
                    level="ERROR",
                    category="AWS",
                )
                return {}
        elif response.status_code == 504:
            log("Aws is not awake yet", level="WARNING")
            return {}
        else:
            log(f"Status code: {response.status_code}", level="ERROR", category="AWS")
            return {}

    except HTTPError as http_err:
        log(f"HTTP error occurred: {http_err}", level="ERROR", category="AWS")
        return {}


def _get_(ep):
    try:
        response = get(ep, headers=conf.HEADERS)

        if response.status_code == 200:
            try:
                return response.json()
            except JSONDecodeError:
                log(
                    f"Response is not of JSON format: {response}",
                    level="ERROR",
                    category="AWS",
                )
                return {}
        else:
            log(f"Status code: {response.status_code}", level="ERROR", category="AWS")
            return {}

    except HTTPError as http_err:
        log(f"HTTP error occurred: {http_err}", level="ERROR", category="AWS")
        return {}


# === QUEUE HANDLING ===
def _load_failed_queue():
    if os.path.exists(conf.FAILED_QUEUE_FILE):
        with open(conf.FAILED_QUEUE_FILE, "r") as f:
            try:
                content = f.read().strip()
                return json.loads(content) if content else []
            except json.JSONDecodeError:
                log("Error parsing failed_queue.json", level="ERROR", category="AWS")
                return []
    return []


def _save_failed_queue(queue):
    with open(conf.FAILED_QUEUE_FILE, "w") as f:
        json.dump(queue, f, indent=4)


def _add_to_failed_queue(type, data):
    queue = _load_failed_queue()
    queue.append((type, data))
    _save_failed_queue(queue)


def retry_failed_tasks():
    queue = _load_failed_queue()
    if not queue:
        return

    log(f"Retrying {len(queue)} failed tasks...", category="AWS")
    new_queue = []

    for type, item in queue:
        if type == "M":
            if not measurement_to_aws(item):  # it tryes to post and return result
                new_queue.append((type, item))
        elif type == "A":
            if not alert_to_aws(item):
                new_queue.append((type, item))

    _save_failed_queue(new_queue)


# Create Measurement
def measurement_to_aws(data: dict):
    # log(f"Uploading measurement for sensorUUID {data['sensor']}", category="AWS")

    payload = {
        "createdOn": data["timestamp"],  # format "2022-10-05T13:00:00.000+01:00"
        "sensorUUID": data["sensor"],
        "temperature": data["value"],
        "status": "OK",  # "test" for testing, "OK" for prod
    }

    responce = _post_(conf.EP_MEASUREMENTS, payload)
    if bool(responce):
        # log("Measurement upload to AWS sucessful", category="AWS")
        return True
    else:
        _add_to_failed_queue("M", data)
        return False


# Create Alert
def alert_to_aws(data: dict):
    # log(f"Uploading alert for sensorUUID {data['sensor']}", category="AWS")

    payload = {  # no status
        "createdOn": data["timestamp"],  # format "2022-10-05T13:00:00.000+01:00"
        "sensorUUID": data["sensor"],
        "temperature": data["value"],
        "highTemperature": conf.SENS_MIN_MAX[data["sensor"]][1],
        "lowTemperature": conf.SENS_MIN_MAX[data["sensor"]][0],
    }

    responce = _post_(conf.EP_ALERTS, payload)
    if bool(responce):
        # log("Alert upload to AWS sucessful", category="AWS")
        return True
    else:
        _add_to_failed_queue("A", data)
        return False


# Read Measurements
def read_measurements():  # if someone needs it
    measurements = _get_(conf.EP_MEASUREMENTS)

    for m in measurements:
        print(m)


def read_allerts():  # if someone needs if
    alerts = _get_(conf.EP_ALERTS)

    for alert in alerts:
        print(alert)


def is_alerting(data: dict) -> bool:
    minimum = conf.SENS_MIN_MAX[data["sensor"]][0]
    maximum = conf.SENS_MIN_MAX[data["sensor"]][1]
    return (minimum > data["value"]) or (data["value"] > maximum)


if __name__ == "__main__":  # for testing
    val = {
        "team_name": "blue",
        "timestamp": "2020-03-24T15:26:05.336974",
        "temperature": 21.72,
        "humidity": 64.5,
        "illumination": 1043,
    }

    # send_to_aws(val)
    print(timestamp_refination("2020-03-24T15:26:05.336974"))
