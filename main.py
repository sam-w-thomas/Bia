import history
from devices import DeviceType
from devices import device_factory
from devices import get_devices
from devices import delete_device
from capture import snapshot
from capture import Periodic
from history import DeviceHistory

import datetime
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from flask import Flask, render_template, request, redirect, Response
import yaml
import json
import io

# Read configuration
with open('configuration.yaml', 'r') as config_file:
    bia_config = yaml.safe_load(config_file)

app = Flask(__name__)
capture_sched = Periodic(bia_config['time_interval'], snapshot)


@app.route('/')
@app.route('/devices')
def devices():
    """
    Provide details on all devices
    """
    return render_template('devices.html', devices=get_devices())


@app.route('/device/<device_id>', methods=['GET', 'POST', 'DELETE'])
def device(
        device_id
):
    """
    Provide details on individual device

    :param device_id: ID of device in inventory
    """
    if request.method == "GET":
        if request.args.get('start_time'):
            start_time_raw = request.args.get('start_time')
            start_time = datetime.datetime.strptime(start_time_raw, '%Y-%m-%dT%H:%M')
        else:
            start_time = datetime.datetime.min
            start_time_raw = start_time.strftime('%Y-%m-%dT%H:%M')

        if request.args.get('end_time'):
            end_time_raw = request.args.get('end_time')
            end_time = datetime.datetime.strptime(end_time_raw, '%Y-%m-%dT%H:%M')
        else:
            end_time = datetime.datetime.max
            end_time_raw = end_time.strftime('%Y-%m-%dT%H:%M')

        device_history = DeviceHistory(device_id)

        return render_template('device.html',
                               device=get_devices(device_id),
                               dev_history=device_history,
                               start_time=start_time,
                               end_time=end_time,
                               start_time_raw=start_time_raw,
                               end_time_raw=end_time_raw)

    if request.method == "DELETE":
        delete_device(device_id)
        return redirect("/devices")


@app.route('/controls')
def controls():
    """
    Controls is the settings page
    Work needed here to make settings usable - currently loads off configuration.yaml and requires restart
    """
    data_points = history.get_all_data_points()

    return render_template('controls.html',
                           capturing=capture_sched.stopped,
                           time_interval=bia_config['time_interval'],
                           data_points=data_points)


@app.route('/add_device', methods=['GET', 'POST'])
def add_device():
    """
    Add device to inventory
    """
    if request.method == "GET":
        device_types = [member.value for member in DeviceType]
        return render_template('add_device.html', device_types=device_types)
    elif request.method == "POST":
        device_type = request.form.get('device_type')
        if device_type == "SMARTPLUG":
            # Get details from form
            device_name = request.form.get('device_name')
            device_address = request.form.get('device_address')

            unsaved_device = device_factory(
                device_name,
                device_type,
                device_address
            )

            unsaved_device.save()

        if device_type == "CISCO":
            # Get details from form
            device_name = request.form.get('device_name')
            device_address = request.form.get('device_address')
            device_username = request.form.get('device_username')
            device_password = request.form.get('device_password')

            unsaved_device = device_factory(
                device_name,
                device_type,
                device_address,
                device_username=device_username,
                device_password=device_password
            )

            unsaved_device.save()

        return redirect("/")


@app.route('/device_snapshot', methods=['POST'])
def device_snapshot():
    """
    Snapshot power consumption across all devices
    Adds consumption to "data" folder
    """
    if request.method == "POST":
        snapshot()

        return redirect("/controls")


@app.route('/enable_capture', methods=['POST'])
def enable_capture():
    """
    Enable periodic capture (snapshots at interval)
    """
    if request.method == "POST":
        capture_sched.start()

        return redirect("/controls")


@app.route('/disable_capture', methods=['POST'])
def disable_capture():
    """
    Disable periodic capture (snapshots at interval)
    """
    if request.method == "POST":
        capture_sched.stop()

        return redirect("/controls")

@app.route('/device/<device_id>/usage_graph.png')
def device_image(device_id):
    """
    Handles dynamic loading graphs
    Start and End time supplied as arguments in request

    :param device_id: ID of device in inventory file

    :return: response_graph
    """
    start_time = None
    end_time = None

    if request.args.get('start_time'):
        start_time = datetime.datetime.strptime(request.args.get('start_time'), '%Y-%m-%dT%H:%M')

    if request.args.get('end_time'):
        end_time = datetime.datetime.strptime(request.args.get('end_time'), '%Y-%m-%dT%H:%M')

    device_history = DeviceHistory(device_id)
    usage_graph = device_history.usage_graph(start_time, end_time)
    output = io.BytesIO()
    FigureCanvas(usage_graph).print_png(output)
    return Response(output.getvalue(), mimetype='image/png')


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)
