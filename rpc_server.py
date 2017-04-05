from xmlrpc.server import SimpleXMLRPCServer
from subprocess import Popen
import sys,ctypes
from multiprocessing import freeze_support
import os

data_server_p = None
file_server_p = None
controller_p = None

def execute_launch_device(dev):
    print('Request to launch device {} received'.format(dev))
    command = 'python launch device {}'.format(dev)
    p = Popen(command)

    return dev  

def execute_launch_data_server():
    global data_server_p
    print('Request to launch data server received')

    if data_server_p:
        data_server_p.kill()
    try:
        command = 'python launch data_server'
        data_server_p = Popen(command)
    except Exception as e:
        return False, e
    return True, ''

def execute_launch_file_server():
    global file_server_p
    print('Request to launch file server received')

    if file_server_p:
        file_server_p.kill()
    try:
        command = 'python launch file_server'
        print(command)
        file_server_p = Popen(command)
    except Exception as e:
        return False, e
    return True, ''

def execute_launch_controller():
    global controller_p
    print('Request to launch controller received')

    if controller_p:
        controller_p.kill()
    try:
        command = 'python launch controller'
        controller_p = Popen(command)
    except Exception as e:
        return False, e
    return True, ''


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


freeze_support()


os.chdir(u"C:\\Networked-data-acquisition")

server = SimpleXMLRPCServer(("0.0.0.0", 5050))
server.register_function(execute_launch_device, "execute_launch_device")
server.register_function(execute_launch_file_server, "execute_launch_file_server")
server.register_function(execute_launch_data_server, "execute_launch_data_server")
server.register_function(execute_launch_controller, "execute_launch_controller")

server.serve_forever()

