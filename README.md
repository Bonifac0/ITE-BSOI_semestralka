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
Entery poin: `src/run_dataprocessor.py`
- Uses:
    - `src/prossing_fcn.py` most of the logick for processing massages
    - `src/mariadb_handler.py` for handling comunication with local running database
    - `src/aws_handler.py` for sending massages to Aimtech rest API
    - `src/config.py` for configuration and global variables
### Webserver (frontend)
Entery poin: `src/run_webserver.py`

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