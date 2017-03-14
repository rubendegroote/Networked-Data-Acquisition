from .hardware import format,BaseHardware
import numpy as np
import mmap
import struct
import time
import threading
from hexdump import dump
import datetime

this_format = format + ('timestamp','energy','detector')
write_params = []
TIME_OFFSET = 1420070400 # 01/01/2015

configData = np.genfromtxt("/TapeData/DSSDataFitter/config.txt", delimiter='\t', dtype="S8,S8,S8,S8,f8,f8", names=['Det', 'Name', 'Type', 'Number', 'Slope', 'Offset'] )
Dets, Slopes, Offsets  = configData["Det"].astype(int) - 140, configData["Slope"], configData["Offset"]
Slope  = Slopes[(Dets == 1)]
print(Slope)
Offset = Offsets[(Dets == 1)]
print(Offset)

print(time.ctime())

class Hardware(BaseHardware):
    def __init__(self):
        super(Hardware,self).__init__(name = 'dss',
                                  format=this_format,
                                  write_params = write_params,
                                  refresh_time=50)

    def connect_to_device(self):
        # open the linux shm device for tapeserver at address 10205
        self.f = open('/dev/shm/SHM_110205','r')
        self.mm = mmap.mmap(self.f.fileno(), 0, mmap.MAP_PRIVATE, mmap.PROT_READ)

        # retrieve settings from the ts data header, described in tsspy.h
        (self.oset,self.cnt,self.bsize,last,self.maxcnt,none,none,none) = struct.unpack('8i',self.mm[:32])
        self.age = struct.unpack('l',self.mm[32:40])[0]-1

    def input(self):
        data_from_device = self.read_from_device()
        data = [time.time() - TIME_OFFSET - self.ns.clock_offset,
                self.ns.clock_offset,
                self.ns.scan_number,
                self.ns.mass]
        data = np.row_stack([data]*len(data_from_device))
        data = np.column_stack((data,data_from_device))
        return ([0],data)

    def read_from_device(self):
        self.start_time = time.time()
        while True:
            new_age = struct.unpack('l',self.mm[32:40])[0]-1
            
            if not self.age == new_age:
                block_ages = struct.unpack('128l',self.mm[40:1064])
                idx = block_ages.index(new_age)
                offset = self.oset+self.bsize*idx        
                block = self.mm[offset:offset+self.bsize]
                self.age = new_age
                data = interpret(self, block)
                if not len(data) == 0:
                    return data

            time.sleep(0.01)

def interpret(self, data):
    full = dump(data, size=4, sep='\t').split('\t')
    length = len(full)
    chan = []
    timestamp = []
    det = []
    i=0
   
    offset = 0
    
    last_t_0 = 0
    last_t_1 = 0

    while True:
        if i>1:    
            line = full[i*8:(i+1)*8]
            if line == []:
                break
            line = [n[2:4]+n[0:2] for n in line]
            try:
                chan.append(int(line[0],16))
                det.append(int(line[7][-1]))
                t = int(line[2]+line[3],16) * 10 * 10**-9
                timestamp.append(t)

            except Exception as e:
                pass
        i += 1

    data = np.column_stack((np.array(timestamp),np.array(chan),np.array(det))) 
    data.T[2] = np.roll(data.T[2],1)
 
    data = data[data[:,2] == 1]
    data[:,1] *= Slope 
    data[:,1] += Offset + (np.random.rand(len(data))-0.5)

    print("Alphas seen:", len(data))
    time_delta = time.time() - self.start_time 
    rate = len(data)/time_delta
    print("Rate: %.1f Hz" % rate)

    return data




