import time
import numpy as np
import can
import threading
import struct
import traceback
from collections import OrderedDict

from .hardware import format,BaseHardware

ini = open('.\\Config files\\beamline_config.ini','rb')
data = np.genfromtxt(ini,delimiter = '\t',dtype=str)
supply_names = list(data.T[0])
modules = list(data.T[1])
channels = list(data.T[2])

modules_id_even={'0':0x200, '1':0x208, '2':0x210, '3':0x218, '4':0x220, '5':0x228, '6':0x230, '7':0x238, 'c':0x610}
modules_id_odd={'0':0x201, '1':0x209, '2':0x211, '3':0x219, '4':0x221, '5':0x229, '6':0x231, '7':0x239}

supplies = OrderedDict()
for n,m,c in zip(supply_names,modules,channels):
    supplies[n] = (modules_id_even[str(m)],
                   modules_id_odd[str(m)],
                   int(c))

this_format = format + tuple(supplies.keys())
write_params = []

class Hardware(BaseHardware):
    def __init__(self):
        super(Hardware,self).__init__(name = 'Beamline',
                                  format=this_format,
                                  write_params = write_params,
                                  refresh_time=200)

        self.received = {}
        self.previous = supplies # quick and dirty init

        self.supplies = supplies
        self.used_modules_even = set([v[0] for v in supplies.values()])
        self.used_modules_odd = set([v[1] for v in supplies.values()])
        
    def hex_to_float(self,h):
        return struct.unpack('!f', bytes.fromhex(h))[0]

    def float_to_hex(self,f):
        h=hex(struct.unpack('<I', struct.pack('<f', f))[0])
        return h.ljust(10, '0')

    def dec_array_to_hex(self,d):
        return [format(x,'0x') for x in d]

    def dec_array_to_hex_j(self,d):
        return ''.join("{0:0{1}x}".format(x,2) for x in d)

    def dec_array_to_bin(self,d):
        return ["{0:08b}".format(x) for x in d]
    
    def CAN_bus_update(self):
        i=0
        while True:
            print("restarting CAN_bus_update")
            try:
                for msge in self.bus:
                    if int(msge.dlc)>3:
                        tup = msge.arbitration_id,msge.data[0],msge.data[1],msge.data[2]
                        self.received[tup]=[msge.dlc, msge.data, msge.timestamp]
                    elif int(msge.dlc)>0:
                        tup = msge.arbitration_id,msge.data[0]
                        self.received[tup]=[msge.dlc, msge.data]
                    else:
                        self.received[msge.arbitration_id]=[msge.dlc, msge.data]
                    time.sleep(0.001)
            except Exception as e:
                print(e)
                i+=1
                print("exception while populating CANbus received array #"+str(i)+", message:")

    def query_device(self):
        while(True):
            for supply in supplies.values():
                mod_write = supply[1]
                chan = supply[2]
                command = [0x41,0x02,chan]
                msg = can.Message(arbitration_id=mod_write, data=command, extended_id=False)
                self.bus.send(msg)
                time.sleep(0.01)

    def connect_to_device(self):
        self.bus = can.interface.Bus(bitrate = 125000)

        # #power crate:
        # command=[0x41,0x00,0x01]
        # msg = can.Message(arbitration_id=0x610, data=command, extended_id=False)
        # self.bus.send(msg)

        for mod in self.used_modules_even:
            # configure ramping speed to 20 percent
            command=[0x11,0x00,0x41,0xA0,0x00,0x00]
            msg = can.Message(arbitration_id=mod, data=command, extended_id=False)
            self.bus.send(msg)

        for supply in self.supplies.values():
            #power up the supplies:
            mod = supply[0]
            chan = supply[2]
            command=[0x40,0x01,chan,0x00,0x08]
            msg = can.Message(arbitration_id=mod, data=command, extended_id=False)
            self.bus.send(msg)

        # start polling and query thread
        self.poll_thread = threading.Thread(target=self.CAN_bus_update)
        self.poll_thread.start()
        
        self.query_thread = threading.Thread(target=self.query_device)
        self.query_thread.start()

    def write_to_device(self):
        #send even
        done = True
        if not type(self.setpoint) == dict:
            # fix this properly later
            return

        for key,val in self.setpoint.items():
            if not val == self.previous[key]:
                tup = self.supplies[key]

                mod_write=int(tup[0])
                channel=int(tup[2])
                v_set=val
                h=self.float_to_hex(v_set)
                command=[0x41,0x00,channel,int(h[2:4],16),int(h[4:6],16),int(h[6:8],16),int(h[8:10],16)]

                msg = can.Message(arbitration_id=mod_write, data=command, extended_id=False)
                self.bus.send(msg)

        self.previous = self.setpoint

        return done

    def read_from_device(self):
        #receive even, send odd
        ret_list = []
        for supply in supplies.values():
            mod_read = supply[0]
            chan = supply[2]
            command=[0x41,0x02,chan]
            cont = True
            while cont:
                try:
                    tup = mod_read,command[0],command[1],command[2]
                    rec_element = self.received[tup]

                    received = rec_element[1][3:7]

                    ret_list.append(self.hex_to_float(self.dec_array_to_hex_j(received)))
                    cont = False

                except:
                    # print('error')
                    # print(traceback.format_exc())
                    pass

        return ret_list



