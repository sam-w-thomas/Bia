import ciso8601
import matplotlib.pyplot as plt
import numpy as np

import csv
import datetime
import statistics as stats
import os


class DeviceHistory:
    def __init__(self, device_uuid):
        with open(f'data/{device_uuid}.csv', 'r', newline='') as csv_file:
            csv_reader = csv.DictReader(csv_file)

            history_data = []
            for row in csv_reader:
                row['timestamp'] = ciso8601.parse_datetime(row['timestamp'])
                history_data.append(row)

        self._history = np.array(history_data)

    def __len__(self):
        return len(self._history)

    def length(self,
               start_time=None,
               end_time=None):
        values = self.history(start_time, end_time)
        return len(values)

    def mean(self,
             start_time=None,
             end_time=None):

        power_values = self.history(start_time, end_time)[:, 1]

        return stats.mean(power_values)

    def mode(self):
        power_captured = [float(capture['power']) for capture in self._history]

        return stats.mode(power_captured)

    def median(self):
        power_captured = [float(capture['power']) for capture in self._history]

        return stats.median(power_captured)

    def raw_data(self):
        print(self._history.tolist())
        return self._history.tolist()

    def history(self,
                start_time=None,
                end_time=None):

        # If no start_time passed
        if start_time is None:
            start_time = datetime.datetime.min

        if end_time is None:
            end_time = datetime.datetime.max

        history_data = []
        for capture in self._history:
            if end_time >= capture['timestamp'] >= start_time:
                history_data.append([
                    capture['timestamp'],
                    float(capture['power']),
                    capture['interval']
                ])

        if len(history_data) == 0:
            return np.zeros((0, 4), dtype='float') # incase no captures yet
        else:
            return np.array(history_data)

    def usage(self,
              start_time=None,
              end_time=None):
        """
        Return calculate usage
        Uses "time_interval" as capture time and adds up all usage in these times

        :return usage_kwh:
        """
        usage_kwh = []

        for capture in self.history(start_time, end_time):
            power = float(capture[1])  # measured in watts
            interval = int(capture[2])  # measured in seconds

            # convert interval ot hours
            interval_hour = interval / 3600

            usage_kwh.append([((power * interval_hour) / 1000), interval])

        return np.array(usage_kwh)

    def sum_usage(self,
                  start_time=None,
                  end_time=None):
        """
        Calculate usage for a given timeperiod
        Uses "time_interval" as capture time and adds up all usage in these times

        :return:
        """
        total_usage = self.usage(start_time, end_time)

        return sum(total_usage)

    def usage_graph(self,
                    start_time=None,
                    end_time=None):

        history = self.history(start_time, end_time)
        np_history = history[:, 1]
        np_time = history[:, 0]

        fig = plt.figure(figsize=(10, 8))
        plt.xticks(rotation=40)
        plt.plot(np_time, np_history)
        plt.xlabel('Timestamp')
        plt.ylabel('Watt')

        return fig

    def empty(self):
        if len(self._history) == 0:
            return True
        else:
            return False

def get_all_data_points():
    """
    Return all energy data points in each data folder

    :return:
    """

    data_points = []

    # get all data points
    directory = os.fsencode('data')

    for device_data in os.listdir(directory):
        with open(f'data/{device_data.decode("utf-8")}', 'r', newline='') as csv_file:
            csv_reader = csv.DictReader(csv_file)

            for row in csv_reader:
                row['device'] = device_data.decode("utf-8")
                data_points.append(row)

    return data_points
