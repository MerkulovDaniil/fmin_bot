#!/bin/bash

# Get the current weekday and MSK hour
TIMEZONE="Europe/Moscow"
FORMATTED_DATE=$(TZ=$TIMEZONE date +"%a_%H")

# Use rclone to copy the data with the formatted date in the path
rclone copy /root/bots/fmin_bot/fmin_data_production remote:/Backups/bots/fmin/fmin_data_$FORMATTED_DATE
