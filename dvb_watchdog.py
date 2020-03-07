#!/usr/bin/env python
#
#   DVB-S HAB Payload Watchdog script.
#
#   Performs checks every X seconds to see if it is safe to enable the DVB-S transmitter.
#
#   This assumes the 
#
import argparse
import logging
import subprocess
import sys
import time

try:
    import RPi.GPIO as GPIO
except RuntimeError:
    print("ERROR: Could not load RPi GPIO Libraries.")

# Pin Definitions
DVB_ENABLE_SWITCH = 21  # Switch wired between GPIO pin and GND. Close switch to enable TX.
DVB_ENABLE_RELAY = 13   # Relay wired between 12V rail and PA power input.
                        # Relay coil powered via 2N7000, with 2N7000 gate connected to this pin via 100ohm resistor,
                        # and 10k pulldown.

# Limits
PIZERO_TEMP_LIMIT = 80.0 # Official threshold is 85 degrees, with CPU throttling occuring at 82 degrees.
HEATSINK_TEMP_LIMIT = 75.0 # Final threshold TBD.

# Timer Settings
LOOP_TIMER = 30 # Check states every 10 seconds.
last_changed_time = 0 # Last changed.

# DS18B20 Heatsink
# Replace this with the path to your specific DS18B20 device.
DS18B20 = "/sys/bus/w1/devices/28-00000259dcab/w1_slave"


def get_cpu_temperature():
    """ Grab the temperature of the RPi CPU """
    try:
        data = subprocess.check_output("/opt/vc/bin/vcgencmd measure_temp", shell=True)
        temp = data.split('=')[1].split('\'')[0]
        return float(temp)
    except Exception as e:
        logging.error("Error reading temperature - %s" % str(e))
        return -1


def get_heatsink_temperature():
    """ Grab the temperature of a connected DS18B20, nominally attached to the payload heatsink """
    if DS18B20 is None:
        return -273.0
    
    try:
        _f = open(DS18B20, 'r')
        _lines = _f.read()
        _f.close()

        if 'YES' in _lines:
            # Valid CRC.
            _temp = _lines.split('t=')[1].strip()
            # Handle the DS18B20's first output, which always seems to be 85 degrees.
            if _temp == "85000":
                return -273.0
            else:
                _temp = int(_temp)/1000.0
                return _temp
    except Exception as e:
        logging.error("Error reading temperature - %s" % str(e))
        return -273.0


def check_dvbsdr_status():
    """ Call systemctl to find out if dvbsdr is running """
    _result = ""
    try:
        _result = subprocess.check_output("sudo systemctl is-active dvbsdr", shell=True)
    except Exception as e:
        logging.error("Error checking dvbsdr status - %s" % str(e))

    if ('active' in _result):
        return True
    else:
        return False


def dvbsdr_start():
    """ Call systemctl to start dvbsdr """
    logging.info("Attempting to start DVBSDR.")
    try:
        _result = subprocess.check_output("sudo systemctl start dvbsdr", shell=True)
    except Exception as e:
        logging.error("Error starting dvbsdr - %s" % str(e))

    logging.info("DVBSDR Started.")


def dvbsdr_stop():
    """ Call systemctl to stop dvbsdr """
    logging.info("Attempting to stop DVBSDR.")
    try:
        _result = subprocess.check_output("sudo systemctl kill dvbsdr", shell=True)
    except Exception as e:
        logging.error("Error stopping dvbsdr - %s" % str(e))

    time.sleep(3)
    try:
        _result = subprocess.check_output("sudo systemctl stop dvbsdr", shell=True)
    except Exception as e:
        logging.error("Error stopping dvbsdr - %s" % str(e))
    
    logging.info("DVBSDR Stopped.")


def loop():

    # Get inputs
    _cpu_temp = get_cpu_temperature()
    _heatsink_temp = get_heatsink_temperature()
    _switch_state = not GPIO.input(DVB_ENABLE_SWITCH)

    # TODO - GPS altitude/descent-rate based check.
    _landing = False

    logging.info("CPU Temp: %.1f \tHeatsink Temp: %.1f \tEnable Switch: %s \tLanding Mode: %s" % (_cpu_temp, _heatsink_temp, str(_switch_state), str(_landing)))

    # Check if DVBSDR is running already.
    _dvbsdr_running = check_dvbsdr_status()
    logging.info("DVBSDR Running: %s" % str(_dvbsdr_running))

    if (_switch_state is True) and (_cpu_temp < PIZERO_TEMP_LIMIT) and (_heatsink_temp < HEATSINK_TEMP_LIMIT) and (not _landing):
        # We should be OK to transmit.
        if not _dvbsdr_running:
            # Ensure the PA is off
            GPIO.output(DVB_ENABLE_RELAY, False)
            # Start DVBSDR.
            dvbsdr_start()
            # We perform a cal every startup, to be sure we get full output power.
            # As such, we should NOT turn on the PA until after the cal is done.
            logging.info("Waiting 30 seconds before enabling PA.")
            time.sleep(30)

        # Enable the PA output.
        GPIO.output(DVB_ENABLE_RELAY, True)
        logging.info("PA Switched to ON.")
    else:
        # We are not in a safe state to transmit. Shutdown.

        # Disable PA.
        GPIO.output(DVB_ENABLE_RELAY, False)
        logging.info("PA Switched to OFF.")

        # Stop DVBSDR.
        # TODO: Decide if we really want to stop DVBSDR. It only saves ~1W of heat dissipation...
        dvbsdr_stop()


    time.sleep(LOOP_TIMER)




def main():
    # Read command-line arguments
    parser = argparse.ArgumentParser(description="Project Horus DVB-S Payload Watchdog", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--debuglog", type=str, default="debug.log", help="Write debug log to this file.")
    parser.add_argument("-v", "--verbose", action="store_true", default=False, help="Verbose output (set logging level to DEBUG)")
    args = parser.parse_args()

    if args.verbose:
        logging_level = logging.DEBUG
    else:
        logging_level = logging.INFO

    # Set up logging
    logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s', filename=args.debuglog, level=logging_level)
    stdout_format = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(stdout_format)
    logging.getLogger().addHandler(stdout_handler)

    logging.info("Starting up DVB-S Watchdog.")

    # Setup GPIO
    # All pin definitions are in Broadcom format.
    GPIO.setmode(GPIO.BCM)

    GPIO.setup(DVB_ENABLE_RELAY, GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(DVB_ENABLE_SWITCH, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    logging.info("GPIO Configured.")

    try:
        while True:
            loop()
    except KeyboardInterrupt:
        logging.info("Exiting...")
        pass



if __name__ == "__main__":
    main()