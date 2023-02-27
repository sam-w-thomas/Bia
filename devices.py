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
    """
    Device Interface for different types of actual devices
    """

    def __init__(self, name, address, device_uuid):
        self._uuid = device_uuid
        self._name = name
        self._address = address
        self.type = None

    @classmethod
    def new_device(cls,
                   name: str,
                   address: str):
        """
        Create a new device
        Creates data files

        :param name: Name of device
        :param address: IP address of device
        :return: device: Returns device object
        """
        device_uuid = uuid.uuid4()

        with open(f'data/{device_uuid}.csv', 'w', newline='') as csvfile:
            device_writer = csv.writer(csvfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            device_writer.writerow(['timestamp', 'power', 'interval'])

        return cls(name, address, device_uuid)

    @property
    def uuid(self):
        """
        Get device ID

        :return: uuid : String
        """
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
    """
    Kasa Smart Plug realisation of Device Interface
    Synonyms with KASA 115 currently

    name: Name of device
    address: IP address of device
    device_uuid: ID of address in inventory
    """

    def __init__(self, name, address, device_uuid):
        asyncio.set_event_loop(asyncio.SelectorEventLoop())
        Device.__init__(self, name, address, device_uuid)
        self._kasa_device = SmartPlug(self._address)
        self.type = DeviceType.SMARTPLUG

    def get_stats(self):
        """
        Get power, voltage and curret

        :return: stats
        """
        return asyncio.get_event_loop().run_until_complete(self.get_plug_stats())

    def get_capability(self):
        """
        Get capability of device - includes version, model etc

        :return: capability
        """
        return asyncio.get_event_loop().run_until_complete(self.get_cap_stats())

    def connected(self):
        """
        Check if device is connected
        True if is connected

        :return: connected
        """
        return asyncio.get_event_loop().run_until_complete(self.is_connected())

    def get_power(self) -> float:
        """
        Get current power in Watts

        :return: power
        """
        return self.get_stats()['power']

    def get_voltage(self) -> float:
        """
        Get current voltage in Volts

        :return: voltage
        """
        return self.get_stats()['voltage']

    def get_current(self) -> float:
        """
        Get current current in Amps

        :return: current
        """
        return self.get_stats()['current']

    def get_properties(self) -> dict:
        """
        Formats output for get_stats function so that deisred properties can be passed
        to Jinja/Flask for individual device displaying

        :return: properties
        """
        device_stats = self.get_stats()
        return {
            'power': device_stats['power'],
            'voltage': device_stats['voltage'],
            'current': device_stats['power'],
        }

    async def get_plug_stats(self):
        """
        Async IO function to be called by get_stats function

        :return: plug_emeter_stats
        """
        device = self._kasa_device
        await device.update()  # Request an update
        return device.emeter_realtime

    async def get_cap_stats(self) -> dict:
        """
        Async IO function to be called by get_capability function

        :return: plug_capability
        """
        device = self._kasa_device
        await device.update()  # Request an update

        cap_stats = {
            'alias': device.alias,
            'model': device.model,
            'rssi': device.rssi,
            'mac': device.mac,
        }

        return {**cap_stats, **device.hw_info}

    async def is_connected(self) -> bool:
        """
        Async IO function to check if device is connected

        SShortening timeout will increase load times but slow networks may be affected

        :return: is_connected
        """
        device = self._kasa_device
        try:
            await asyncio.wait_for(device.update(), timeout=0.75)
        except:
            return False

        return device.is_on


class CiscoDevice(Device):
    """
    Cisco Router realisation of Device Interface
    Currently only tested on 2911 - may be made specifically a 2911 in future

    name: Name of device
    address: IP address of device
    device_uuid: ID of address in inventory
    username: Device username for login
    password: Device password for login
    """

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

    def get_stats(self) -> dict:
        """
        Get device environment stats, such as power (if supported), cpu usage, memory usage

        :return: stats
        """
        try:
            self._device.open()
            dev_env = self._device.get_environment()
            self._device.close()
            return dev_env
        except napalm.base.exceptions.ConnectionException:
            return {}

    def get_capability(self) -> dict:
        """
        Get device capability, such as model, version, code train etc

        :return: capability
        """
        try:
            self._device.open()
            capabilities = self._device.get_facts()
            self._device.close()
            return capabilities
        except napalm.base.exceptions.ConnectionException:
            return {}

    def connected(self) -> bool:
        """
        Check if device is connected

        :return: connected
        """
        try:
            self._device.open()
            self._device.close()
            return True
        except napalm.base.exceptions.ConnectionException:
            return False

    def get_power(self) -> float:
        """
        Get device power via TextFSM template
        Alternative if Scrapli is unable to get directly

        :return:
        """
        self._scrapli_device.open()
        response = self._scrapli_device.send_command("show environment")
        enviroment_result = textfsm_parse("textfsm_templates/r2911_show_enviroment.textfsm", response.result)[
            0]  # Select first one, show enviroment won't have multiple instances
        self._scrapli_device.close()
        return float(enviroment_result['systempower'])

    def get_properties(self) -> dict:
        """
        Formats output for stats function so that desired properties can be passed
        to Jinja/Flask for individual device displaying

        Plus some output validation

        :return: properties
        """
        device_stats = self.get_stats()

        properties = {}

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
        device_id: str = None,
        check_connected: bool = False
):
    """
    Return all devices, or, if a device_id is supplied - a specific device

    :param device_id: Device ID of device in inventory file
    :param check_connected: Only return devices confirmed to be connected

    :return: devices: List of devices
    """
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
    """
    Factory for creating devices based on type supplied
    Moves logic away from main.py

    :param device_name: Device Name
    :param device_type: Device Type (enum)
    :param device_address: Device IP address
    :param device_username: Device username used for login (only on specific devices)
    :param device_password: Device password user for login (only on specific devices)
    :return:
    """
    if device_type == DeviceType.SMARTPLUG.value:
        return SmartPlugDevice.new_device(device_name, device_address)
    elif device_type == DeviceType.CISCO.value:
        return CiscoDevice.new_device(device_name, device_address, device_username, device_password)


def delete_device(device_id):
    """
    Remove device from inventory and associated data

    :param device_id: Device ID device in inventory
    """
    if os.path.exists(f'data/{device_id}.csv'):
        os.remove(f'data/{device_id}.csv')

    with open('inventory/devices.json', 'r+') as device_file:
        raw_devices = json.load(device_file)

        del raw_devices[device_id]

        device_file.seek(0)
        json.dump(raw_devices, device_file)
        device_file.truncate()
