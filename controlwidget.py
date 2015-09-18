from PyQt4 import QtCore, QtGui

class ControlWidgets(dict):
    def __init__(self):
        super(ControlWidgets,self).__init__()

    def update(self,track,info):
        for key,val in info.items():
            self[key].update(val)

class ControlWidget(QtGui.QWidget):
    refresh_changed = QtCore.Signal(tuple)
    lock_etalon_sig = QtCore.Signal(tuple)
    etalon_value_sig = QtCore.Signal(tuple)
    lock_cavity_sig = QtCore.Signal(tuple)
    cavity_value_sig = QtCore.Signal(tuple)
    lock_wavelength_sig = QtCore.Signal(tuple)
    lock_ecd_sig = QtCore.Signal(tuple)
    def __init__(self, name):
        super(ControlWidget, self).__init__()
        self.name = name
        layout = QtGui.QGridLayout(self)

        layout.addWidget(QtGui.QLabel('Refresh rate (ms)'),0,0)
        self.refresh_field = QtGui.QSpinBox()
        self.refresh_field.setRange(1,10**4)
        self.refresh_field.valueChanged.connect(self.emit_refresh_change)
        layout.addWidget(self.refresh_field,0,1)

        # do this with subclassing later
        if name == 'M2':
            layout.addWidget(QtGui.QLabel("Etalon voltage"),2,0)
            self.ref_cavity_value = QtGui.QDoubleSpinBox()
            self.ref_cavity_value.setDecimals(4)
            self.ref_cavity_value.setSingleStep(0.01)
            self.ref_cavity_value.setRange(0,100)
            layout.addWidget(self.ref_cavity_value,2,1)

            self.etalon_locked = False
            self.lock_etalon_button = QtGui.QPushButton("Lock Etalon")
            self.lock_etalon_button.clicked.connect(self.emit_lock_etalon)
            layout.addWidget(self.lock_etalon_button,2,2)

            layout.addWidget(QtGui.QLabel("Ref. cavity coarse"),3,0)
            self.ref_cavity_value = QtGui.QDoubleSpinBox()
            self.ref_cavity_value.setDecimals(4)
            self.ref_cavity_value.setSingleStep(0.01)
            self.ref_cavity_value.setRange(0,100)
            layout.addWidget(self.ref_cavity_value,3,1)

            self.cavity_locked = False
            self.lock_cavity_button = QtGui.QPushButton("Lock Cavity")
            self.lock_cavity_button.clicked.connect(self.emit_lock_cavity)
            layout.addWidget(self.lock_cavity_button,3,2)

            self.wavelength_locked = False
            self.lock_wavelength_button = QtGui.QPushButton("Lock to wavemeter")
            self.lock_wavelength_button.clicked.connect(self.emit_lock_wavelength)
            layout.addWidget(self.lock_wavelength_button,4,0)

            self.ecd_locked = False
            self.lock_ecd_button = QtGui.QPushButton("Lock doubler")
            self.lock_ecd_button.clicked.connect(self.emit_lock_ecd)
            layout.addWidget(self.lock_ecd_button,4,2)

    def update(self,info):
        print(info)
        self.etalon_locked = info['etalon_lock'] == 'on'
        if self.etalon_locked:
            self.lock_etalon_button.setText('Unlock etalon')
        else:
            self.lock_etalon_button.setText('Lock etalon')

        self.cavity_locked = info['cavity_lock'] == 'on'
        if self.cavity_locked:
            self.lock_cavity_button.setText('Unlock cavity')
        else:
            self.lock_cavity_button.setText('Lock cavity')

        self.wavelength_locked = info['wavelength_lock']
        if self.wavelength_locked:
            self.lock_wavelength_button.setText('Unlock wavelength')
        else:
            self.lock_wavelength_button.setText('Lock wavelength')

        self.ecd_locked = info['ecd_lock'] == 'on'
        if self.ecd_locked:
            self.lock_ecd_button.setText('Unlock Doubler')
        else:
            self.lock_ecd_button.setText('Lock Doubler')

    def emit_refresh_change(self):
        self.refresh_changed.emit((self.name,int(self.refresh_field.value())))

    def emit_lock_etalon(self):
        self.lock_etalon_sig.emit((self.name,not self.etalon_locked))

    def emit_set_etalon(self):
        etalon_value = float(self.ref_etalon_value.value())
        self.etalon_value_sig.emit((self.name,etalon_value))

    def emit_lock_cavity(self):
        self.lock_cavity_sig.emit((self.name,not self.cavity_locked))

    def emit_set_cavity(self):
        cavity_value = float(self.ref_cavity_value.value())
        self.cavity_value_sig.emit((self.name,cavity_value))

    def emit_lock_wavelength(self):
        self.lock_wavelength_sig.emit((self.name,not self.wavelength_locked))

    def emit_lock_ecd(self):
        self.lock_ecd_sig.emit((self.name,not self.ecd_locked))
