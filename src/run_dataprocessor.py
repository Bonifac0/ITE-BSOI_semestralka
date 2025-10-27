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
    # message structure:
    # {'team_name': string, 'timestamp': string, 'temperature': float, 'humidity': float, 'illumination': float}

    # e.g.: {'team_name': 'white', 'timestamp': '2020-03-24T15:26:05.336974', 'temperature': 25.72, 'humidity': 64.5, 'illumination': 1043}

    insert_to_mariadb(data)

    sensor = conf.SENS_HUMI_UUID
    value = 1212
    timestamp = "pul ctvrta"

    massage = {
        "sensor": sensor,
        "value": value,
        "timestamp": timestamp,
    }
    aws.measurement_to_aws(massage)

    if aws.is_alerting(massage):  # podminka pro poslani alertu
        aws.alert_to_aws(massage)

    aws.retry_failed_tasks()

    notify_local_server()


# === STORE IN MYSQL DATABASE ===
def value_to_sql(inp: dict) -> str:
    # input:
    # {'team_name': string, 'timestamp': string, 'temperature': float, 'humidity': float, 'illumination': float}
    # output:
    # (
    # "INSERT INTO test (team, temperature, humidity, lightness, time) "
    # f"VALUES ({team_id}, {new_temp}, {new_hum}, {new_light}, '{time_str}');"
    # )
    return ""


def insert_to_mariadb(data):
    """Executes a list of SQL statements in a single transaction."""
    # input
    # list(dict in form of mqtt return)

    try:
        for sql in data:
            cmd = value_to_sql(sql)
            CURSOR.execute(cmd)

        # Commit the transaction to make the changes permanent
        MARIADB_CONNECTION.commit()
        print(
            f"SUCCESS: Successfully inserted {len(data)} records into the 'test' table."
        )
        return True

    except Error as e:
        print(f"Database Error occurred: {e}")
        # TODO call reconect function

        # tmp
        return False


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
# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    """
    print("Connected with result code " + str(rc))

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe(conf.MQTT_TOPIC)
    """
    if rc == 0:
        print("Connected securely to MQTT broker.")
        client.subscribe(conf.MQTT_TOPIC)
    else:
        print(f"Failed to connect to MQTT broker, return code {rc}")


# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    """When data id added to broker."""
    try:
        if msg.payload == "Q":
            client.disconnect()  # dont know if we want this
        payload = msg.payload.decode("utf-8")
        print(f"MQTT received data: {payload}")

        # ite25/practise/blue

        process_data(msg)

    except Exception as e:
        print(f"Error processing message: {e}")


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

    # MQTT===
    client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    client.username_pw_set(conf.BROKER_UNAME, password=conf.BROKER_PASSWD)

    while True:
        try:
            client.connect(conf.BROKER_IP, conf.BROKER_PORT, 60)
            client.loop_forever()
        except Exception as e:
            print(f"MQTT connection error: {e}. Reconnecting...")
            reconnect_mqtt(client)
        finally:
            if CURSOR:
                CURSOR.close()
            if MARIADB_CONNECTION and MARIADB_CONNECTION.is_connected():
                MARIADB_CONNECTION.close()


if __name__ == "__main__":
    # global, not pretty tho :(
    MARIADB_CONNECTION = mysql.connector.connect(**conf.MYSQL_CONFIG)
    CURSOR = MARIADB_CONNECTION.cursor()
    main()

# --------------------------------------------
# topic: ite25/<team_name>

# e.g.: ite25/white


# - pokud měříme např. jen teplotu, klíče 'humidity' a 'illumination' ve zprávě nebudou (to je potřeba ošetřit a počítat s tím ve vašich "subscriberech")
