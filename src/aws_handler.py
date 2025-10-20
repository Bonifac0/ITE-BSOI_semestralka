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


def _add_to_failed_queue(data):
    queue = _load_failed_queue()
    queue.append(data)
    _save_failed_queue(queue)


def retry_failed_tasks():
    queue = _load_failed_queue()
    if not queue:
        return

    print(f"Retrying {len(queue)} failed tasks...")
    new_queue = []

    for item in queue:
        if not upload_to_aws(**item):
            new_queue.append(item)

    _save_failed_queue(new_queue)


# Create Measurement
def upload_to_aws(data):  # TODO add alert capabilities
    print(f"Uploading for sensorUUID {data[1]}")

    measurement_payload = {
        "createdOn": data["timestamp"],
        "sensorUUID": data["sensor"],
        "temperature": str(data["value"]),  # propably has to be string
        "status": "TEST",  # dont know, I have to ask
    }

    answer = _post_(conf.EP_MEASUREMENTS, measurement_payload)
    if bool(answer):
        print(f"Measurement creation successful:\n{answer}")
        return True
    else:
        _add_to_failed_queue(data)
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
