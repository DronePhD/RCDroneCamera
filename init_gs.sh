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
    # install python 3.12 via pyenv
    sudo apt-get update
    curl https://pyenv.run | bash
    export PYENV_ROOT="$HOME/.pyenv"
    command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"
    eval "$(pyenv init -)"
    git clone https://github.com/pyenv/pyenv-virtualenv.git $(pyenv root)/plugins/pyenv-virtualenv
    eval "$(pyenv virtualenv-init -)"
#    pyenv install 3.12
    pyenv global 3.12

    # Create a virtual environment via virtualenv
    pyenv virtualenv 3.12 RCDroneCamera
    pyenv activate RCDroneCamera

    # install dependencies
    pip install -r gs_requirements.txt

    # copy camera.service to /etc/systemd/system and enable it
    sudo cp display.service /etc/systemd/system/
    sudo systemctl enable display.service
    sudo systemctl enable wifibroadcast
    sudo systemctl enable wifibroadcast@gs
fi

# restart the camera service
sudo cp display.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl restart display
echo "Restarted display service."
sudo systemctl status display
