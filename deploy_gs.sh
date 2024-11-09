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
REMOTE_USER="rock"
REMOTE_HOST="rock-5b.local"
DESTINATION_FOLDER="/home/rock/drone"

# generate ssh key if it doesn't exist
if [ ! -f ~/.ssh/id_rsa.pub ]; then
    ssh-keygen -t rsa -b 4096 -C "" -f ~/.ssh/id_rsa -q -N ""
fi

# add ssh key to server if it doesn't exist
ssh-copy-id -i ~/.ssh/id_rsa.pub "$REMOTE_USER"@"$REMOTE_HOST"

# copy the project to the server via ssh except for the .venv folder
rsync -avz -e ssh --exclude='.venv' $SOURCE_FOLDER $REMOTE_USER@$REMOTE_HOST:$DESTINATION_FOLDER

# run init_project.sh on the server
ssh "$REMOTE_USER"@"$REMOTE_HOST" "cd $DESTINATION_FOLDER/RCDroneCamera && sudo -S sh init_gs.sh -i $install"
