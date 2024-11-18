#!/bin/bash

# This script is used to deploy a RCDroneCamera project

while getopts i: flag
do
    case "${flag}" in
        i) install=${OPTARG};;
        *) install=false ;;
    esac
done

# set variables
SOURCE_FOLDER=$(pwd)
REMOTE_USER="admin"
REMOTE_HOST="raspberrypi"
DESTINATION_FOLDER="/home/admin/drone"

# generate ssh key if it doesn't exist
if [ ! -f ~/.ssh/id_rsa.pub ]; then
    ssh-keygen -t rsa -b 4096 -C "" -f ~/.ssh/id_rsa -q -N ""
fi

# add ssh key to server if it doesn't exist
ssh-copy-id -i ~/.ssh/id_rsa.pub "$REMOTE_USER"@"$REMOTE_HOST"

# copy the project to the server via ssh except for the .venv and .git folder
rsync -avz -e ssh --exclude='.venv' --exclude='.git' $SOURCE_FOLDER $REMOTE_USER@$REMOTE_HOST:$DESTINATION_FOLDER

# run init_drone.sh on the server
ssh "$REMOTE_USER"@"$REMOTE_HOST" "cd $DESTINATION_FOLDER/RCDroneCamera && sudo -S sh init_drone.sh -i $install"
