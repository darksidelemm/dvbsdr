#!/bin/bash
# dvbsdr watchdog startup script
sudo modprobe w1-therm
cd /home/pi/dvbsdr/
python dvb_watchdog.py