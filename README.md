# ITE-BSOI_semestralka
Semestral project for KKY/ITE and KKY/BSOI

Team: **Blue**

[**WEBSITE**](https://aether70.zcu.cz/)

## Authors:
- Michal Kolinek (Backend)
- Martin Horesovsky (Frontend)
- Ondrej Cihlar (Hardware)

## Requirements:
- Python 3.11+
- Pip packages in `requirements.txt`
## Prerequisties
- credentials folder in root of project
```
credentials/
├── credentials_aws.txt
|      >69********************d20 (UUID)
├── credentials_cookie.txt
|      >cookie=ht******KI  (hash)
├── credentials_mqtt.txt
|      >username=****
|      >password=****
|      >broker_adress=***.***.***.***
|      >port=****
└── credentials_mysql.txt
       >host=localhost
       >database=sensors
       >username=mqttwrite
       >password=***
```

## Processes
### Dataprocessor (backend)
Entery point: `src/run_dataprocessor.py`
- Uses:
    - `src/prossing_fcn.py` most of the logic for processing messages
    - `src/mariadb_handler.py` for handling comunication with local running database
    - `src/aws_handler.py` for sending messages to Aimtech rest API
    - `src/config.py` for configuration and global variables
### Webserver (frontend)
Entery point: `src/run_webserver.py`
### Raspberry (hardware)
Main program: `main.py`
- measures temperature, humidity, and light intensity, synchronizes time via NTP, connects to Wi-Fi, and periodically publishes sensor data to an MQTT broker in JSON format.
- include class tempSensorDS for temperature measurment
- uses:

    -`simple.py` class MQTTClient for work with mqtt (connection and publish)
    - `bh1750.py` class for work with light sensor

## Hypervisor configuration
Backend:
```
[Unit]
Description=ITE-BSOI Backend
After=network.target

[Service]
WorkingDirectory=/workplace

# Clear logs only on manual start/restart
# ExecStartPre=/usr/bin/truncate -s 0 /workplace/logs/dataprocessor.log
ExecStartPre=/usr/bin/truncate -s 0 /workplace/logs/dataprocessor_error.log

ExecStart=/workplace/venv/bin/python3 -u /workplace/repo/src/run_dataprocessor.py

Restart=always
RestartSec=5

StandardOutput=append:/workplace/logs/dataprocessor.log
StandardError=append:/workplace/logs/dataprocessor_error.log

[Install]
WantedBy=multi-user.target
```
Frontend:
```
[Unit]
Description=ITE-BSOI Backend
After=network.target

[Service]
WorkingDirectory=/workplace

# Clear logs only on manual start/restart
ExecStartPre=/usr/bin/truncate -s 0 /workplace/logs/webserver.log
ExecStartPre=/usr/bin/truncate -s 0 /workplace/logs/webserver_error.log

ExecStart=/workplace/venv/bin/python3 -u /workplace/repo/src/run_webserver.py

Restart=always
RestartSec=5

StandardOutput=append:/workplace/logs/webserver.log
StandardError=append:/workplace/logs/webserver_error.log

[Install]
WantedBy=multi-user.target
```
## Deployment:
- Automatical using github actions on push or merge to main
- More in `.github/workflows/deploy.yml`

# Frontend Functionality & Features

The frontend is a responsive web dashboard built to visualize environmental data from distributed sensor nodes.

### 1. Dashboard Overview
- **Multi-Sensor Monitoring:** Displays real-time status for 5 distinct sensor teams (Blue, Yellow, Green, Red, Black).
- **Live View:**
  - **Real-time Updates:** Utilizes **WebSockets** to push data updates instantly to the client.
  - **Status Indicators:** Sensors are marked as "Online" or "Offline" based on a 5-minute heartbeat threshold.
  - **Visual Alerts:** Data values (Temperature, Humidity, Lightness) change color or glow to indicate out-of-bounds readings.
  - **Detailed Modal:** Clicking a sensor card opens a modal displaying high-resolution data for the last 10 minutes.

### 2. Historical Trends
*Available only to authenticated users.*
- Provides interactive line charts for Temperature, Humidity, and Lightness.
- **Time Ranges:** Supports data visualization over multiple intervals: 1 hour, 12 hours, 1 day, 7 days, 1 month, and All-time.
- **Data Aggregation:** automatically aggregates data points for longer time ranges to ensure performance.

### 3. Authentication
- **Standard Login:** Username and password authentication with client-side and server-side SHA-256 hashing.
- **Face ID Login:** Biometric authentication feature that captures a webcam image and verifies identity against a pre-trained dataset using OpenCV and face recognition models on the backend.

### 4. Tech Stack
- **Backend:** Python (Tornado Web Server)
- **Frontend:** HTML5, Tailwind CSS (Styling), Chart.js (Data Visualization), Vanilla JavaScript.
- **Communication:** Secure WebSockets (WSS) and REST API.

