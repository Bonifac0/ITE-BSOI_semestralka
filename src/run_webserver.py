from tornado import httpserver, ioloop, web, websocket
import os
import json
import random
import mysql.connector
from datetime import datetime, timedelta, date
import processor_config as conf


INDEX_PATH = os.path.join(os.path.dirname(__file__), "..", "web_resources", "index.html")
CERTIFILE_PATH = "certification/cert.pem"
KEYFILE_PATH = "certification/key.pem"
CA_CERTS = "certification/fullchain.pem"

def get_db_connection():
    conn = mysql.connector.connect(**conf.MYSQL_CONFIG)
    return conn

def json_default(o):
    if isinstance(o, (datetime, date)):
        return o.isoformat()
    raise TypeError("Type %s not serializable" % type(o))

class NewDataHandler(web.RequestHandler):
    def get(self):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        query = ("SELECT team, temperature, humidity, lightness, time FROM test ORDER BY time DESC LIMIT 1")
        cursor.execute(query)
        latest_record = cursor.fetchone()
        cursor.close()
        conn.close()

        if latest_record:
            SensorSocketHandler.broadcast_single_update(latest_record)
        
        self.write({"status": "ok"})


class HistoryDataHandler(web.RequestHandler):
    def get(self):
        time_range = self.get_argument('range', '1h')
        now = datetime.now()
        
        # Define the start time based on the range parameter
        if time_range == '12h':
            start_time = now - timedelta(hours=12)
        elif time_range == '1d':
            start_time = now - timedelta(days=1)
        elif time_range == '7d':
            start_time = now - timedelta(days=7)
        elif time_range == '1m':
            start_time = now - timedelta(days=30)  # Approximation for a month
        else: # Default to 1h
            start_time = now - timedelta(hours=1)

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        if time_range == 'all':
            query = ("SELECT team, temperature, humidity, lightness, time FROM test ORDER BY time ASC")
            cursor.execute(query)
        else:
            query = ("SELECT team, temperature, humidity, lightness, time FROM test WHERE time >= %s ORDER BY time ASC")
            cursor.execute(query, (start_time,))
            
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
        {'id': 1, 'name': 'Blue Team', 'data': {'temperature': 0, 'humidity': 0, 'lightness': 0}, 'status': 'Offline'},
        {'id': 2, 'name': 'Yellow Team', 'data': {'temperature': 0, 'humidity': 0, 'lightness': 0}, 'status': 'Offline'},
        {'id': 3, 'name': 'Green Team', 'data': {'temperature': 0, 'humidity': 0, 'lightness': 0}, 'status': 'Offline'},
        {'id': 4, 'name': 'Red Team', 'data': {'temperature': 0, 'humidity': 0, 'lightness': 0}, 'status': 'Offline'},
        {'id': 5, 'name': 'Black Team', 'data': {'temperature': 0, 'humidity': 0, 'lightness': 0}, 'status': 'Offline'},
    ]
    team_map = {
        'blue': 1,
        'yellow': 2,
        'green': 3,
        'red': 4,
        'black': 5
    }

    def open(self):
        SensorSocketHandler.clients.add(self)
        # On connection, send the current state of all sensors
        initial_message = {
            "type": "full_state",
            "payload": SensorSocketHandler.initial_sensors
        }
        self.write_message(json.dumps(initial_message, default=json_default))

    def on_close(self):
        SensorSocketHandler.clients.remove(self)

    @classmethod
    def broadcast_single_update(cls, record):
        team_name_lower = record['team'].lower()
        sensor_id = cls.team_map.get(team_name_lower)
        
        if sensor_id is not None:
            # Find the sensor in our state and update it
            for sensor in cls.initial_sensors:
                if sensor['id'] == sensor_id:
                    sensor['status'] = 'Online'
                    sensor['data'] = {
                        'temperature': record['temperature'],
                        'humidity': record['humidity'],
                        'lightness': record['lightness'],
                    }
                    # Prepare the message to broadcast
                    update_message = {
                        "type": "update",
                        "payload": sensor
                    }
                    # Broadcast to all clients
                    for client in cls.clients:
                        client.write_message(json.dumps(update_message, default=json_default))
                    break # Exit loop once sensor is found and updated



if __name__ == "__main__":
    print("Server is starting")
    check_files()
    app = web.Application([
        (r"/", RootHandler),
        (r"/websocket", SensorSocketHandler),
        (r"/static/(.*)", web.StaticFileHandler, {"path": os.path.join(os.path.dirname(__file__), "..", "web_resources", "static")}),
        (r"/api/history", HistoryDataHandler),
        (r"/api/newData", NewDataHandler)
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
    ioloop.IOLoop.instance().start()
