from kasa import SmartPlug
from kasa import SmartDeviceException
from scrapli.driver.core import IOSXEDriver
from scrapli.helper import textfsm_parse
from scrapli import Scrapli

import asyncio
import csv
from enum import Enum
import napalm
import uuid
import json
import os


class DeviceType(Enum):
    SMARTPLUG = "SMARTPLUG"
    CISCO = "CISCO"


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
            device_writer.writerow(['timestamp', 'power', 'interval'])

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

    def is_connected(self):
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

    def connected(self):
        return asyncio.get_event_loop().run_until_complete(self.is_connected())

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

    async def is_connected(self):
        device = self._kasa_device
        try:
            await asyncio.wait_for(device.update(), timeout=0.75)
        except:
            return False

        return device.is_on


class CiscoDevice(Device):
    def __init__(self, name, address, device_uuid, username, password):
        Device.__init__(self, name, address, device_uuid)

        # Setup Napalm
        self._driver = napalm.get_network_driver("ios")
        conn_details = {
            "hostname": address,
            "username": username,
            "password": password,
            "timeout": 0.75
        }
        self._device = self._driver(**conn_details)
        self._username = username
        self._password = password
        self.type = DeviceType.CISCO

        # Setup Scrapli, primarily for TextFSM parsing
        scrapli_conn_details = {
            "host": address,
            "auth_username": username,
            "auth_password": password,
            "auth_strict_key": False,
            "platform": "cisco_iosxe",
            "transport": "paramiko"
        }

        self._scrapli_device = Scrapli(**scrapli_conn_details)


    @classmethod
    def new_device(cls, name, address, username, password):
        device_uuid = uuid.uuid4()

        with open(f'data/{device_uuid}.csv', 'w', newline='') as csvfile:
            device_writer = csv.writer(csvfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            device_writer.writerow(['timestamp', 'power', 'interval'])

        return cls(name, address, device_uuid, username, password)

    def get_stats(self):
        try:
            self._device.open()
            dev_env = self._device.get_environment()
            self._device.close()
            return dev_env
        except napalm.base.exceptions.ConnectionException:
            return {}

    def get_capability(self):
        try:
            self._device.open()
            capabilities = self._device.get_facts()
            self._device.close()
            return capabilities
        except napalm.base.exceptions.ConnectionException:
            return {}

    def connected(self):
        try:
            self._device.open()
            self._device.close()
            return True
        except napalm.base.exceptions.ConnectionException:
            return False

    def get_power(self):
        self._scrapli_device.open()
        response = self._scrapli_device.send_command("show environment")
        enviroment_result = textfsm_parse("textfsm_templates/r2911_show_enviroment.textfsm", response.result)[0] #Select first one, show enviroment won't have multiple instances
        self._scrapli_device.close()
        print(enviroment_result)
        return enviroment_result['systempower']

    def get_properties(self):
        device_stats = self.get_stats()
        properties = {}

        print(device_stats)

        if 'power' in device_stats and "output" in device_stats['power']:
            properties['power'] = device_stats['power']['output']
        else:
            properties['power'] = self.get_power()
        
        if 'cpu' in device_stats:
            properties['cpu'] = device_stats['cpu'][0]['%usage']

        if 'memory' in device_stats:
            properties['memory'] = device_stats['memory']['used_ram'],

        return properties

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
                'address': self._address,
                'username': self._username,
                'password': self._password
            }

            device_file.seek(0)
            json.dump(raw_devices, device_file)
            device_file.truncate()


def get_devices(
        device_id=None,
        check_connected=False
):
    with open('inventory/devices.json') as device_file:
        raw_devices = json.load(device_file)

    # Return single device if device_id supplied
    if device_id:
        device_details = raw_devices[device_id]
        dev_type = device_details['type']
        if dev_type == "SMARTPLUG":
            return SmartPlugDevice(device_details['name'], device_details['address'], device_id)
        elif dev_type == "CISCO":
            return CiscoDevice(device_details['name'],
                               device_details['address'],
                               device_id,
                               device_details['username'],
                               device_details['password'])

    # Return multiple devices if no device_id supplied
    converted_devices = []
    for device_uuid, device_details in raw_devices.items():
        dev_type = device_details['type']
        if dev_type == "SMARTPLUG":
            converted_device = SmartPlugDevice(device_details['name'], device_details['address'], device_uuid)
        elif dev_type == "CISCO":
            converted_device = CiscoDevice(device_details['name'],
                                           device_details['address'],
                                           device_uuid,
                                           device_details['username'],
                                           device_details['password'])

        if check_connected:
            if converted_device.connected():
                converted_devices.append(converted_device)
        else:
            converted_devices.append(converted_device)

    return converted_devices


def device_factory(device_name, device_type, device_address, device_username=None, device_password=None):
    if device_type == DeviceType.SMARTPLUG.value:
        return SmartPlugDevice.new_device(device_name, device_address)
    elif device_type == DeviceType.CISCO.value:
        return CiscoDevice.new_device(device_name, device_address, device_username, device_password)


def delete_device(device_id):
    if os.path.exists(f'data/{device_id}.csv'):
        os.remove(f'data/{device_id}.csv')

    with open('inventory/devices.json', 'r+') as device_file:
        raw_devices = json.load(device_file)

        del raw_devices[device_id]

        device_file.seek(0)
        json.dump(raw_devices, device_file)
        device_file.truncate()
