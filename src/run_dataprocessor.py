import json
import time
import ssl
import requests
import paho.mqtt.client as mqtt
import mysql.connector
from mysql.connector import Error
import processor_config as conf
import aws_handler as aws


# === PROCESSING FUNCTION ===
def process_data(data):
    massage = {
        "type": conf.EP_MEASUREMENTS,
        "sensor": conf.SENS_HUMI_UUID,
        "value": 1212,
        "timestamp": "pul ctvrta",
    }
    aws.upload_to_aws(massage)
    insert_to_mysql(data)
    notify_local_server()

    aws.retry_failed_tasks()


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
