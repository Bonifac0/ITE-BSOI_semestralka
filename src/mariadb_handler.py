from mysql.connector import Error
import mysql.connector


import processor_config as conf


class mariaDB_handler:
    def __init__(self):
        self.MARIADB_CONNECTION = mysql.connector.connect(**conf.MYSQL_CONFIG)
        self.CURSOR = self.MARIADB_CONNECTION.cursor()

    def __value_to_sql(inp) -> str:
        # input:
        # {'team_name': string, 'timestamp': string, 'temperature': float, 'humidity': float, 'illumination': float}
        # {'team_name': 'white', 'timestamp': '2020-03-24T15:26:05.336974', 'temperature': 25.72, 'humidity': 64.5, 'illumination': 1043}
        # output:
        # (
        # "INSERT INTO test (team, temperature, humidity, lightness, time) "
        # f"VALUES ({team_id}, {new_temp}, {new_hum}, {new_light}, '{time_str}');"
        # )
        return ""

    def insert_to_mariadb(self, data):
        """Executes a list of SQL statements in a single transaction."""
        # input
        # list(dict in form of mqtt return)

        try:
            # for sql in data:
            cmd = mariaDB_handler.__value_to_sql(data)
            self.CURSOR.execute(cmd)

            # Commit the transaction to make the changes permanent
            self.MARIADB_CONNECTION.commit()
            return True

        except Error as e:
            print(f"Database Error occurred: {e}")
            # TODO call reconect function

            # tmp
            return False
