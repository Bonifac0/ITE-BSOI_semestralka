import os

TORNADO_NOTIFY_URL = "http://localhost:8888/notify"

# Failed queue======
FAILED_QUEUE_FILE = "failed_queue.json"
# - If the file doesn't exist, it will be created.
# - If the file exists, its contents will be cleared.
with open(FAILED_QUEUE_FILE, "w") as f:
    pass

# AWS==============
AWS_API_URL = "https://your-api.execute-api.us-east-1.amazonaws.com/prod/data"
AWS_API_KEY = "YOUR_AWS_API_KEY"

CA_CERT_PATH = "credentials/ca.crt"


# MySQL============
def load_mysql_credentials():
    username, password = None, None
    with open(MYSQL_CREDENTIALS_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if line.startswith("username="):
                username = line.split("=", 1)[1].strip()
            elif line.startswith("password="):
                password = line.split("=", 1)[1].strip()

    if not username or not password:
        raise ValueError(
            """Credentials file must contain something like:
            username=franta
            password=123"""
        )
    return username, password


MYSQL_CREDENTIALS_FILE = "credentials/credentials_mysql.txt"
user, passwd = load_mysql_credentials()

MYSQL_CONFIG = {
    "host": "localhost",
    "user": user,
    "password": passwd,
    "database": "sensor_data",
}


# MQTT==============
MQTT_CREDENTIALS_FILE = "credentials/credentials_mqtt.txt"
MQTT_TOPIC = "sensors/temperature"


def load_mqtt_credentials():
    username, password, url, port = None, None, None, None
    with open(MQTT_CREDENTIALS_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if line.startswith("username="):
                username = line.split("=", 1)[1].strip()
            elif line.startswith("password="):
                password = line.split("=", 1)[1].strip()
            elif line.startswith("broker_url="):
                url = line.split("=", 1)[1].strip()
            elif line.startswith("port="):
                port = int(line.split("=", 1)[1].strip())

    if not username or not password or not url or not port:
        raise ValueError(
            """Credentials file must contain something like:
            username=franta
            password=123
            broker_url=mqtt.example.com
            port=8883"""
        )
    return username, password, url, port


def check_files():
    files_to_check = [
        MQTT_CREDENTIALS_FILE,
        MYSQL_CREDENTIALS_FILE,
        CA_CERT_PATH,
        FAILED_QUEUE_FILE,
    ]
    for path in files_to_check:
        if not os.path.isfile(path):
            raise FileNotFoundError(f"File '{path}' does not exist.")
