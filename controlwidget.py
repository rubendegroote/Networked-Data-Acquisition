from PyQt4 import QtCore, QtGui
from spin import Spin

class ControlWidget(QtGui.QWidget):
    prop_changed_sig = QtCore.pyqtSignal(tuple)
    lock_etalon_sig = QtCore.pyqtSignal(tuple)
    etalon_value_sig = QtCore.pyqtSignal(tuple)
    lock_cavity_sig = QtCore.pyqtSignal(tuple)
    cavity_value_sig = QtCore.pyqtSignal(tuple)
    lock_wavelength_sig = QtCore.pyqtSignal(tuple)
    lock_ecd_sig = QtCore.pyqtSignal(tuple)
    int_changed_sig = QtCore.pyqtSignal(tuple)
    diff_changed_sig = QtCore.pyqtSignal(tuple)
    wavenumber_sig = QtCore.pyqtSignal(dict)
    calibrate_sig = QtCore.pyqtSignal(dict)
    setpoint_reached_sig = QtCore.pyqtSignal(bool)
    setpoint_value_sig = QtCore.pyqtSignal(str)
    def __init__(self):
        super(ControlWidget, self).__init__()
        layout = QtGui.QGridLayout(self)

        label = QtGui.QLabel('M2 Controls')
        font = QtGui.QFont("Helvetica", 16, QtGui.QFont.Bold) 
        label.setFont(font)
        layout.addWidget(label,0,0,1,5)

        self.M2 = M2_UI()
        self.M2.prop_field.valueChanged.connect(self.emit_prop_change_M2)
        self.M2.etalon_value.sigValueChanging.connect(self.emit_set_etalon)
        self.M2.lock_etalon_button.clicked.connect(self.emit_lock_etalon)
        self.M2.ref_cavity_value.sigValueChanging.connect(self.emit_set_cavity)
        self.M2.lock_cavity_button.clicked.connect(self.emit_lock_cavity)
        self.M2.wavenumber_value.sigValueChanging.connect(self.emit_set_wavenumber_M2)
        self.M2.lock_wavelength_button.clicked.connect(self.emit_lock_wavelength_M2)
        self.M2.lock_ecd_button.clicked.connect(self.emit_lock_ecd)
        layout.addWidget(self.M2,1,0)

        label = QtGui.QLabel('Matisse Controls')
        font = QtGui.QFont("Helvetica", 16, QtGui.QFont.Bold) 
        label.setFont(font)
        layout.addWidget(label,2,0,1,5)

        self.Matisse = Matisse_UI()
        self.Matisse.prop_field.valueChanged.connect(self.emit_prop_change_Matisse)
        self.Matisse.int_field.valueChanged.connect(self.emit_int_change_Matisse)
        self.Matisse.diff_field.valueChanged.connect(self.emit_diff_change_Matisse)
        self.Matisse.lock_wavelength_button.clicked.connect(self.emit_lock_wavelength_Matisse)
        self.Matisse.wavenumber_value.sigValueChanging.connect(self.emit_set_wavenumber_Matisse)

        layout.addWidget(self.Matisse,3,0)

        label = QtGui.QLabel('WSU2 controls')
        font = QtGui.QFont("Helvetica", 16, QtGui.QFont.Bold) 
        label.setFont(font)
        layout.addWidget(label,4,0,1,5)

        self.cal_button = QtGui.QPushButton('calibrate')
        self.cal_button.clicked.connect(self.emit_calibrate_sig)
        layout.addWidget(self.cal_button,5,0)

        label = QtGui.QLabel('WS6 controls')
        font = QtGui.QFont("Helvetica", 16, QtGui.QFont.Bold) 
        label.setFont(font)
        layout.addWidget(label,6,0,1,5)

        self.cal_button_pdl = QtGui.QPushButton('calibrate pdl')
        self.cal_button_pdl.clicked.connect(self.emit_calibrate_sig)
        layout.addWidget(self.cal_button_pdl,7,0)

        spacer = QtGui.QSpacerItem(20,40,QtGui.QSizePolicy.Minimum,QtGui.QSizePolicy.Expanding)
        layout.addItem(spacer,10,1,1,4)

    def update(self,track,info):
        if not 'wavemeter' in info.keys():
            self.cal_button.setDisabled(True)
        else:
            self.cal_button.setEnabled(True)
        if not 'wavemeter_pdl' in info.keys():
            self.cal_button_pdl.setDisabled(True)
        else:
            self.cal_button_pdl.setEnabled(True)
        if not 'M2' in info.keys():
            self.M2.setDisabled(True)
        else:
            self.M2.setEnabled(True)
        if not 'Matisse' in info.keys():
            self.Matisse.setDisabled(True)
        else:
            self.Matisse.setEnabled(True)


        try:
            M2_info = info['M2']

            self.etalon_locked = M2_info['etalon_lock'] == 'on'
            if self.etalon_locked:
                self.M2.lock_etalon_button.setText('Unlock etalon')
            else:
                self.M2.lock_etalon_button.setText('Lock etalon')

            self.cavity_locked = M2_info['cavity_lock'] == 'on'
            if self.cavity_locked:
                self.M2.lock_cavity_button.setText('Unlock cavity')
            else:
                self.M2.lock_cavity_button.setText('Lock cavity')

            self.M2.wavelength_locked = M2_info['wavelength_lock']
            if self.M2.wavelength_locked:
                self.M2.lock_wavelength_button.setText('Unlock wavelength')
            else:
                self.M2.lock_wavelength_button.setText('Lock wavelength')

            self.ecd_locked = M2_info['ecd_lock'] == 'on'
            if self.ecd_locked:
                self.M2.lock_ecd_button.setText('Unlock Doubler')
            else:
                self.M2.lock_ecd_button.setText('Lock Doubler')

            self.M2.cavity_label.setText("{0:.4f}".format(M2_info['cavity_value']))
            self.M2.etalon_label.setText("{0:.4f}".format(M2_info['etalon_value']))
            self.M2.etalon_voltage_label.setText("{0:.4f}".format(M2_info['etalon_voltage'][0]))
            self.M2.cavity_voltage_label.setText("{0:.4f}".format(M2_info['resonator_voltage'][0]))
            self.M2.ecd_voltage_label.setText("{0:.4f}".format(M2_info['ecd_voltage'][0]))
        except:
            pass

        try:
            Matisse_info = info['Matisse']
            self.Matisse.wavelength_locked = Matisse_info['Stabilization Active']
            if self.Matisse.wavelength_locked:
                self.Matisse.lock_wavelength_button.setText('Unlock wavelength')
            else:
                self.Matisse.lock_wavelength_button.setText('Lock wavelength')

            # self.Matisse.prop_field.valueChanged.disconnect(self.emit_prop_change_Matisse)
            # self.Matisse.int_field.valueChanged.disconnect(self.emit_int_change_Matisse)
            # self.Matisse.diff_field.valueChanged.disconnect(self.emit_diff_change_Matisse)

            # self.Matisse.prop_field.setValue(int(Matisse_info['P']))
            # self.Matisse.int_field.setValue(int(Matisse_info['I']))
            # self.Matisse.diff_field.setValue(int(Matisse_info['D']))

            # self.Matisse.prop_field.valueChanged.connect(self.emit_prop_change_Matisse)
            # self.Matisse.int_field.valueChanged.connect(self.emit_int_change_Matisse)
            # self.Matisse.diff_field.valueChanged.connect(self.emit_diff_change_Matisse)

        except:
            pass

    def emit_prop_change_M2(self):
        self.prop_changed_sig.emit(('M2',int(self.M2.prop_field.value())))

    def emit_lock_etalon(self):
        self.lock_etalon_sig.emit(('M2',not self.etalon_locked))

    def emit_set_etalon(self):
        self.etalon_value_sig.emit(('M2',self.M2.etalon_value.value))

    def emit_lock_cavity(self):
        self.lock_cavity_sig.emit(('M2',not self.cavity_locked))

    def emit_set_cavity(self):
        self.cavity_value_sig.emit(('M2',self.M2.ref_cavity_value.value))

    def emit_lock_wavelength_M2(self):
        self.lock_wavelength_sig.emit(('M2',not self.M2.wavelength_locked))

    def emit_lock_wavelength_Matisse(self):
        self.lock_wavelength_sig.emit(('Matisse',not self.Matisse.wavelength_locked))

    def emit_prop_change_Matisse(self):
        self.prop_changed_sig.emit(('Matisse',int(self.Matisse.prop_field.value())))

    def emit_int_change_Matisse(self):
        self.int_changed_sig.emit(('Matisse',int(self.Matisse.int_field.value())))

    def emit_diff_change_Matisse(self):
        self.diff_changed_sig.emit(('Matisse',int(self.Matisse.diff_field.value())))

    def emit_lock_ecd(self):
        self.lock_ecd_sig.emit(('M2',not self.ecd_locked))

    def emit_set_wavenumber_M2(self):
        wavenumber = self.M2.wavenumber_value.value
        self.wavenumber_sig.emit({'device':'M2',
                                  'parameter':"wavenumber",
                                  'setpoint': [wavenumber]})

    def emit_set_wavenumber_Matisse(self):
        wavenumber = self.Matisse.wavenumber_value.value
        self.wavenumber_sig.emit({'device':'Matisse',
                                  'parameter':"wavenumber",
                                  'setpoint': [wavenumber]})

    def emit_calibrate_sig(self):
        if self.sender() == self.cal_button:
            self.calibrate_sig.emit({'device':'wavemeter'})
        elif self.sender() == self.cal_button_pdl:
            self.calibrate_sig.emit({'device':'wavemeter_pdl'})

