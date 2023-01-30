import ciso8601

from devices import SmartPlugDevice
from devices import DeviceType
from history import DeviceHistory
import datetime

device_history = DeviceHistory("407e584b-9d70-41db-a5c1-c39bf6652cd5")
start_time = ciso8601.parse_datetime("2023-01-25T16:10:57.394552")
end_time = ciso8601.parse_datetime("2023-01-25T16:11:47.441577")
#print(device_history.usage(start_time, end_time)[:, 0])
#print(device_history.total_usage())
device_history.usage_graph(start_time = start_time)
#print(device_history.history(start_time, end_time))