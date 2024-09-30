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
PROJECT_PATH=$(pwd)
SERVER_USER="admin"
SERVER_IP="raspberrypi"
SERVER_PATH="/srv/RCDroneCamera/"

# generate ssh key if it doesn't exist
if [ ! -f ~/.ssh/id_rsa.pub ]; then
    ssh-keygen -t rsa -b 4096 -C "" -f ~/.ssh/id_rsa -q -N ""
fi

# add ssh key to server if it doesn't exist
ssh-copy-id -i ~/.ssh/id_rsa.pub "$SERVER_USER"@"$SERVER_IP"

# copy the project to the server via ssh
ssh "$SERVER_USER"@"$SERVER_IP" "sudo -S rm -r $SERVER_PATH"
scp -r "$PROJECT_PATH" "$SERVER_USER"@"$SERVER_IP":"$SERVER_PATH"

# run init_project.sh on the server
ssh "$SERVER_USER"@"$SERVER_IP" "cd $SERVER_PATH && sudo -S sh init_project.sh -i $install"