class M2_UI(QtGui.QWidget):
    def __init__(self):
        super(M2_UI,self).__init__()

        layout = QtGui.QGridLayout(self)

        layout.addWidget(QtGui.QLabel('Proportional stab.'),0,0)
        self.prop_field = QtGui.QSpinBox()
        self.prop_field.setRange(1,500)
        layout.addWidget(self.prop_field,0,1)

        layout.addWidget(QtGui.QLabel("Etalon Tune"),1,2)
        self.etalon_value = Spin(50.0000,0,100,sig_figs=2)
        layout.addWidget(self.etalon_value,1,4)

        self.etalon_label = QtGui.QLabel()
        layout.addWidget(self.etalon_label,1,3)

        self.etalon_locked = False
        self.lock_etalon_button = QtGui.QPushButton("Lock Etalon")
        layout.addWidget(self.lock_etalon_button,1,6)

        layout.addWidget(QtGui.QLabel("Cavity Tune"),2,2)
        self.ref_cavity_value = Spin(50.0000,0,100)
        layout.addWidget(self.ref_cavity_value,2,4)

        self.cavity_label = QtGui.QLabel()
        layout.addWidget(self.cavity_label,2,3)

        self.cavity_locked = False
        self.lock_cavity_button = QtGui.QPushButton("Lock Cavity")
        layout.addWidget(self.lock_cavity_button,2,6)

        layout.addWidget(QtGui.QLabel("target wavenumber"),4,0)
        self.wavenumber_value = Spin(11836.0000,0,10**5)
        layout.addWidget(self.wavenumber_value,4,1)

        self.wavelength_locked = False
        self.lock_wavelength_button = QtGui.QPushButton("Lock to wavemeter")
        layout.addWidget(self.lock_wavelength_button,4,6)

        self.ecd_locked = False
        self.lock_ecd_button = QtGui.QPushButton("Lock doubler")
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

class Matisse_UI(QtGui.QWidget):
    def __init__(self):
        super(Matisse_UI,self).__init__()

        layout = QtGui.QGridLayout(self)

        layout.addWidget(QtGui.QLabel('Proportional stab.'),0,0)
        self.prop_field = QtGui.QSpinBox()
        self.prop_field.setRange(-500,500)
        layout.addWidget(self.prop_field,0,1)

        layout.addWidget(QtGui.QLabel('Integral stab.'),1,0)
        self.int_field = QtGui.QSpinBox()
        self.int_field.setRange(-500,500)
        layout.addWidget(self.int_field,1,1)

        layout.addWidget(QtGui.QLabel('Differential stab.'),2,0)
        self.diff_field = QtGui.QSpinBox()
        self.diff_field.setRange(-500,500)
        layout.addWidget(self.diff_field,2,1)

        layout.addWidget(QtGui.QLabel("Target wavenumber"),3,0)
        self.wavenumber_value = Spin(11836.0000,0,10**5)
        layout.addWidget(self.wavenumber_value,3,1)

        self.wavelength_locked = False
        self.lock_wavelength_button = QtGui.QPushButton("Lock to wavemeter")
        layout.addWidget(self.lock_wavelength_button,3,2)
