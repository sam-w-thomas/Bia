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
    return render_template('devices.html', devices=get_devices())


@app.route('/device/<device_id>', methods=['GET', 'POST', 'DELETE'])
def device(
        device_id
):
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
    return render_template('controls.html', capturing=capture_sched.stopped, time_interval=bia_config['time_interval'])


@app.route('/add_device', methods=['GET', 'POST'])
def add_device():
    if request.method == "GET":
        device_types = [member.value for member in DeviceType]
        return render_template('add_device.html', device_types=device_types)
    elif request.method == "POST":

        # Get details from form
        device_name = request.form.get('device_name')
        device_type = request.form.get('device_type')
        device_address = request.form.get('device_address')

        unsaved_device = device_factory(
            device_name,
            device_type,
            device_address
        )

        unsaved_device.save()

        return redirect("/")


@app.route('/device_snapshot', methods=['POST'])
def device_snapshot():
    if request.method == "POST":
        snapshot()

        return redirect("/controls")


@app.route('/enable_capture', methods=['POST'])
def enable_capture():
    if request.method == "POST":
        capture_sched.start()

        return redirect("/controls")


@app.route('/disable_capture', methods=['POST'])
def disable_capture():
    if request.method == "POST":
        capture_sched.stop()

        return redirect("/controls")


@app.route('/device/<device_id>/usage_graph.png')
def device_image(device_id):
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
