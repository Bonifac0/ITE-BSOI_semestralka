from tornado import httpserver, ioloop, web, websocket
import os
import json
import random
import mysql.connector
from datetime import datetime, timedelta, date


INDEX_PATH = os.path.join(os.path.dirname(__file__), "..", "web_resources", "index.html")
CERTIFILE_PATH = "certification/cert.pem"
KEYFILE_PATH = "certification/key.pem"
CA_CERTS = "certification/fullchain.pem"

def get_db_config():
    cred_path = "/workplace/credentials/credentials_mysql.txt"
    with open(cred_path, 'r') as f:
        lines = f.read().splitlines()
        config = {
            'host': lines[0],
            'database': lines[1],
            'user': lines[2],
            'password': lines[3]
        }
    return config

def get_db_connection():
    conn = mysql.connector.connect(**get_db_config())
    return conn

def json_default(o):
    if isinstance(o, (datetime, date)):
        return o.isoformat()
    raise TypeError("Type %s not serializable" % type(o))

class LastHourDataHandler(web.RequestHandler):
    def get(self):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        one_hour_ago = datetime.now() - timedelta(hours=1)
        query = ("SELECT id, team, temperature, humidity, lightness, time FROM sensor_data WHERE time >= %s")
        cursor.execute(query, (one_hour_ago,))
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        self.write(json.dumps(results, default=json_default))


def check_files():
    files_to_check = [CERTIFILE_PATH, KEYFILE_PATH, CA_CERTS]
    for path in files_to_check:
        if not os.path.isfile(path):
            raise FileNotFoundError(f"File '{path}' does not exist.")


class RootHandler(web.RequestHandler):
    def get(self):
        self.render(INDEX_PATH)


class SensorSocketHandler(websocket.WebSocketHandler):
    clients = set()
    initial_sensors = [
        {'id': 1, 'name': 'Blue Team', 'data': {'temperature': 25.5, 'humidity': 45, 'lightness': 300}, 'status': 'Online'},
        {'id': 2, 'name': 'Yellow Team', 'data': {'temperature': 23.1, 'humidity': 55, 'lightness': 450}, 'status': 'Online'},
        {'id': 3, 'name': 'Green Team', 'data': None, 'status': 'Offline'},
        {'id': 4, 'name': 'Red Team', 'data': {'temperature': 28.9, 'humidity': 40, 'lightness': 600}, 'status': 'Online'},
        {'id': 5, 'name': 'Black Team', 'data': None, 'status': 'Offline'},
    ]

    def open(self):
        SensorSocketHandler.clients.add(self)
        self.write_message(json.dumps(SensorSocketHandler.initial_sensors))

    def on_close(self):
        SensorSocketHandler.clients.remove(self)

    @classmethod
    def send_updates(cls):
        for client in cls.clients:
            client.write_message(json.dumps(cls.generate_sensor_data()))

    @classmethod
    def generate_sensor_data(cls):
        for sensor in cls.initial_sensors:
            if sensor['status'] == 'Online' and sensor['data']:
                sensor['data']['temperature'] += random.uniform(-0.25, 0.25)
                sensor['data']['humidity'] += random.uniform(-0.5, 0.5)
                sensor['data']['lightness'] += random.uniform(-5, 5)
        return cls.initial_sensors


if __name__ == "__main__":
    print("Server is starting")
    check_files()
    app = web.Application([
        (r"/", RootHandler),
        (r"/websocket", SensorSocketHandler),
        (r"/static/(.*)", web.StaticFileHandler, {"path": os.path.join(os.path.dirname(__file__), "..", "web_resources", "static")}),
        (r"/api/last1h", LastHourDataHandler),
    ])
    server = httpserver.HTTPServer(
        app,
        ssl_options={
            "certfile": CERTIFILE_PATH,
            "keyfile": KEYFILE_PATH,
            "ca_certs": CA_CERTS,
        },
    )
    server.listen(443)
    ioloop.PeriodicCallback(SensorSocketHandler.send_updates, 2000).start()
    ioloop.IOLoop.instance().start()
