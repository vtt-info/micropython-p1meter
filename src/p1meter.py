import binascii
import uasyncio as asyncio
from machine import UART
import ure as re
import ujson as json

# ------------------------
# decode bytearray
# ------------------------
def decode(a:bytearray):
    "bytearray to string"
    return binascii.hexlify(a).decode()


#####################################################
# MQTT Stuff
#####################################################

from micropython import const
import time
import ubinascii
import machine
from umqtt.simple import MQTTClient
from machine import Pin


# Default MQTT server to connect to
SERVER = "192.168.1.99"
CLIENT_ID = b'p1_meter_'+ubinascii.hexlify(machine.unique_id())
TOPIC = b"p1_meter"
mqtt_client = None

async def ensure_mqtt_connected(server = SERVER):
    #todo: refactor to class to get rid of global
    global mqtt_client
    while True:
        if mqtt_client == None:
            mqtt_client  = MQTTClient(CLIENT_ID, server , user='jos', password='Passport')
        if mqtt_client.sock == None:
            print("connecting to mqtt server {0}".format(server))
            mqtt_client.connect()
            print("Connected")
        # check 
        await asyncio.sleep(30)



#####################################################
#
#####################################################
t : dict = None
async def publish_meters(telegram: dict):
    t = telegram
    if telegram['meters']:
        print("{} meters found".format(len(telegram['meters'])))

        if 1:
            #write meters as json 
            topic = TOPIC + b"/json"
            try:
                mqtt_client.publish(topic, json.dumps(telegram['meters'])) 
            except BaseException as error:  
                print("Error: sending to MQTT : {}".format(error) )
                #todo: flag reinit of MQTT client 

        #write meters 1 by one 
        for meter in telegram['meters']:
            topic = TOPIC + b"/"+ meter['meter'].encode()
            try:
                mqtt_client.publish(topic, meter['reading']) 
            except BaseException as error:  
                print("Error: sending to MQTT : {}".format(error) )
                #todo: flag reinit of MQTT client 
    return

#####################################################
async def receiver(uart_rx: UART):
    sreader = asyncio.StreamReader(uart_rx)
    #start with an empty telegram, explicit to avoid references 
    # possible solution : copy.deepcopy(dict1) not on micropython
    # copy by hydrate from json ?
    # create class -- TMO 

    tele = {'header': '', 'data': [], 'meters': [],  'footer': ''}
    while True:
        line = await sreader.readline()
        # print("raw:", line)
        if line:
            # to string and remove last character : \n
            try:
                line = line.decode()
                line = line[:-1]
            except BaseException as error:  # pylint: disable=unused-variable
                line = "--noise--"
            # print("clean", line)
            if line[0] == '/':
                print('header found')
                tele = {'header': '', 'data': [], 'meters': [],  'footer': ''}

            elif line[0] == '!':
                print('footer found')
                tele['footer'] = line
                # todo: -check CRC 
                await publish_meters(tele)
                # publish_meters(tele)

            elif line != "--noise--":
                tele['data'].append(line)
                # split data into meters
                out = re.match('(.*?)\((.*)\)', line)
                if out:
                    lineinfo = {'meter': out.group(1), 'reading':None, 'unit': None}

                    reading = out.group(2).split('*')
                    if len(reading) == 2:
                        lineinfo['reading'] = reading[0]
                        lineinfo['unit'] = reading[1]
                    else:
                        lineinfo['reading'] = reading[0]
                    print(lineinfo)
                    tele['meters'].append(lineinfo )
    



