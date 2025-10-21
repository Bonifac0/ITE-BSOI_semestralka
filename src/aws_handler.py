from requests import get, post, HTTPError
from json import dumps, JSONDecodeError
import processor_config as conf
import json
import os


def _post_(ep, body):
    try:
        response = post(ep, dumps(body), headers=conf.HEADERS)

        if response.status_code == 200:
            try:
                return response.json()
            except JSONDecodeError:
                print("E: Response is not of JSON format.")
                return {}
        else:
            print("E: Status code:", response.status_code)
            return {}

    except HTTPError as http_err:
        print("E: HTTP error occurred:", http_err)
        return {}


def _get_(ep):
    try:
        response = get(ep, headers=conf.HEADERS)

        if response.status_code == 200:
            try:
                return response.json()
            except JSONDecodeError:
                print("E: Response is not of JSON format.")
                return {}
        else:
            print("E: Status code:", response.status_code)
            return {}

    except HTTPError as http_err:
        print("E: HTTP error occurred:", http_err)
        return {}


# === QUEUE HANDLING ===
def _load_failed_queue():
    if os.path.exists(conf.FAILED_QUEUE_FILE):
        with open(conf.FAILED_QUEUE_FILE, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                print("Error parsing failed_queue.json")
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

    print(f"Retrying {len(queue)} failed tasks...")
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
def measurement_to_aws(data):
    print(f"Uploading measurement for sensorUUID {data['sensor']}")

    payload = {
        "createdOn": data["timestamp"],  # format "2022-10-05T13:00:00.000+01:00"
        "sensorUUID": data["sensor"],
        "temperature": data["value"],
        "status": "TEST",  # for testing, after that change it to something
    }

    responce = _post_(conf.EP_MEASUREMENTS, payload)
    if bool(responce):
        print(f"Measurement creation successful:\n{responce}")
        return True
    else:
        _add_to_failed_queue("M", data)
        return False


# Create Alert
def alert_to_aws(data):
    print(f"Uploading alert for sensorUUID {data['sensor']}")

    payload = {  # no status
        "createdOn": data["timestamp"],  # format "2022-10-05T13:00:00.000+01:00"
        "sensorUUID": data["sensor"],
        "temperature": data["value"],
        "highTemperature": conf.SENS_MIN_MAX[data["sensor"]][1],
        "lowTemperature": conf.SENS_MIN_MAX[data["sensor"]][0],
    }

    responce = _post_(conf.EP_ALERTS, payload)
    if bool(responce):
        print(f"Alert creation successful:\n{responce}")
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


def is_alerting(data) -> bool:
    minimum = conf.SENS_MIN_MAX[data["sensor"]][0]
    maximum = conf.SENS_MIN_MAX[data["sensor"]][1]
    return (minimum > data["value"]) or (data["value"] > maximum)


if __name__ == "__main__":  # for testing
    sensor = conf.SENS_HUMI_UUID
    value = 80
    timestamp = "pul ctvrta"

    massage = {
        "sensor": sensor,
        "value": value,
        "timestamp": timestamp,
    }
    print(is_alerting(massage))
