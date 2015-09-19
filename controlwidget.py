from PyQt4 import QtCore, QtGui

class ControlWidgets(QtCore.QObject):
    artist_missing = QtCore.Signal(str)
    def __init__(self):
        super(ControlWidgets,self).__init__()
        self.controls = {}

    def update(self,track,info):
        for key in info.keys():
            try:
                self.controls[key].update(info)
            except KeyError:
                self.artist_missing.emit(key)

class ControlWidget(QtGui.QWidget):
    prop_changed_sig = QtCore.Signal(tuple)
    refresh_changed_sig = QtCore.Signal(tuple)
    lock_etalon_sig = QtCore.Signal(tuple)
    etalon_value_sig = QtCore.Signal(tuple)
    lock_cavity_sig = QtCore.Signal(tuple)
    cavity_value_sig = QtCore.Signal(tuple)
    lock_wavelength_sig = QtCore.Signal(tuple)
    lock_ecd_sig = QtCore.Signal(tuple)
    wavenumber_sig = QtCore.Signal(dict)
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
            layout.addWidget(QtGui.QLabel('Proportional stab.'),0,2)
            self.prop_field = QtGui.QSpinBox()
            self.prop_field.setRange(1,500)
            self.prop_field.valueChanged.connect(self.emit_prop_change)
            layout.addWidget(self.prop_field,0,3)

            layout.addWidget(QtGui.QLabel("Etalon Tune"),1,2)
            self.etalon_value = QtGui.QDoubleSpinBox()
            self.etalon_value.setDecimals(4)
            self.etalon_value.setSingleStep(0.01)
            self.etalon_value.setRange(0,100)
            layout.addWidget(self.etalon_value,1,4)
            self.setEtalonButton = QtGui.QPushButton("Set")
            self.setEtalonButton.clicked.connect(self.emit_set_etalon)
            layout.addWidget(self.setEtalonButton,1,5)

            self.etalon_label = QtGui.QLabel()
            layout.addWidget(self.etalon_label,1,3)

            self.etalon_locked = False
            self.lock_etalon_button = QtGui.QPushButton("Lock Etalon")
            self.lock_etalon_button.clicked.connect(self.emit_lock_etalon)
            layout.addWidget(self.lock_etalon_button,1,6)

            layout.addWidget(QtGui.QLabel("Cavity Tune"),2,2)
            self.ref_cavity_value = QtGui.QDoubleSpinBox()
            self.ref_cavity_value.setDecimals(4)
            self.ref_cavity_value.setSingleStep(0.01)
            self.ref_cavity_value.setRange(0,100)
            layout.addWidget(self.ref_cavity_value,2,4)
            self.setCavityButton = QtGui.QPushButton("Set")
            self.setCavityButton.clicked.connect(self.emit_set_cavity)
            layout.addWidget(self.setCavityButton,2,5)

            self.cavity_label = QtGui.QLabel()
            layout.addWidget(self.cavity_label,2,3)

            self.cavity_locked = False
            self.lock_cavity_button = QtGui.QPushButton("Lock Cavity")
            self.lock_cavity_button.clicked.connect(self.emit_lock_cavity)
            layout.addWidget(self.lock_cavity_button,2,6)

            layout.addWidget(QtGui.QLabel("Wavenumber"),4,2)
            self.wavenumber_value = QtGui.QLineEdit()
            layout.addWidget(self.wavenumber_value,4,4)
            self.setWaveButton = QtGui.QPushButton("Set")
            self.setWaveButton.clicked.connect(self.emit_set_wavenumber)
            layout.addWidget(self.setWaveButton,4,5)

            self.wavelength_locked = False
            self.lock_wavelength_button = QtGui.QPushButton("Lock to wavemeter")
            self.lock_wavelength_button.clicked.connect(self.emit_lock_wavelength)
            layout.addWidget(self.lock_wavelength_button,4,6)

            self.ecd_locked = False
            self.lock_ecd_button = QtGui.QPushButton("Lock doubler")
            self.lock_ecd_button.clicked.connect(self.emit_lock_ecd)
            layout.addWidget(self.lock_ecd_button,3,6)

            self.etalon_voltage_label = QtGui.QLabel()
            layout.addWidget(QtGui.QLabel('Etalon voltage'),1,0)
            layout.addWidget(self.etalon_voltage_label,1,1)

            self.cavity_voltage_label = QtGui.QLabel()
            layout.addWidget(QtGui.QLabel('Cavity voltage'),2,0)
            layout.addWidget(self.cavity_voltage_label,2,1)

            self.ecd_voltage_label = QtGui.QLabel()
            layout.addWidget(QtGui.QLabel('ECD voltage'),3,0)
            layout.addWidget(self.ecd_voltage_label,3,1)

            layout.addWidget(QtGui.QLabel('Laser wavenumber'),4,0)
            self.wave_1 = QtGui.QLabel()
            layout.addWidget(self.wave_1,4,1)

        elif name == 'wavemeter':
            layout.addWidget(QtGui.QLabel('Laser wavenumber'),1,0)
            self.wave_1 = QtGui.QLabel()
            layout.addWidget(self.wave_1,1,1)

            layout.addWidget(QtGui.QLabel('HeNe wavenumber'),2,0)
            self.wave_2 = QtGui.QLabel()
            layout.addWidget(self.wave_2,2,1)

    def update(self,info):
        if self.name == 'M2':
            M2_info = info['M2']
            self.etalon_locked = M2_info['etalon_lock'] == 'on'
            if self.etalon_locked:
                self.lock_etalon_button.setText('Unlock etalon')
            else:
                self.lock_etalon_button.setText('Lock etalon')

            self.cavity_locked = M2_info['cavity_lock'] == 'on'
            if self.cavity_locked:
                self.lock_cavity_button.setText('Unlock cavity')
            else:
                self.lock_cavity_button.setText('Lock cavity')

            self.wavelength_locked = M2_info['wavelength_lock']
            if self.wavelength_locked:
                self.lock_wavelength_button.setText('Unlock wavelength')
            else:
                self.lock_wavelength_button.setText('Lock wavelength')

            self.ecd_locked = M2_info['ecd_lock'] == 'on'
            if self.ecd_locked:
                self.lock_ecd_button.setText('Unlock Doubler')
            else:
                self.lock_ecd_button.setText('Lock Doubler')

            self.cavity_label.setText("{0:.4f}".format(M2_info['cavity_value']))
            self.etalon_label.setText("{0:.4f}".format(M2_info['etalon_value']))
            self.etalon_voltage_label.setText("{0:.4f}".format(M2_info['etalon_voltage'][0]))
            self.cavity_voltage_label.setText("{0:.4f}".format(M2_info['resonator_voltage'][0]))
            self.ecd_voltage_label.setText("{0:.4f}".format(M2_info['ecd_voltage'][0]))

            try:
                wavemeter_info = info['wavemeter']
                self.wave_1.setText(str("{0:.5f}".format(wavemeter_info['wavenumber_wsu_1'])))
            except KeyError:
                pass

        elif self.name == 'wavemeter':
            wavemeter_info = info['wavemeter']
            self.wave_1.setText(str("{0:.5f}".format(wavemeter_info['wavenumber_wsu_1'])))
            self.wave_2.setText(str("{0:.5f}".format(wavemeter_info['wavenumber_wsu_2'])))

    def emit_refresh_change(self):
        self.refresh_changed_sig.emit((self.name,int(self.refresh_field.value())))

    def emit_prop_change(self):
        self.prop_changed_sig.emit((self.name,int(self.prop_field.value())))

    def emit_lock_etalon(self):
        self.lock_etalon_sig.emit((self.name,not self.etalon_locked))

    def emit_set_etalon(self):
        etalon_value = float(self.etalon_value.value())
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

    def emit_set_wavenumber(self):
        wavenumber = float(self.wavenumber_value.text())
        self.wavenumber_sig.emit({'artist':['M2'],
                                  'parameter':["wavenumber"],
                                  'setpoint': [wavenumber]})