#!/usr/bin/env python3
import binascii
import struct
import time
from bluepy import btle
from ha_mqtt_discoverable import Settings, DeviceInfo
from ha_mqtt_discoverable.sensors import Sensor, SensorInfo

class MyDelegate(btle.DefaultDelegate):
    def __init__(self):
        btle.DefaultDelegate.__init__(self)

    def handleDiscovery(self, scanEntry, isNewDev, isNewData):
        if isNewDev:
            print("Discovered device", scanEntry.addr)
        elif isNewData:
            print("Received new data from", scanEntry.addr)

    def handleNotification(self, cHandle, data):
        pass

# Configure the required parameters for the MQTT broker
mqtt_settings = Settings.MQTT(host="localhost")

# Define the device. At least one of `identifiers` or `connections` must be supplied
device_info = DeviceInfo(name="AirburgEmoPlus", identifiers="airburg_emo_plus")

# Associate the sensor with the device via the `device` parameter
# `unique_id` must also be set, otherwise Home Assistant will not display the device in the UI
density_sensor_info = SensorInfo(
    name="PM2.5",
    device_class="pm25",
    state_class="measurement",
    icon="mdi:molecule",
    accuracy_decimals=0,
    unit_of_measurement="μg/m³",
    unique_id="airburg_emo_plus_pm2_5_density",
    #object_id="airburg_emo_plus_pm2_5_density",
    device=device_info
)
count_sensor_info = SensorInfo(
    name="PM2.5 Count",
    state_class="measurement",
    icon="mdi:molecule",
    unit_of_measurement="/dL",
    accuracy_decimals=0,
    unique_id="airburg_emo_plus_pm2_5_count",
    object_id="airburg_emo_plus_pm2_5_count",
    device=device_info
)
density_settings = Settings(mqtt=mqtt_settings, entity=density_sensor_info)
density_sensor = Sensor(density_settings)

count_settings = Settings(mqtt=mqtt_settings, entity=count_sensor_info)
count_sensor = Sensor(count_settings)

# scan
# scanner = btle.Scanner().withDelegate(MyDelegate())
# devices = scanner.scan(10.0)

# for dev in devices:
#     print("Device %s(%s), RSSI=%d db" % (dev.addr, dev.addrType, dev.rssi))
#     for (adType, desc, value) in dev.getScanData():
#         print("\t\t", "adType =", adType, ", desc =", desc, ", value =", value)

# service discovery
device = btle.Peripheral().withDelegate(MyDelegate())
device.connect("20:16:09:10:00:96")

#for service in device.getServices():
#    print("service:", service.uuid)
#    for char in service.getCharacteristics():
#        print("\tcharacteristic:", char.uuid, ", properties =", char.propertiesToString())

# for char in device.getCharacteristics():
#     print("characteristic:", char.uuid, 
#         ", properties =", char.propertiesToString())

#service_battery_uuid = "0000180f-0000-1000-8000-00805f9b34fb"

#service_battery = device.getServiceByUUID(service_battery_uuid) 
#char = service_battery.getCharacteristics()
#print(len(char))
#if len(char) == 1:
#    raw_data = char[0].read()
#    print("battery level is %d%%" % struct.unpack('B', raw_data)[0])

service_pm2dot5_uuid = "0000fff0-0000-1000-8000-00805f9b34fb"
service_pm2dot5 = device.getServiceByUUID(service_pm2dot5_uuid)

warm_up_char = service_pm2dot5.getCharacteristics(forUUID="0000fff3-0000-1000-8000-00805f9b34fb")
#print(len(warm_up_char))
raw_data = warm_up_char[0].read()
#print("value is %d" % struct.unpack('B', raw_data)[0])


time.sleep(20)

value_char = service_pm2dot5.getCharacteristics(forUUID="0000fff2-0000-1000-8000-00805f9b34fb")
#print(len(value_char))
value = value_char[0].read()
#print('value=%s' % binascii.b2a_hex(value))
    
c1 = bytes(value[10:12])
c2 = bytes(value[12:14])
#print('c1=%s, c2=%s' % (binascii.b2a_hex(c1), binascii.b2a_hex(c2)))

a = struct.unpack('B', c1[1:])[0]
b = struct.unpack('B', c1[:1])[0]
density = int((b << 8) | (a & 0xff)) * 1.265

a = struct.unpack('B', c2[1:])[0]
b = struct.unpack('B', c2[:1])[0]
count = (int((a & 0xff) << 0) + int((b & 0xff) << 8)) * 2.56
if count < 0:
    count = 0

#print('%d ug/m3, %d 0.3um' % (density, count))
print('{"density": %d, "count": %d}' % (density, count))

density_sensor.set_state("%d" % density)
count_sensor.set_state("%d" % count)

device.disconnect()

