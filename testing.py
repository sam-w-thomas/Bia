from devices import SmartPlugDevice
from devices import DeviceType

smart_device = SmartPlugDevice("KASA115", "192.168.0.28")

print(smart_device.get_power())
