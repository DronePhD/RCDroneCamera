# RCDroneCamera project

This project is a service that connects RC controller with a camera via PX4 to control the camera and take photos,
videos, and stream video.

## How to deploy

Run the following command:

```bash
sh deploy.sh -i <true|false>
```

The `-i` flag is optional. If it is set to `true`, the script will install python and other dependencies. Otherwise, it
will only deploy the project.
You may be asked to enter your password to install python and other dependencies. In such a case, please enter Radxa
password and press enter.

Deployment is possible only from the local network with Raspberry Pi connected to the same network.

## How to connect to the RaspberryPi board

1. Connect to the RaspberryPi board via ssh

```bash
ssh admin@raspberrypi
```

3. Enter the password: `admin`

Code is located in the `/srv/RCDroneCamera` directory.

## How to run

1. Connect to the RaspberryPi board
2. Go to the project directory and activate root

```bash
cd /srv/RCDroneCamera
sudo su
```

3. Run the following command:

```bash
source venv/bin/activate
python main.py --stream-resolution 1280x720 --stream-url udp://<IP>:<PORT> --media-folder /srv/samba/shared --drone-connection /dev/serial0 --drone-baud-rate 921600
```

Replace `<IP>` and `<PORT>` with the IP address and port number of the device that will receive the video stream.
All of the parameters are optional. But if you want to change the default values, you need to provide them.

## How to debug

1. Connect to the RaspberryPi board
2. Go to the project directory and activate root and run ipython

```bash
cd /srv/RCDroneCamera
sudo su
source venv/bin/activate
ipython
```

3. Run the following code:

```python
from main import *

mavlink_handler = MAVLinkHandler(CONNECTION_STRING, BAUD_RATE)
mavlink_handler.setLevel(logging.INFO)
logger.addHandler(mavlink_handler)
with CameraService(VIDEO_STREAM_URL, MEDIA_FOLDER, (1280, 720)) as camera:
    RCService(CONNECTION_STRING, BAUD_RATE, camera).listen()
    time.sleep(1000000)
```

This code will start the service and you will be able to see the logs in the console. Also, you can interact with the
service using the RC controller. Or make changes in the code and see the results.
