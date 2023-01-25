import ciso8601

from devices import SmartPlugDevice
from devices import DeviceType
from history import DeviceHistory
import datetime

device_history = DeviceHistory("407e584b-9d70-41db-a5c1-c39bf6652cd5")
start_time = ciso8601.parse_datetime("2023-01-24T18:41:58.100972")
end_time = ciso8601.parse_datetime("2023-01-25T16:10:57.394552")
print(device_history.usage(start_time,end_time))
print(device_history.total_usage())
