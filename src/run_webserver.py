from tornado import httpserver, ioloop, web, websocket
import os
import json
import random
import mysql.connector
from datetime import datetime, timedelta, date
import config as conf
import hashlib
import uuid
import cv2
import numpy as np
import base64
from urllib.request import urlopen


def recognize(image_array):
    """
    This function will be implemented by the user.
    It takes a numpy array (the image) and should return a string with the user's name or 'unknown'.
    """
    # For now, it returns a default value.
    print("Placeholder recognize function called.")
    return "unknown"


# --- Hashing Utility ---

INDEX_PATH = os.path.join(
    os.path.dirname(__file__), "..", "web_resources", "index.html"
)
LOGIN_PATH = os.path.join(
    os.path.dirname(__file__), "..", "web_resources", "login.html"
)
CERTIFILE_PATH = "certification/cert.pem"
KEYFILE_PATH = "certification/key.pem"
CA_CERTS = "certification/fullchain.pem"


def get_db_connection():
    conn = mysql.connector.connect(**conf.MYSQL_CONFIG)
    return conn


def json_default(o):
    if isinstance(o, (datetime, date)):
        return o.isoformat()
    if isinstance(o, Decimal):
        return float(o)
    raise TypeError(f"Type {type(o)} not serializable")


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

            query = (
                "SELECT * FROM sessions WHERE session_id = %s AND expires_at > NOW()"
            )
            cursor.execute(query, (session_id.decode(),))
            session = cursor.fetchone()

            if not session:
                return None

            query = "SELECT id, username FROM users WHERE id = %s"
            cursor.execute(query, (session["user_id"],))
            user = cursor.fetchone()
            return user
        finally:
            if "cursor" in locals() and cursor:
                cursor.close()
            if "conn" in locals() and conn.is_connected():
                conn.close()


class NewDataHandler(web.RequestHandler):
    def post(self):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        query = "SELECT team, temperature, humidity, lightness, time FROM test ORDER BY time DESC LIMIT 1"
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

        time_range = self.get_argument("range", "1h")
        now = datetime.now()

        # Define the aggregation interval and start time based on the range parameter
        agg_interval_seconds = None
        if time_range == "12h":
            start_time = now - timedelta(hours=12)
            agg_interval_seconds = 5 * 60  # 5 minutes
        elif time_range == "1d":
            start_time = now - timedelta(days=1)
            agg_interval_seconds = 15 * 60  # 15 minutes
        elif time_range == "7d":
            start_time = now - timedelta(days=7)
            agg_interval_seconds = 60 * 60  # 1 hour
        elif time_range == "1m":
            start_time = now - timedelta(days=30)
            agg_interval_seconds = 6 * 60 * 60  # 6 hours
        elif time_range == "all":
            start_time = None
            agg_interval_seconds = 24 * 60 * 60  # 1 day
        else:  # Default to 1h
            start_time = now - timedelta(hours=1)

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        params = []
        if start_time:
            params.append(start_time)

        if agg_interval_seconds:
            # The query uses integer division on UNIX timestamps to group records into time intervals.
            # It calculates the average for temperature, humidity, and lightness.
            query = f"""
                SELECT
                    team,
                    AVG(temperature) as temperature,
                    AVG(humidity) as humidity,
                    AVG(lightness) as lightness,
                    FROM_UNIXTIME(FLOOR(UNIX_TIMESTAMP(time) / {agg_interval_seconds}) * {agg_interval_seconds}) as time
                FROM test
                {'WHERE time >= %s' if start_time else ''}
                GROUP BY team, FLOOR(UNIX_TIMESTAMP(time) / {agg_interval_seconds})
                ORDER BY time ASC
            """
        else:
            query = "SELECT team, temperature, humidity, lightness, time FROM test WHERE time >= %s ORDER BY time ASC"

        cursor.execute(query, tuple(params))
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

        if user and user["password_hash"] == hash_password(password):
            session_id = str(uuid.uuid4())
            expires_at = datetime.now() + timedelta(days=7)

            insert_query = "INSERT INTO sessions (session_id, user_id, expires_at) VALUES (%s, %s, %s)"
            cursor.execute(insert_query, (session_id, user["id"], expires_at))
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
    team_map = {"blue": 1, "yellow": 2, "green": 3, "red": 4, "black": 5}

    def open(self):
        SensorSocketHandler.clients.add(self)

        # Query DB for the last 3 minutes of data to send as initial state
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        three_minutes_ago = datetime.now() - timedelta(minutes=3)
        query = "SELECT team, temperature, humidity, lightness, time FROM test WHERE time >= %s ORDER BY time ASC"
        cursor.execute(query, (three_minutes_ago,))
        results = cursor.fetchall()
        cursor.close()
        conn.close()

        # The initial message contains all data points from the last 3 minutes
        initial_message = {"type": "initial_data", "payload": results}
        self.write_message(json.dumps(initial_message, default=json_default))

    def on_close(self):
        SensorSocketHandler.clients.remove(self)

    @classmethod
    def broadcast_single_update(cls, record):
        # This method now just formats the DB record and broadcasts it.
        team_name_lower = record["team"].lower()
        sensor_id = cls.team_map.get(team_name_lower)

        if sensor_id is not None:
            # The payload is the raw record from the DB, plus the sensor ID.
            payload = {
                "id": sensor_id,
                "team": record["team"],
                "time": record["time"],
                "data": {
                    "temperature": record["temperature"],
                    "humidity": record["humidity"],
                    "lightness": record["lightness"],
                },
            }
            update_message = {"type": "update", "payload": payload}

            for client in cls.clients:
                client.write_message(json.dumps(update_message, default=json_default))


