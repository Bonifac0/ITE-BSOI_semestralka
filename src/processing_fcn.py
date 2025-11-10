import requests
import ast  # json module is not enough


import aws_handler as aws
import config as conf
from mariadb_handler import mariaDB_handler
from logger import log


class PROCESSOR:  # :}
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
            log(f"Mqtt massage is not json, msg: {msg}\n{e}", level="ERROR")
            return False

        if not self.validate_input(payload):
            log(
                "Data validation failed, skipping.",
                level="WARNING",
                category="VALIDATOR",
            )
            return False

        self.mariaDB.insert_to_mariadb(payload)  # send to our database

        if payload["team_name"] == "blue":
            aws.send_to_aws(payload)

        self.notify_local_server(payload)

        log("Waiting for next massage")
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
            log(
                f"Missing required keys: {missing}",
                level="WARNING",
                category="VALIDATOR",
            )
            return False

        if inp["team_name"] not in conf.VALID_TEAMS:
            log(
                f"Invalid team name: {inp['team_name']}",
                level="WARNING",
                category="VALIDATOR",
            )
            return False

        # timestamp format check (simple ISO8601 validation)
        if not conf.TIMESTAMP_REGEX.match(inp["timestamp"]):
            log(
                f"Invalid timestamp format: {inp['timestamp']}",
                level="WARNING",
                category="VALIDATOR",
            )
            return False

        try:
            float(inp["temperature"])
        except (ValueError, TypeError):
            log(
                f"Invalid temperature value: {inp['temperature']}",
                level="WARNING",
                category="VALIDATOR",
            )
            return False

        for key in ["humidity", "illumination"]:
            if key in inp and inp[key] is not None:
                try:
                    float(inp[key])
                except (ValueError, TypeError):
                    log(
                        f"Invalid {key} value: {inp[key]}",
                        level="WARNING",
                        category="VALIDATOR",
                    )
                    return False

        return True

    def notify_local_server(self, payload):
        """NOTIFY LOCAL TORNADO SERVER"""
        try:
            response = requests.post(conf.TORNADO_NOTIFY_URL, json=payload, timeout=3)
            if response.status_code == 200:
                log("Local Tornado server notified.", category="TORNADO")
            else:
                log(
                    f"Tornado server notification failed: {response.status_code}",
                    level="WARNING",
                    category="TORNADO",
                )
        except Exception as e:
            log(
                f"Error notifying Tornado server: {e}",
                level="ERROR",
                category="TORNADO",
            )


if __name__ == "__main__":  # for testing
    val = "{'team_name': 'blue', 'timestamp': '2020-03-24T15:26:05.336974', 'temperature': 20.72, 'humidity': 64.5, 'illumination': 1043}"

    processor = PROCESSOR()
    processor.process_data(val)
