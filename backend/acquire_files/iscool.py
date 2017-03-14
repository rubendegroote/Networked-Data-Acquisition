import visa
from .hardware import format,BaseHardware

this_format = format + ('voltage',)
write_params = []

class Hardware(BaseHardware):
    def __init__(self):
        super(Hardware,self).__init__(name = 'ISCOOL',
                                  format=this_format,
                                  write_params = write_params,
                                  refresh_time=5000)

        self.settings = dict()

        self.opc = None

    def connect_to_device(self):
        rm = visa.ResourceManager()
        self.inst = rm.open_resource('TCPIP0::A-34461A-06386::inst0::INSTR')
        print(self.inst.query("*IDN?"))

        self.inst.write("CONF:VOLT:DC 10,0.00003")
        self.inst.write("TRIG:SOUR BUS")
        self.inst.write("SAMP:COUN 1")

    def read_from_device(self):
        self.inst.write("INIT")
        self.inst.write("*TRG")
        voltage=float(self.inst.query("FETC?"))
        print(voltage)

        self.ns.status_data = {'voltage':voltage}

        return [voltage]

