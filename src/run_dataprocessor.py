import time
import paho.mqtt.client as mqtt
import config as conf

from processing_fcn import PROCESSOR
from logger import log


# === MQTT CALLBACKS ===
# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc, properties):
    if rc == 0:
        client.subscribe(conf.MQTT_TOPIC)
        log("Waiting for massage from publicher", category="MQTT")
    else:
        log(
            f"Failed to connect to MQTT broker, return code {rc}",
            level="ERROR",
            category="MQTT",
        )


# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    """When data id added to broker."""
    try:
        if msg.topic not in conf.VALID_TOPICS:
            log(f"Invalid topic: {msg.topic}", category="MQTT")
            return
        payload = msg.payload.decode("utf-8")  # type: ignore
        log(f"MQTT received data: {payload}", category="MQTT")

        processor.process_data(payload)

    except Exception as e:
        log(f"Error processing message: {e}", level="ERROR", category="MQTT")


def reconnect_mqtt(client, max_delay=300):
    delay = 1
    while True:
        try:
            log(f"Reconnecting to MQTT broker (waiting {delay}s)...", category="MQTT")
            time.sleep(delay)
            client.reconnect()
            log("Reconnected to MQTT broker.", category="MQTT")
            return
        except Exception as e:
            log(f"Reconnect failed: {e}", level="ERROR", category="MQTT")
            delay = min(delay * 2, max_delay)


# === MAIN SCRIPT ===
def main():
    conf.check_files()

    # MQTT===
    client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)  # type: ignore
    client.on_connect = on_connect
    client.on_message = on_message
    client.username_pw_set(conf.BROKER_UNAME, password=conf.BROKER_PASSWD)

    while True:
        try:
            client.connect(conf.BROKER_IP, conf.BROKER_PORT, 60)
            client.loop_forever()
        except Exception as e:
            log(f"Mqtt connection lost: {e}", level="ERROR", category="MQTT")
            reconnect_mqtt(client)


# MAIN ENTERY POINT
if __name__ == "__main__":
    log("=====DATAPROCESSOR STRARTING=====")
    processor = PROCESSOR()
    try:
        main()
    finally:
        processor.terminarot()
