import requests
import json


import aws_handler as aws
import processor_config as conf
from mariadb_handler import mariaDB_handler


class PROCESSOR:  # :}
    def __init__(self) -> None:
        self.mariaDB = mariaDB_handler()

    def terminarot(self):
        """Hasta La vista, baby
        Close all things that need to be closed."""
        self.mariaDB.close()

    def process_data(self, msg):
        """
        message structure:
        {'team_name': string, 'timestamp': string, 'temperature': float, 'humidity': float, 'illumination': float}

        e.g.: {'team_name': 'white', 'timestamp': '2020-03-24T15:26:05.336974', 'temperature': 25.72, 'humidity': 64.5, 'illumination': 1043}
        """
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
        except ValueError as e:
            print("mqtt massage is not json")
            print(msg)
            print(e)

        self.mariaDB.insert_to_mariadb(payload)

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

        self.notify_local_server()

    def notify_local_server(self):
        """NOTIFY LOCAL TORNADO SERVER"""
        notification = '{"note" = ":)"}'
        try:
            response = requests.post(
                conf.TORNADO_NOTIFY_URL, json=notification, timeout=3
            )
            if response.status_code == 200:
                print("Local Tornado server notified.")
            else:
                print(f"Tornado server notification failed: {response.status_code}")
        except Exception as e:
            print(f"Error notifying Tornado server: {e}")
