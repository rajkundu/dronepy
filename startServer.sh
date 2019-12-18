#!/bin/bash

HOSTIP="192.168.1.2"
LISTENPORT=26495

# Ensure the environment is available
source /home/raj/.bashrc

/usr/bin/tmux new-session -d -s textserver
/usr/bin/tmux send-keys -t textserver "source /home/raj/.bashrc" C-m
/usr/bin/tmux send-keys -t textserver "/home/raj/dronepy/textserver.py \"$HOSTIP:$LISTENPORT\"" C-m

