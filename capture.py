from devices import DeviceType
from devices import device_factory
from devices import get_devices

import csv
from threading import Timer, Lock
from datetime import datetime
import yaml

# Read configuration
with open('configuration.yaml', 'r') as config_file:
    bia_config = yaml.safe_load(config_file)

class Periodic(object):
    """
    A periodic task running in threading.Timers
    Based on https://stackoverflow.com/questions/2398661/schedule-a-repeating-event-in-python-3
    """

    def __init__(self, interval, function, *args, **kwargs):
        self._lock = Lock()
        self._timer = None
        self.function = function
        self.interval = interval
        self.args = args
        self.kwargs = kwargs
        self._stopped = True

    @property
    def stopped(self):
        return self._stopped

    def start(self, from_run=False):
        self._lock.acquire()
        if from_run or self._stopped:
            self._stopped = False
            self._timer = Timer(self.interval, self._run)
            self._timer.start()
        self._lock.release()

    def _run(self):
        self.start(from_run=True)
        self.function(*self.args, **self.kwargs)

    def stop(self):
        self._lock.acquire()
        self._stopped = True
        self._timer.cancel()
        self._lock.release()


def write_csv_line(device_id,
                   time_captured,
                   power=None):
    """
    Writs data to a devices data .csv

    :param device_id:
    :param time_captured:
    :param current:
    :param voltage:
    :param power:
    :return:
    """

    with open(f'data/{device_id}.csv', 'a', newline='') as csvfile:
        device_writer = csv.writer(csvfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)

        date_str = time_captured.isoformat()
        device_writer.writerow([date_str, power, bia_config['time_interval']])


def snapshot():
    devices = get_devices()

    print("Snapshotting")

    for device in devices:
        power = 0.0
        if device.connected():
            device_stats = device.get_properties()

            if 'power' in device_stats:
                power = device_stats['power']
            else:
                power = None

            current_date = datetime.now()

        write_csv_line(device.uuid, current_date, power)

