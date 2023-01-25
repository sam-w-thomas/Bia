from devices import DeviceType
from devices import device_factory
from devices import get_devices
from devices import delete_device
from capture import snapshot
from capture import Periodic

from flask import Flask, render_template, request, redirect
import yaml
import json

# Read configuration
with open('configuration.yaml', 'r') as config_file:
    bia_config = yaml.safe_load(config_file)

app = Flask(__name__)
capture_sched = Periodic(bia_config['time_interval'], snapshot)

@app.route('/')
@app.route('/devices')
def devices():
    return render_template('devices.html', devices=get_devices())


@app.route('/device/<device_id>', methods=['GET', 'POST'])
def device(
        device_id
):
    if request.method == "POST":
        delete_device(device_id)
        return redirect("/devices")
    if request.method == "GET":
        return render_template('device.html', device=get_devices(device_id))


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

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)
