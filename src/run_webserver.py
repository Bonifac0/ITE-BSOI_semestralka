from tornado import httpserver, ioloop, web, websocket
import os
import json
import random
import mysql.connector
from datetime import datetime, timedelta, date
import processor_config as conf
import hashlib
import uuid

INDEX_PATH = os.path.join(os.path.dirname(__file__), "..", "web_resources", "index.html")
LOGIN_PATH = os.path.join(os.path.dirname(__file__), "..", "web_resources", "login.html")
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

def hash_password(password):
    """Hashes a password using SHA256."""
    return hashlib.sha256(password.encode()).hexdigest()

# --- Base Handler for User Authentication ---
class BaseHandler(web.RequestHandler):
    def get_current_user(self):
        session_id = self.get_secure_cookie("session_id")
        if not session_id:
            return None

        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            query = "SELECT * FROM sessions WHERE session_id = %s AND expires_at > NOW()"
            cursor.execute(query, (session_id.decode(),))
            session = cursor.fetchone()
            
            if not session:
                return None

            query = "SELECT id, username FROM users WHERE id = %s"
            cursor.execute(query, (session['user_id'],))
            user = cursor.fetchone()
            return user
        finally:
            if 'cursor' in locals() and cursor:
                cursor.close()
            if 'conn' in locals() and conn.is_connected():
                conn.close()


class NewDataHandler(web.RequestHandler):
    def post(self):
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


class HistoryDataHandler(BaseHandler):
    def get(self):
        if not self.get_current_user():
            self.set_status(403)
            self.write({"error": "Forbidden"})
            return
        
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


class RootHandler(BaseHandler):
    def get(self):
        current_user = self.get_current_user()
        self.render(INDEX_PATH, is_logged_in=(current_user is not None))

class LoginRenderHandler(web.RequestHandler):
    def get(self):
        self.render(LOGIN_PATH, error=None)

class LoginActionHandler(BaseHandler):
    def post(self):
        username = self.get_argument("username")
        password = self.get_argument("password")
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        query = "SELECT * FROM users WHERE username = %s"
        cursor.execute(query, (username,))
        user = cursor.fetchone()

        if user and user['password_hash'] == hash_password(password):
            session_id = str(uuid.uuid4())
            expires_at = datetime.now() + timedelta(days=7)
            
            insert_query = "INSERT INTO sessions (session_id, user_id, expires_at) VALUES (%s, %s, %s)"
            cursor.execute(insert_query, (session_id, user['id'], expires_at))
            conn.commit()
            
            self.set_secure_cookie("session_id", session_id, expires_days=7)
            self.redirect("/")
        else:
            self.render(LOGIN_PATH, error="Invalid username or password")
        
        cursor.close()
        conn.close()

class LogoutHandler(BaseHandler):
    def get(self):
        session_id = self.get_secure_cookie("session_id")
        if session_id:
            conn = get_db_connection()
            cursor = conn.cursor()
            query = "DELETE FROM sessions WHERE session_id = %s"
            cursor.execute(query, (session_id.decode(),))
            conn.commit()
            cursor.close()
            conn.close()
        
        self.clear_cookie("session_id")
        self.redirect("/login")


class SensorSocketHandler(websocket.WebSocketHandler):
    clients = set()
    team_map = {
        'blue': 1, 'yellow': 2, 'green': 3, 'red': 4, 'black': 5
    }

    def open(self):
        SensorSocketHandler.clients.add(self)
        
        # Query DB for the last 3 minutes of data to send as initial state
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        three_minutes_ago = datetime.now() - timedelta(minutes=3)
        query = ("SELECT team, temperature, humidity, lightness, time FROM test WHERE time >= %s ORDER BY time ASC")
        cursor.execute(query, (three_minutes_ago,))
        results = cursor.fetchall()
        cursor.close()
        conn.close()

        # The initial message contains all data points from the last 3 minutes
        initial_message = {
            "type": "initial_data",
            "payload": results
        }
        self.write_message(json.dumps(initial_message, default=json_default))

    def on_close(self):
        SensorSocketHandler.clients.remove(self)

    @classmethod
    def broadcast_single_update(cls, record):
        # This method now just formats the DB record and broadcasts it.
        team_name_lower = record['team'].lower()
        sensor_id = cls.team_map.get(team_name_lower)
        
        if sensor_id is not None:
            # The payload is the raw record from the DB, plus the sensor ID.
            payload = {
                'id': sensor_id,
                'team': record['team'],
                'time': record['time'],
                'data': {
                    'temperature': record['temperature'],
                    'humidity': record['humidity'],
                    'lightness': record['lightness'],
                }
            }
            update_message = {
                "type": "update",
                "payload": payload
            }
            
            for client in cls.clients:
                client.write_message(json.dumps(update_message, default=json_default))



if __name__ == "__main__":
    print("Server is starting")
    check_files()
    app = web.Application([
        (r"/", RootHandler),
        (r"/login", LoginRenderHandler),
        (r"/login_action", LoginActionHandler),
        (r"/logout", LogoutHandler),
        (r"/websocket", SensorSocketHandler),
        (r"/static/(.*)", web.StaticFileHandler, {"path": os.path.join(os.path.dirname(__file__), "..", "web_resources", "static")}),
        (r"/api/history", HistoryDataHandler),
        (r"/api/newData", NewDataHandler),
    ], cookie_secret=conf.COOKIE_CONFIG)
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
