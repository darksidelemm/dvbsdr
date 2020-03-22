## VK5QI fork

This fork of dvbsdr exists so I can configuration-manage the changes I have made to dvbsdr for an upcoming Project Horus payload.

Additions by VK5QI:
* `scripts/rpi_tx.sh` - Essentially the same as the encode_modulate.sh script mentioned below, with customizations for our flight.
* dvbsdr systemd service file (`dvbsdr.service`). Allows dvbsdr to be started and stopped using sytemd.
  * Note: not everything stops cleanly using sytemctl stop. Suggest using systemctl kill, followed by a systemctl stop to properly kill the software.
* `dvb_watchdog.py`, intended to be run on startup from `/etc/rc.local`. This script monitors a few temperature sensors, some IO pins, and (eventually) GPS descent/altitude data to determine when the DVB-S modulator and Power Amplifier should be enabled. Currently the following IO Connections are used:
  * GPIO 21 - DVB-S Enable. Short pin to ground to enable DVB-S transmissions. Disconnect to stop transmissions.
  * GPIO 13 - PA Enable. This used to drive the gate of a 2N7000 (via 100R, with a 10K pull-down at the gate), which drives a relay coil. This lets me completely cut power to the PA, cutting power dissipation within the payload by ~3-4W.
  * GPIO 4 - 1Wire Interface, to a DS18B20.

As I have had issues reliably getting full power out of the LimeSDR Mini when using a stored limemini.cal file, I've taken the approach of calibrating at each startup. As I have control over the PA, I disable power to the PA prior to starting DVB-S modulation, then enable the PA 30 seconds later.

TODO:
* Monitor modulator output, and try and detect there are issues with the PiCam. (Maybe monitor running processes?)
* Add GPS input, with descent rate detection. Aim here is to cut power to the PA when the payload is in descent, and is about to land. Will need to use some non-volatile storage (save a file?) to ensure this persists across reboots.
  * Maybe use another GPIO line to override these checks, for testing on ground?
* Add additional temp sensors (DS18B20), bonded to the payload's heat spreader. Decided on an appropriate high temperature cutoff, and hysteresis values.

### Video Flipping
avc2ts doesn't have a command-line option to flip the video, which might be required if the camera is mounted upside-down (as it is in my case). To get around this, [this line](https://github.com/F5OEO/avc2ts/blob/master/avc2ts.cpp#L1261) needs to be uncommented in avc2ts.cpp (which will be located in ~/dvbsdr/build/avc2ts/ after running the install script), and changed to read
```
setMirror(OPORT_VIDEO,OMX_MirrorBoth);
```

Then, re-compile (run `make` in the avc2ts directory) and copy the avc2ts binary into `~/dvbsdr/bin/`.

# About dvbsdr

**dvbsdr** is an integration of several projects around Digital Amator TeleVision using SDR technics.

LimeSDRMini is the main supported SDR hardware for now.

This project is less user friendly than [BATC Portsdown](https://wiki.batc.org.uk/Portsdown_2019) also based on similar components.

This project help people who want to use latest developments and more in depeth experts parameters.

It should run on 
- Raspberry Pi 
- Nvidia Jetson Nano
- Some parts works on regular X86 Debian based 

# Installation

- Pi : Assuming a Raspbian Lite installation (stretch) : https://www.raspberrypi.org/downloads/raspbian/
- Jetson Nano : Assuming a Linux Tegra Ubuntu
- X86 : Debian stretch based

Be sure to have git package installed :
```sh
sudo apt-get update
sudo apt-get install git
```
You can now clone the repository. A script (install.sh) is there for easy installation. You could inspect it and make steps manualy in case of any doubt.  

```sh
git clone https://github.com/F5OEO/dvbsdr
cd dvbsdr
./install.sh
```

# Running

Scripts are located under dvbsdr/scripts

- Pi : Encode from Picamera or USB Webcam
```sh
./encode_modulate.sh
```

- Jetson nano : Encode from Picamera V2 or transmodulate from an incoming IP transport stream
```sh
./jetson_nano.sh
```

- All : Modulate from an incoming IP transport stream
```sh
./encode_modulate.sh
```

Please inspect each script, parameters are mainly self documented.

# Special firmware

In order to decrease USB bandwidth and have better signal quality, a special [Firmware](https://github.com/natsfr/LimeSDR_DVBSGateware) is available.

In order to use this mode you should prior flash it, 
```sh
./install_fpga_mapping.sh
```

If you like to reverse back to regular firmware 
```sh
./restore_original_firmware.sh
```

# Notes

Some components are installed but not used right now (csdr,leandvb,KisSpectrum...) which will be integrated in the future (or not) to extend DATV only transmission feature.


