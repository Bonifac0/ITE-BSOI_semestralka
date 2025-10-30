import time
import paho.mqtt.client as mqtt
import processor_config as conf

from processing_fcn import PROCESSOR


# === MQTT CALLBACKS ===
# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc, properties):
    if rc == 0:
        print("Connected to MQTT broker.")
        client.subscribe(conf.MQTT_TOPIC)
        print("Waiting for massage from publicher")
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

        processor.process_data(payload)

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


if __name__ == "__main__":
    processor = PROCESSOR()
    try:
        main()
    finally:
        processor.terminarot()
