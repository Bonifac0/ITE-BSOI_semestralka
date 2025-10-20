import json
import time
import ssl
import os
import requests
import paho.mqtt.client as mqtt
import mysql.connector
from mysql.connector import Error
import processor_config as conf


# === QUEUE HANDLING ===
def load_failed_queue():
    if os.path.exists(conf.FAILED_QUEUE_FILE):
        with open(conf.FAILED_QUEUE_FILE, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []


def save_failed_queue(queue):
    with open(conf.FAILED_QUEUE_FILE, "w") as f:
        json.dump(queue, f, indent=2)


def add_to_failed_queue(task_type, data):
    queue = load_failed_queue()
    queue.append({"task": task_type, "data": data, "timestamp": time.time()})
    save_failed_queue(queue)


def retry_failed_tasks():
    queue = load_failed_queue()
    if not queue:
        return

    print(f"Retrying {len(queue)} failed tasks...")
    new_queue = []

    for item in queue:
        success = False
        if item["task"] == "aws":
            success = upload_to_aws(item["data"])
        elif item["task"] == "mysql":
            success = insert_to_mysql(item["data"])

        if not success:
            new_queue.append(item)

    save_failed_queue(new_queue)


# === PROCESSING FUNCTION ===
def process_data(data):
    data["processed_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    data["temp_celsius"] = (data.get("temp_fahrenheit", 0) - 32) * 5 / 9

    upload_to_aws(data)
    insert_to_mysql(data)
    notify_local_server()

    retry_failed_tasks()


# === UPLOAD TO AWS ===
def upload_to_aws(data):
    """return True if sucessfull"""
    headers = {"Content-Type": "application/json", "x-api-key": conf.AWS_API_KEY}
    try:
        response = requests.post(
            conf.AWS_API_URL, json=data, headers=headers, timeout=5
        )
        if response.status_code == 200:
            print("Successfully uploaded to AWS.")
            return True
        else:
            print(f"AWS upload failed: {response.status_code} {response.text}")
    except Exception as e:
        print(f"Error uploading to AWS: {e}")

    add_to_failed_queue("aws", data)
    return False


# === STORE IN MYSQL DATABASE ===
def insert_to_mysql(data):
    """return True if sucessfull"""
    try:
        connection = mysql.connector.connect(**conf.MYSQL_CONFIG)
        cursor = connection.cursor()
        query = """
        INSERT INTO sensor_readings (sensor_id, temp_fahrenheit, temp_celsius, processed_at)
        VALUES (%s, %s, %s, %s)
        """
        cursor.execute(
            query,
            (
                data.get("sensor_id"),
                data.get("temp_fahrenheit"),
                data.get("temp_celsius"),
                data.get("processed_at"),
            ),
        )
        connection.commit()

        print("Data inserted into MySQL database.")
        return True
    except Error as e:
        print(f"MySQL error: {e}")
        add_to_failed_queue("mysql", data)
        return False
    finally:
        if "connection" in locals() and connection.is_connected():
            cursor.close()
            connection.close()


# === NOTIFY LOCAL TORNADO SERVER ===
def notify_local_server():
    notification = '{"note" = ":)"}'
    try:
        response = requests.post(conf.TORNADO_NOTIFY_URL, json=notification, timeout=3)
        if response.status_code == 200:
            print("Local Tornado server notified.")
        else:
            print(f"Tornado server notification failed: {response.status_code}")
    except Exception as e:
        print(f"Error notifying Tornado server: {e}")


# === MQTT CALLBACKS ===
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected securely to MQTT broker.")
        client.subscribe(conf.MQTT_TOPIC)
    else:
        print(f"Failed to connect to MQTT broker, return code {rc}")


def on_disconnect(client, userdata, rc):
    print(f"Disconnected from MQTT broker with code {rc}. Attempting reconnect...")
    reconnect_mqtt(client)


def on_message(client, userdata, msg):
    """When data id added to broker."""
    try:
        payload = msg.payload.decode("utf-8")
        data = json.loads(payload)
        print(f"Received data: {data}")

        process_data(data)

    except Exception as e:
        print(f"Error processing message: {e}")


# === RECONNECTION LOGIC ===
def reconnect_mqtt(client, max_delay=300):
    delay = 1
    while True:
        try:
            print(f"Reconnecting to MQTT broker (waiting {delay}s)...")
            time.sleep(delay)
            client.reconnect()
            print("Reconnected to MQTT broker.")
            return
        except Exception as e:
            print(f"Reconnect failed: {e}")
            delay = min(delay * 2, max_delay)


# === MAIN SCRIPT ===
def main():
    conf.check_files()

    client = mqtt.Client()
    mgtt_username, mqtt_password, mqtt_url, mqtt_port = conf.load_mqtt_credentials()
    client.username_pw_set(mgtt_username, mqtt_password)
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message

    print("Connecting securely to MQTT broker...")

    client.tls_set(
        ca_certs=conf.CA_CERT_PATH,
        cert_reqs=ssl.CERT_REQUIRED,
        tls_version=ssl.PROTOCOL_TLSv1_2,
    )
    client.tls_insecure_set(False)

    while True:
        try:
            client.connect(mqtt_url, mqtt_port, 60)
            client.loop_forever()
        except Exception as e:
            print(f"MQTT connection error: {e}. Reconnecting...")
            reconnect_mqtt(client)


if __name__ == "__main__":
    main()
