from tornado import httpserver, ioloop, web, websocket
import os
import json
import random
from faceid.recognize import Recognizer
import mysql.connector
from datetime import datetime, timedelta, date, timezone
import config as conf
import hashlib
import uuid
import cv2
import numpy as np
import base64
from urllib.request import urlopen
from decimal import Decimal


rec = Recognizer()


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
        try:
            # Parse the JSON payload from the request body
            payload = json.loads(self.request.body)
            print("Received payload:", payload)
            team_name = payload.get('team_name')
            timestamp_str = payload.get('timestamp')
            temperature = payload.get('temperature')
            humidity = payload.get('humidity')
            illumination = payload.get('illumination')

            # Basic validation for presence of all required fields
            # team_name, timestamp, temperature are still required
            if not all([team_name, timestamp_str, temperature is not None]):
                self.set_status(400)
                self.write({"error": "Missing required data in payload. Required: team_name, timestamp, temperature."})
                return

            # Convert timestamp string to datetime object
            try:
                # Assuming ISO format (e.g., "YYYY-MM-DDTHH:MM:SS" or "YYYY-MM-DD HH:MM:SS")
                dt_obj = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                # If the incoming timestamp is naive (no timezone), assume it's UTC and make it aware.
                if dt_obj.tzinfo is None:
                    dt_obj = dt_obj.replace(tzinfo=timezone.utc)
                timestamp = dt_obj
            except ValueError:
                self.set_status(400)
                self.write({"error": f"Invalid timestamp format: '{timestamp_str}'. Expected ISO format (e.g., YYYY-MM-DDTHH:MM:SS)."})
                return

            # Construct the record in the format expected by broadcast_single_update
            record = {
                "team": team_name,
                "time": timestamp,
                "temperature": float(temperature),
                "humidity": float(humidity) if humidity is not None else None, # Make optional
                "lightness": float(illumination) if illumination is not None else None, # Make optional
            }
            print("Processed record for broadcasting:", record)
            # Broadcast the received data to all connected WebSocket clients
            SensorSocketHandler.broadcast_single_update(record)

            self.write({"status": "ok"})

        except json.JSONDecodeError:
            self.set_status(400)
            self.write({"error": "Invalid JSON payload. Ensure the request body is valid JSON."})
        except Exception as e:
            # Catch any other unexpected errors
            self.set_status(500)
            self.write({"error": f"An internal server error occurred: {str(e)}"})


class HistoryDataHandler(BaseHandler):
    def get(self):
        if not self.get_current_user():
            self.set_status(403)
            self.write({"error": "Forbidden"})
            return

        time_range = self.get_argument("range", "1h")
        now = datetime.now(timezone.utc)

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
            # Convert aware datetime to naive datetime in UTC for the DB driver
            params.append(start_time.replace(tzinfo=None))

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
                FROM prod
                {'WHERE time >= %s' if start_time else ''}
                GROUP BY team, FLOOR(UNIX_TIMESTAMP(time) / {agg_interval_seconds})
                ORDER BY time ASC
            """
        else:
            query = "SELECT team, temperature, humidity, lightness, time FROM prod WHERE time >= %s ORDER BY time ASC"

        cursor.execute(query, tuple(params))
        results = cursor.fetchall()

        # Format numerical values and fix timezones
        for record in results:
            if 'time' in record and record['time'] and record['time'].tzinfo is None:
                record['time'] = record['time'].replace(tzinfo=timezone.utc)
            if 'temperature' in record and record['temperature'] is not None:
                record['temperature'] = round(float(record['temperature']), 2)
            if 'humidity' in record and record['humidity'] is not None:
                record['humidity'] = round(float(record['humidity']), 1)
            if 'lightness' in record and record['lightness'] is not None:
                record['lightness'] = int(round(float(record['lightness']), 0))


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
        three_minutes_ago = datetime.now(timezone.utc) - timedelta(minutes=3)
        query = "SELECT team, temperature, humidity, lightness, time FROM prod WHERE time >= %s ORDER BY time ASC"
        cursor.execute(query, (three_minutes_ago,))
        results = cursor.fetchall()
        cursor.close()
        conn.close()

        # Make all time objects timezone-aware before sending
        for record in results:
            if 'time' in record and record['time'] and record['time'].tzinfo is None:
                record['time'] = record['time'].replace(tzinfo=timezone.utc)

        print("Sending initial data:", results)
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
            print("Broadcasting update:", update_message)
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
        recognized_name = rec.recognize(image_array)

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
