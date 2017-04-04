import os,sys
import configparser
import subprocess
from multiprocessing import freeze_support
import time
from config.absolute_paths import CONFIG_PATH

def main():
    freeze_support()
    this_pc =  os.environ['COMPUTERNAME']

    print(this_pc)

    config_parser = configparser.ConfigParser()
    config_parser.read(CONFIG_PATH)


    for key in config_parser['IPs devices']:
        if config_parser['IPs devices'][key] == this_pc:
            print(key)
            subprocess.Popen('python launch device {}'.format(key))
            # time.sleep(5)
    for key in config_parser['IPs']:
        if config_parser['IPs'][key] == this_pc:
            print(key)
            subprocess.Popen('python launch {}'.format(key))

if __name__ == '__main__':
    main()

