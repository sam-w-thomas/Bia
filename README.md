# NetworkBia
NetworkBia is a tool designed to monitor the electrical consumption across multiple network devices, providing the following:
* Aggregate Statistics
* Individual Device Statistics
* Historic Trends

KASA smart plugs are used when devices don't natively support grabbing power consumption

## Features
* Supports polling Cisco 2911 Router (potentially others but not tested) and KASA Smart Plug
* View current power consumption
* View historic power consumption in a graph - with datatime options
* View facts about device, such as version, model etc
* Setup customize polling interval (used in historic stats)
* Custom TextFSM templates

## Usage
1. Clone the repo from GitHub
2. Change to local repository and ensure any permissions are correct (usually a Linux problem)
3. Install requirements `pip install -r requirements.txt`
4. Launch main.py `python main.py`
5. Connect to website 127.0.0.1:8080
6. Add device via clicking "Add Device"
7. Select device type and complete form
![image](https://i.ibb.co/KXz0mCc/bia-add-device.png)
8. To capture data - click Controls
9. Select Snapshot to create individual data entry for all devices for capture for continuous polling

## Gallery
![image](https://i.ibb.co/RbbpFG5/bia-historic-stats.png)
![image](https://i.ibb.co/N3H3Pb2/bia-controls.png)
![image](https://i.ibb.co/NmNpjzj/bia-devices.png)
![image](https://i.ibb.co/5jV4CDw/bia-disconnected-devices.png)
![image](https://i.ibb.co/VDWz9R0/bia-smart-plug.png)
## ToDo
* Enable controls to change capture interval via GUI - currently done via configuration.yaml file and a restart
* Add proper documentation to each function/class
* Speed up load times
* Add aggregate historical stats

# Known Bugs
* Too short Capture Interval can cause issues
* If loading devices when polling it incorrectly reports device as down 