class FaceLoginHandler(BaseHandler):
    def post(self):
        try:
            body = json.loads(self.request.body)
            image_data_url = body["image"]
            typed_username = body["username"]
        except (json.JSONDecodeError, KeyError):
            self.set_status(400)
            self.write({"error": "Invalid request format"})
            return

        try:
            # Decode the base64 image
            header, encoded = image_data_url.split(",", 1)
            image_bytes = base64.b64decode(encoded)

            # Convert to numpy array
            nparr = np.frombuffer(image_bytes, np.uint8)
            image_array = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        except Exception as e:
            self.set_status(400)
            self.write({"error": f"Could not process image data: {e}"})
            return

        # Call the placeholder recognition function
        recognized_name = recognize(image_array)

        # Check if recognition was successful and matches the typed username
        if (
            recognized_name != "unknown"
            and recognized_name.lower() == typed_username.lower()
        ):
            # Successful login, create session
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            query = "SELECT * FROM users WHERE username = %s"
            cursor.execute(query, (typed_username,))
            user = cursor.fetchone()

            if user:
                session_id = str(uuid.uuid4())
                expires_at = datetime.now() + timedelta(days=7)

                insert_query = "INSERT INTO sessions (session_id, user_id, expires_at) VALUES (%s, %s, %s)"
                cursor.execute(insert_query, (session_id, user["id"], expires_at))
                conn.commit()

                self.set_secure_cookie("session_id", session_id, expires_days=7)
                self.write({"status": "success"})
            else:
                self.set_status(401)
                self.write({"error": "User not found in database"})

            cursor.close()
            conn.close()
        else:
            # Failed login
            self.set_status(401)
            self.write({"error": "Face not recognized or does not match username"})


if __name__ == "__main__":
    print("Server is starting")
    check_files()
    app = web.Application(
        [
            (r"/", RootHandler),
            (r"/login", LoginRenderHandler),
            (r"/login_action", LoginActionHandler),
            (r"/logout", LogoutHandler),
            (r"/api/face_login", FaceLoginHandler),
            (r"/websocket", SensorSocketHandler),
            (
                r"/static/(.*)",
                web.StaticFileHandler,
                {
                    "path": os.path.join(
                        os.path.dirname(__file__), "..", "web_resources", "static"
                    )
                },
            ),
            (r"/api/history", HistoryDataHandler),
            (r"/api/newData", NewDataHandler),
        ],
        cookie_secret=conf.COOKIE_CONFIG,
    )
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
