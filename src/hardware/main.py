from machine import I2C, Pin
import network
import time
from onewire import OneWire
from ds18x20 import DS18X20
from time import sleep
import dht
import ntptime
import bh1750
from umqtt.simple import MQTTClient


TEAM_NAME = "blue"
BROKER_HOST = "***.***.***.***"
BROKER_PORT = 0000
BROKER_USER = "****"
BROKER_PASS = "****"
TOPIC = b"ite25/" + TEAM_NAME.encode()
PERIOD_S = 60  # publikování každých 60 s
wifi_networks = [("zcu-hub-us", "***"), ("zcu-hub-ui", "***"), ("TP-Link_920B", "***")]


class tempSensorDS:
    def __init__(self, pin_nb):
        self.pin = Pin(pin_nb, Pin.IN)
        self.ow = DS18X20(OneWire(self.pin))
        self.ds_sensor = self.scan()

    def scan(self):
        try:
            return self.ow.scan()[0]
        except IndexError:
            print("ERR: No DS sensors found.")
            exit(1)

    def measure_temp(self, delay=0.75):
        self.ow.convert_temp()
        sleep(delay)
        return self.ow.read_temp(self.ds_sensor)


def connect(ssid, password):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.config(hostname="iteBlueTeam")
    print("Připojuji se k síti", ssid)
    wlan.connect(ssid, password)
    timeout = 5  # 5 sekund timeout
    while timeout > 0:
        if wlan.isconnected():
            print("Síťová konfigurace:", wlan.ifconfig())
            try:
                ntptime.settime()
                print("Čas synchronizován s NTP serverem")
            except:
                print("Chyba při synchronizaci času")
            return
        time.sleep(1)
        timeout -= 1
    print(f"Nepodařilo se připojit k síti {ssid}")


def is_connected():
    wlan = network.WLAN(network.STA_IF)
    return wlan.isconnected()


def disconnect():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(False)
    print("WiFi odpojeno")


def iso_timestamp():
    current_time = time.time()
    y, m, d, hh, mm, ss, wd, yd = time.localtime(current_time)
    micros = time.ticks_us() % 1_000_000
    # YYYY-MM-DDTHH:MM:SS.ffffff
    return "%04d-%02d-%02dT%02d:%02d:%02d.%06d" % (y, m, d, hh, mm, ss, micros)


# 2CCF67EF4C4F
if __name__ == "__main__":
    sensor = tempSensorDS(28)  # GPIO DS18B20 sensoru
    client = MQTTClient(
        TEAM_NAME, BROKER_HOST, port=BROKER_PORT, user=BROKER_USER, password=BROKER_PASS
    )
    for ssid, password in wifi_networks:
        if is_connected():
            try:
                ntptime.settime()
                print("Čas synchronizován s NTP serverem")
            except:
                print("Chyba při synchronizaci času")
            client.connect()
            break
        connect(ssid, password)

    DHT_PIN = 3  # GPIO DHT sensoru
    d = dht.DHT11(Pin(DHT_PIN))
    client.connect()
    i2c = I2C(0, sda=12, scl=13, freq=100_000)  # GPIO pro I2C
    print("I2C scan:", i2c.scan())
    sensor1 = bh1750.BH1750(i2c)  # adresa 0x23
    print("Připojeno k MQTT brokeru")
    payloads = []

    while True:
        time_start = time.time()
        d.measure()
        humidity = d.humidity()
        temperature = sensor.measure_temp()
        luminance = int(sensor1.luminance(bh1750.BH1750.ONCE_HIRES_1))
        print("Teplota:", temperature, "°C")
        print(f"vlhkost:  {humidity} %")
        print("Luminance: %.2f lx" % luminance)

        timestamp = iso_timestamp()
        payload = '{{"team_name":"{}","timestamp":"{}","temperature":{:.2f},"humidity":{:.1f},"illumination":{}}}'.format(
            TEAM_NAME, timestamp, temperature, humidity, luminance
        )
        payloads.append(payload)

        if not is_connected():
            for ssid, password in wifi_networks:
                if is_connected():
                    client.connect()
                    break
                connect(ssid, password)
        else:
            client.connect()
            client.publish(TOPIC, payload)
            payloads.remove(payload)
            pocet = len(payloads)
            if pocet > 30:
                pocet = 30
            i = 0
            for p in payloads:
                i += 1
                print("Odesílám uložené:", p)
                client.publish(TOPIC, p)
                payloads.remove(payloads[0])
                if i == pocet:
                    break
                sleep(0.5)
            print("Odesláno na téma:", TOPIC.decode())

        time_end = time.time()
        elapsed_time = time_end - time_start
        remaining_time = PERIOD_S - elapsed_time
        if remaining_time > 0:
            sleep(remaining_time)
