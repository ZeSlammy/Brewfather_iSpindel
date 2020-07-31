# brewfather craftbeerpi3 plugin
# Log iSpindel temperature, SG and Battery data from CraftBeerPi 3.0 to the brewfather app
# https://brewfather.app/
#
# Note this code is heavily based on the Thingspeak plugin by Atle Ravndal
# and I acknowledge his efforts have made the creation of this plugin possible
# It is also now heavily based on the BrewStat.us and Brewfather modules I've written
#
from modules import cbpi
from thread import start_new_thread
import logging
import requests
import datetime
import json

DEBUG = True
drop_first = None

# Parameters
brewfather_iSpindel_id = None


def log(s):
    if DEBUG:
        s = "brewfather_iSpindel: " + s
        cbpi.app.logger.info(s)


@cbpi.initalizer(order=9000)
def init(cbpi):
    cbpi.app.logger.info("brewfather_iSpindel plugin Initialize")
    log("Brewfather_iSpindel params")
# the unique id value (the bit following id= in the "Cloud URL"
# in the setting screen
    global brewfather_iSpindel_id

    brewfather_iSpindel_id = cbpi.get_config_parameter(
        "brewfather_iSpindel_id", None)
    log("Brewfather brewfather_iSpindel_id %s" % brewfather_iSpindel_id)

    if brewfather_iSpindel_id is None:
        log("Init brewfather_iSpindel config URL")
    try:
        # TODO: is param2 a default value?
        cbpi.add_config_parameter(
            "brewfather_iSpindel_id", "", "text", "Brewfather_iSpindel id")
    except:
        cbpi.notify("Brewfather_iSpindel Error",
                    "Unable to update Brewfather_iSpindel id parameter", type="danger")
    log("Brewfather_iSpindel params ends")

# interval=900 is 900 seconds, 15 minutes, same as the Tilt Android App logs.
# if you try to reduce this, brewfather will throw "ignored" status back at you
@cbpi.backgroundtask(key="brewfather_iSpindel_task", interval=900)
def brewfather_iSpindel_background_task(api):
    log("brewfather_iSpindel background task")
    global drop_first
    if drop_first is None:
        drop_first = False
        return False

    if brewfather_iSpindel_id is None:
        return False
    # Potentially multiple iSpindels
    # Build a list with iSpindel / Temperature / Gravity / Battery
    multi_payload = {}
    for key, value in cbpi.cache.get("sensors").iteritems():
        log("key %s value.name %s value.instance.last_value %s value.type %s" %
            (key, value.name, value.instance.last_value, value.type))

        if (value.type == "iSpindel"):
            log("sensorType %s value.instance.last_value %s " %
                (value.instance.sensorType,    value.instance.last_value))
            iSpindel_name = value.instance.key
            if not(iSpindel_name in multi_payload):
                multi_payload[iSpindel_name] = {}
            if (value.instance.sensorType == "Temperature"):
                temp = value.instance.last_value
                # brewfather expects *F so convert back if we use C
                '''if (cbpi.get_config_parameter("unit",None) == "C"):
                    temp = temp * 1.8 + 32'''
                multi_payload[iSpindel_name]['temperature'] = temp
                # payload['name'] = value.instance.key
                # If Plato then "normal name" else add [SG] at the end
            if (value.instance.unitsGravity == u'SG'):
                multi_payload[iSpindel_name]['name'] = value.instance.key + "[SG]"
                multi_payload[iSpindel_name]['id'] = value.instance.key
            else:
                multi_payload[iSpindel_name]['name'] = value.instance.key
                multi_payload[iSpindel_name]['id'] = value.instance.key
            if (value.instance.sensorType == "RSSI"):
                multi_payload[iSpindel_name]['RSSI'] = value.instance.last_value
            if (value.instance.sensorType == "Battery") and (value.instance.last_value > 0):
                multi_payload[iSpindel_name]['battery'] = value.instance.last_value
            if (value.instance.sensorType == "Gravity") and (value.instance.last_value > 0):
                multi_payload[iSpindel_name]['gravity'] = value.instance.last_value
            multi_payload[iSpindel_name]['angle'] = 22
    log("BrewFather_iSpindel Parsing done")
    for iSpindel, payload in multi_payload.iteritems():
        log("BrewFather_iSpindel %s" % (iSpindel))
        url = "http://log.brewfather.net/ispindel"
        headers = {
            'Content-Type': "application/json",
            'Cache-Control': "no-cache"
        }
        id = cbpi.get_config_parameter("brewfather_iSpindel_id", None)
        querystring = {"id": id}
        log("Payload %s querystring %s" %
            (json.dumps(payload), querystring))
        r = requests.request("POST", url, json=payload,
                             headers=headers, params=querystring)
        log("Result %s" % r.text)
        log("brewfather_iSpindel done")


def get_gravity_from_logs(id):
    try:
        with open('./logs/sensor_' + str(id) + '.log', 'r') as f:
            lines = f.read().splitlines()
            last_line = lines[-1]
            Gravity = last_line.split(",")[1].replace('\n', '')
    except:
        log("Failed to get Gravity")
        Gravity = 0
    return Gravity
