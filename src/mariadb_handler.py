from mysql.connector import Error
import mysql.connector
import processor_config as conf


class mariaDB_handler:
    def __init__(self):
        # self.MARIADB_CONNECTION = mysql.connector.connect(**conf.MYSQL_CONFIG)
        # self.CURSOR = self.MARIADB_CONNECTION.cursor()
        pass

    def close(self):
        """Safely close cursor and database connection."""
        try:
            # if self.CURSOR:
            #     self.CURSOR.close()
            #     self.CURSOR = None
            # if self.MARIADB_CONNECTION and self.MARIADB_CONNECTION.is_connected():
            #     self.MARIADB_CONNECTION.close()
            #     self.MARIADB_CONNECTION = None
            print("MariaDB connection closed.")
        except Error as e:
            print(f"Error closing MariaDB connection: {e}")

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
            sql, params = self.__value_to_sql(data)
            # self.CURSOR.execute(sql, params)
            # self.MARIADB_CONNECTION.commit()

            print("Record inserted successfully.")
            return True

        except Error as e:
            print(f"Database Error: {e}")
            # TODO call reconect function

            # tmp
            return False
