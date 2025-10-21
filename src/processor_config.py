import os

TORNADO_NOTIFY_URL = "http://localhost:8888/notify"

# Failed queue======
FAILED_QUEUE_FILE = "failed_queue.json"
# - If the file doesn't exist, it will be created.
# - If the file exists, its contents will be cleared.
with open(FAILED_QUEUE_FILE, "w") as f:
    pass

# AWS============== (from aimtech guy, dont change)
URI_BASE = "https://ro7uabkugk.execute-api.eu-central-1.amazonaws.com/Prod"
# EP_LOGIN = f"{URI_BASE}/login"
# EP_SENSORS = f"{URI_BASE}/sensors"
EP_MEASUREMENTS = f"{URI_BASE}/measurements"
EP_ALERTS = f"{URI_BASE}/alerts"


def load_aws_credentials():
    username, password = None, None
    with open(AWS_CREDENTIALS_FILE, "r") as f:
        uuid = f.readline()

    if not username or not password:
        raise ValueError(
            """Credentials file must contain something like:
            ca75a253-4f03-4c3d-b150-8bce54792d25"""
        )
    return uuid


AWS_CREDENTIALS_FILE = "credentials/credentials_aws.txt"
HEADERS = {"Content-Type": "application/json", "teamUUID": load_aws_credentials()}
SENS_TEMP_UUID = "43e67eda-67ab-4524-b945-df18cc9d4e44"
SENS_HUMI_UUID = "8548701c-5af7-4d1b-b7ef-1292847ebdc4"
SENS_ILLU_UUID = "5bbc2513-b731-4c18-9548-94129c0351b6"

SENS_MIN_MAX = {
    "43e67eda-67ab-4524-b945-df18cc9d4e44": (-2.0, 23.0),  # temp
    "8548701c-5af7-4d1b-b7ef-1292847ebdc4": (32.0, 77.0),  # humi
    "5bbc2513-b731-4c18-9548-94129c0351b6": (0.0, 4150.0),  # illu
}

""" blue sensors
{
    "id": 68,
    "sensorUUID": "43e67eda-67ab-4524-b945-df18cc9d4e44",
    "name": "sensor21_temperature",
    "location": "Bolevecka 23, Plzen",
    "minTemperature": -2.0,
    "maxTemperature": 23.0,
}
{
    "id": 69,
    "sensorUUID": "8548701c-5af7-4d1b-b7ef-1292847ebdc4",
    "name": "sensor22_humidity",
    "location": "Hálkova 32, Plzeň",
    "minTemperature": 32.0,
    "maxTemperature": 77.0,
}
{
    "id": 70,
    "sensorUUID": "5bbc2513-b731-4c18-9548-94129c0351b6",
    "name": "sensor23_illumination",
    "location": "Luční 180, Plzeň",
    "minTemperature": 0.0,
    "maxTemperature": 4150.0,
}
"""


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
CA_CERT_PATH = "credentials/ca.crt"


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
