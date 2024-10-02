#!/bin/sh
# This script is used to initialize a RCDroneCamera project
# install python, and dependencies

while getopts i: flag
do
    case "${flag}" in
        i) install=${OPTARG};;
        *) install=false ;;
    esac
done

if [ "$install" = true ]; then
    # install picamera2
    sudo apt update
    sudo apt install -y python3-libcamera python3-kms++
    sudo apt install -y python3-prctl libatlas-base-dev ffmpeg python3-pip
    sudo apt install -y python3-picamera2 --no-install-recommends

    # Create a virtual environment from global python environment
    python -m venv venv --system-site-packages
    . ./venv/bin/activate

    # install dependencies
    pip install -r requirements.txt

    # copy camera.service to /etc/systemd/system and enable it
    sudo cp camera.service /etc/systemd/system/
    sudo systemctl enable camera.service
fi

# restart the camera service
sudo systemctl restart camera.service
