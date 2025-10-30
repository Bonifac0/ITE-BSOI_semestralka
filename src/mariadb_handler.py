from mysql.connector import Error
import mysql.connector
import re
import processor_config as conf


class mariaDB_handler:
    VALID_TEAMS = {"yellow", "black", "red", "blue", "green"}
    TIMESTAMP_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?$")

    def __init__(self):
        self.MARIADB_CONNECTION = mysql.connector.connect(**conf.MYSQL_CONFIG)
        self.CURSOR = self.MARIADB_CONNECTION.cursor()

    def close(self):
        """Safely close cursor and database connection."""
        try:
            if self.CURSOR:
                self.CURSOR.close()
                self.CURSOR = None
            if self.MARIADB_CONNECTION and self.MARIADB_CONNECTION.is_connected():
                self.MARIADB_CONNECTION.close()
                self.MARIADB_CONNECTION = None
            print("MariaDB connection closed.")
        except Error as e:
            print(f"Error closing MariaDB connection: {e}")

    @staticmethod
    def __validate_input(inp: dict) -> bool:
        """Validates input data before SQL insertion."""
        required = {"team_name", "timestamp", "temperature"}
        missing = required - inp.keys()
        if missing:
            print(f"Missing required keys: {missing}")
            return False

        if inp["team_name"] not in mariaDB_handler.VALID_TEAMS:
            print(f"Invalid team name: {inp['team_name']}")
            return False

        # timestamp format check (simple ISO8601 validation)
        if not mariaDB_handler.TIMESTAMP_REGEX.match(inp["timestamp"]):
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

    @staticmethod
    def __value_to_sql(inp: dict):
        """Return parameterized SQL and params tuple."""
        sql = (
            "INSERT INTO test (team, temperature, humidity, lightness, time) "
            "VALUES (%s, %s, %s, %s, %s)"
        )
        params = (
            inp["team_name"],
            float(inp["temperature"]),
            float(inp["humidity"]) if inp.get("humidity") is not None else None,
            float(inp["illumination"]) if inp.get("illumination") is not None else None,
            inp["timestamp"],
        )
        return sql, params

    def insert_to_mariadb(self, data: dict) -> bool:
        """Insert a validated record into MariaDB."""
        try:
            if not self.__validate_input(data):
                print("Data validation failed, skipping insert.")
                return False

            sql, params = self.__value_to_sql(data)
            self.CURSOR.execute(sql, params)
            self.MARIADB_CONNECTION.commit()

            print("Record inserted successfully.")
            return True

        except Error as e:
            print(f"Database Error: {e}")
            # TODO call reconect function

            # tmp
            return False
