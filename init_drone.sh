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

    # install GStreamer
    sudo apt install libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev libgstreamer-plugins-bad1.0-dev \
                     gstreamer1.0-plugins-base gstreamer1.0-plugins-good gstreamer1.0-plugins-bad \
                     gstreamer1.0-plugins-ugly gstreamer1.0-libav gstreamer1.0-tools gstreamer1.0-x \
                     gstreamer1.0-alsa gstreamer1.0-gl gstreamer1.0-gtk3 gstreamer1.0-qt5 gstreamer1.0-pulseaudio

    # Install wfb-ng
    sudo apt-get install dkms
    # For 8812au:
    git clone -b v5.2.20 https://github.com/svpcom/rtl8812au.git
    cd rtl8812au/
    sudo ./dkms-install.sh

    cat <<EOF >> /etc/wifibroadcast.cfg
[common]
wifi_channel = 161     # 161 -- radio channel @5825 MHz, range: 5815–5835 MHz, width 20MHz
                       # 1 -- radio channel @2412 Mhz,
                       # see https://en.wikipedia.org/wiki/List_of_WLAN_channels for reference
wifi_region = 'BO'     # Your country for CRDA (use BO or GY if you want max tx power)

[drone_video]
peer = 'listen://0.0.0.0:5602'  # listen for video stream (gstreamer on drone)

[drone_mavlink]
peer = 'listen://0.0.0.0:14550'  # listen for mavlink messages
EOF
    cat > /etc/modprobe.d/wfb.conf << EOF
# blacklist stock module
blacklist 88XXau
blacklist 8812au
options cfg80211 ieee80211_regdom=RU
# maximize output power by default
#options 88XXau_wfb rtw_tx_pwr_idx_override=30
# minimize output power by default
options 88XXau_wfb rtw_tx_pwr_idx_override=1
options 8812eu rtw_tx_pwr_by_rate=0 rtw_tx_pwr_lmt_enable=0
EOF

    sudo apt install python3-all libpcap-dev libsodium-dev python3-pip python3-pyroute2 \
                     python3-future python3-twisted python3-serial python3-all-dev iw virtualenv \
                     debhelper dh-python build-essential -y
    git clone -b stable https://github.com/svpcom/wfb-ng.git
    cd wfb-ng && make deb && sudo apt install ./deb_dist/wfb-ng*.deb

    # Create a virtual environment from global python environment
    python -m venv venv --system-site-packages
    . ./venv/bin/activate

    # install dependencies
    pip install -r requirements.txt

    # copy camera.service to /etc/systemd/system and enable it
    sudo cp camera.service /etc/systemd/system/
    sudo cp health_check.service /etc/systemd/system/
    sudo systemctl enable camera.service
    sudo systemctl enable health_check.service
    sudo systemctl enable wifibroadcast
    sudo systemctl enable wifibroadcast@drone
fi

# restart the camera service
sudo cp camera.service /etc/systemd/system/
sudo cp health_check.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl restart camera
echo "Restarted camera"
sudo systemctl status camera
sudo systemctl restart health_check
echo "Restarted health_check"
sudo systemctl status health_check
