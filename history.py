import ciso8601

import csv
import statistics as stats

class DeviceHistory:
    def __init__(self, device_uuid):
        with open(f'data/{device_uuid}.csv', 'r', newline='') as csv_file:
            csv_reader = csv.DictReader(csv_file)

            history_data = []
            for row in csv_reader:
                print(row['timestamp'])
                row['timestamp'] = ciso8601.parse_datetime(row['timestamp'])
                history_data.append(row)

        self._history = history_data

    def history(self):
        print(self._history)

    def mean(self):
        power_captured = [float(capture['power']) for capture in self._history]

        return stats.mean(power_captured)

    def mode(self):
        power_captured = [float(capture['power']) for capture in self._history]

        return stats.mode(power_captured)

    def median(self):
        power_captured = [float(capture['power']) for capture in self._history]

        return stats.median(power_captured)

    def total_usage(self):
        """
        Return calculate usage
        Uses "time_interval" as capture time and adds up all usage in these times

        :return total_kwh:
        """
        total_kwh = 0.0

        for capture in self._history:
            power = float(capture['power']) # measured in watts
            interval = int(capture['interval']) # measured in seconds

            # convert interval ot hours
            interval_hour = interval / 3600

            kwh = (power * interval_hour) / 1000

            total_kwh += kwh

        return total_kwh

    def usage(self,
              start_time,
              end_time):
        """
        Calculate usage for a given timeperiod
        Uses "time_interval" as capture time and adds up all usage in these times

        :return:
        """
        total_kwh = 0.0

        for capture in self._history:
            if end_time >= capture['timestamp'] >= start_time:
                power = float(capture['power']) # measured in watts
                interval = int(capture['interval']) # measured in seconds

                # convert interval ot hours
                interval_hour = interval / 3600

                kwh = (power * interval_hour) / 1000

                total_kwh += kwh

        return total_kwh