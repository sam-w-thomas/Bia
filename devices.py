from kasa import SmartPlug

import asyncio
import csv
from enum import Enum
import uuid
import json
import os

class DeviceType(Enum):
    SMARTPLUG = "SMARTPLUG"
    CISCO_ROUTER = "CISCOROUTER"
    CISCO_SWITCH = "CISCOSWITCH"


class Device:
    def __init__(self, name, address, device_uuid):
        self._uuid = device_uuid
        self._name = name
        self._address = address
        self.type = None

    @classmethod
    def new_device(cls, name, address):
        device_uuid = uuid.uuid4()

        with open(f'data/{device_uuid}.csv', 'w', newline='') as csvfile:
            device_writer = csv.writer(csvfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            device_writer.writerow(['timestamp','power', 'voltage', 'current'])

        return cls(name, address, device_uuid)

    @property
    def uuid(self):
        return self._uuid

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, new_name):
        self.name = new_name
        self.save()

    @property
    def address(self):
        return self._address

    @address.setter
    def address(self, new_name):
        self.name = self._address
        self.save()

    def get_current(self):
        pass

    def get_properties(self):
        pass

    def get_capability(self):
        pass

    def save(self):
        """
        Save device to inventory
        If already exists, overrides type and address

        :return:
        """

        with open('inventory/devices.json', 'r+') as device_file:
            raw_devices = json.load(device_file)

            raw_devices[str(self._uuid)] = {
                'name': self._name,
                'type': self.type.value,
                'address': self._address
            }

            device_file.seek(0)
            json.dump(raw_devices, device_file)
            device_file.truncate()


class SmartPlugDevice(Device):
    def __init__(self, name, address, device_uuid):
        asyncio.set_event_loop(asyncio.SelectorEventLoop())
        Device.__init__(self, name, address, device_uuid)
        self._kasa_device = SmartPlug(self._address)
        self.type = DeviceType.SMARTPLUG

    def get_stats(self):
        return asyncio.get_event_loop().run_until_complete(self.get_plug_stats())

    def get_capability(self):
        return asyncio.get_event_loop().run_until_complete(self.get_cap_stats())

    def get_power(self):
        return self.get_stats()['power']

    def get_voltage(self):
        return self.get_stats()['voltage']

    def get_current(self):
        return self.get_stats()['current']

    def get_properties(self):
        device_stats = self.get_stats()
        return {
            'power': device_stats['power'],
            'voltage': device_stats['voltage'],
            'current': device_stats['power'],
        }

    async def get_plug_stats(self):
        device = self._kasa_device
        await device.update()  # Request an update
        return device.emeter_realtime

    async def get_cap_stats(self):
        device = self._kasa_device
        await device.update()  # Request an update

        cap_stats = {
            'alias': device.alias,
            'model': device.model,
            'rssi': device.rssi,
            'mac': device.mac,
        }

        return {**cap_stats, **device.hw_info}

def get_devices(
        device_id = None
):
    with open('inventory/devices.json') as device_file:
        raw_devices = json.load(device_file)

    # Return single device if device_id supplied
    if device_id:
        device_details = raw_devices[device_id]
        return SmartPlugDevice(device_details['name'], device_details['address'], device_id)


    # Return multiple devices if no device_id supplied
    converted_devices = []
    for device_uuid, device_details in raw_devices.items():
        if device_details['type'] == "SMARTPLUG":
            converted_device = SmartPlugDevice(device_details['name'], device_details['address'], device_uuid)

        converted_devices.append(converted_device)

    return converted_devices


def device_factory(device_name, device_type, device_address):
    if device_type == DeviceType.SMARTPLUG.value:
        return SmartPlugDevice.new_device(device_name, device_address)


def delete_device(device_id):
    if os.path.exists(f'data/{device_id}.csv'):
        os.remove(f'data/{device_id}.csv')

    with open('inventory/devices.json', 'r+') as device_file:
        raw_devices = json.load(device_file)

        del raw_devices[device_id]

        device_file.seek(0)
        json.dump(raw_devices, device_file)
        device_file.truncate()
