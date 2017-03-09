import os,sys
import configparser
import subprocess
from backend.Device import Device
from backend.BaseDevice import BaseDevice
from multiprocessing import freeze_support
import time
from killpython import kill_all_python

def main():
    freeze_support()
    this_pc = sys.argv[1]

    kill_all_python()

    CONFIG_PATH = os.getcwd() + "\\Config files\\config.ini"
    config_parser = configparser.ConfigParser()
    config_parser.read(CONFIG_PATH)


    for key in config_parser['IPs devices']:
        if config_parser['IPs devices'][key] == this_pc:
            print(key)
            subprocess.Popen('python launch device {}'.format(key))
            # time.sleep(5)

    subprocess.Popen('python launch data_server')
    # time.sleep(5)
    subprocess.Popen('python launch controller')
    # time.sleep(5)
    subprocess.Popen('python launch_ui controller')
    time.sleep(10)

if __name__ == '__main__':
    main()

