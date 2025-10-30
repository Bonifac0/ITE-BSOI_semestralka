import requests
import re
import ast  # json module is not enough


import aws_handler as aws
import processor_config as conf
from mariadb_handler import mariaDB_handler


class PROCESSOR:  # :}
    VALID_TEAMS = {"yellow", "black", "red", "blue", "green"}
    TIMESTAMP_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?$")

    def __init__(self) -> None:
        self.mariaDB = mariaDB_handler()

    def terminarot(self):
        """Hasta La vista, baby.
        Close all things that need to be closed."""
        self.mariaDB.close()

    def process_data(self, msg: str):
        """
        MAIN PROCESSING FUNCTION

        message structure:
        {'team_name': string, 'timestamp': string, 'temperature': float, 'humidity': float, 'illumination': float}

        e.g.: {'team_name': 'white', 'timestamp': '2020-03-24T15:26:05.336974', 'temperature': 25.72, 'humidity': 64.5, 'illumination': 1043}
        """
        try:
            payload: dict = ast.literal_eval(msg)  # json.loads() is too weak
        except ValueError as e:
            print("Mqtt massage is not json")
            print(msg)
            print(e)
            return False

        if not self.validate_input(payload):
            print("Data validation failed, skipping.")
            return False

        self.mariaDB.insert_to_mariadb(payload)  # send to our database

        if payload["team_name"] == "blue":
            aws.send_to_aws(payload)

        # self.notify_local_server()

        return True

    @staticmethod
    def validate_input(inp: dict) -> bool:
        """
        Validates input data.
        Suported format:
        {
            "team_name": string,
            "timestamp": string,
            "temperature": float,
            optional: "humidity": float,
            optional: "illumination": float,
        }
        """
        required = {"team_name", "timestamp", "temperature"}
        missing = required - inp.keys()
        if missing:
            print(f"Missing required keys: {missing}")
            return False

        if inp["team_name"] not in PROCESSOR.VALID_TEAMS:
            print(f"Invalid team name: {inp['team_name']}")
            return False

        # timestamp format check (simple ISO8601 validation)
        if not PROCESSOR.TIMESTAMP_REGEX.match(inp["timestamp"]):
            print(f"Invalid timestamp format: {inp['timestamp']}")
            return False

        try:
            float(inp["temperature"])
        except (ValueError, TypeError):
            print(f"Invalid temperature value: {inp['temperature']}")
            return False

        for key in ["humidity", "illumination"]:
            if key in inp and inp[key] is not None:
                try:
                    float(inp[key])
                except (ValueError, TypeError):
                    print(f"Invalid {key} value: {inp[key]}")
                    return False

        return True

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


if __name__ == "__main__":  # for testing
    val = "{'team_name': 'blue', 'timestamp': '2020-03-24T15:26:05.336974', 'temperature': 20.72, 'humidity': 64.5, 'illumination': 1043}"

    processor = PROCESSOR()
    processor.process_data(val)
