from dispatcher import Dispatcher
import sys

class Manager(Dispatcher):
    def __init__(self, artists=[], PORT=5007):
        super(Manager, self).__init__()
        self.scanNo = 0
        self.progress = 0
        self.scanning = False
        self.format = {}
        self.measuring = False

    def connector_cb(self, sender, message):
        reply_params = message['reply']['parameters']
        self.format[sender.artistName] = reply_params['format']
        if sender.scanning and reply_params['measuring'] != self.measuring:
            self.measuring = reply_params['measuring']
            if message['reply']['parameters']['measuring']:
                self.notifyAll(['Measuring', self.scanNo])
            else:
                self.notifyAll(['idling'])
                self.scanToNext()

    def resumeScan(self):
        self.scanner = self.connectors[self.resumeName]
        self.scanner.scanning = True
        self.scanPar = 'A0V'
        self.scanning = True
        self.scanNo += 1
        try:
            newEntry = {key: '' for key in self.logbook[-1][-1].keys()}
            if 'Tags' in self.logbook[-1][-1].keys():
                newEntry['Tags'] = OrderedDict()
                for t in self.logbook[-1][-1]['Tags'].keys():
                    newEntry['Tags'][t] = False
        except:
            newEntry = {}
        entry = {'Scan Number': self.scanNo,
                 'Author': 'Automatic Entry',
                 'Text': self.resumeMessage.format(name,
                                                   self.scanRange[0],
                                                   self.scanRange[-1],
                                                   len(self.scanRange),
                                                   self.tPerStep,
                                                   self.curPos)}
        for key in entry.keys():
            newEntry[key] = entry[key]
        logbooks.addEntry(self.logbook, **newEntry)
        logbooks.saveEntry(self.logbookPath, self.logbook, -1)
        self.notifyAllLogs(
                ['Notify', self.logbook[-1], len(self.logbook) - 1])
        self.scanParser['scanprogress'] = {'scanno': self.scanNo}
        self.progressParser['progress'] = {'name': self.resumeName}
        with open('ManagerScan.ini', 'w') as scanfile:
            self.scanParser.write(scanfile)
        self.scanToNext()

    def scan(self, scanInfo):
        try:
            name, self.scanPar = scanInfo[0].split(':')
            self.scanner = self.connectors[name]
        except:
            logging.error('Could not start scan, no connection with Artist')
        self.scanner.scanning = True
        self.curPos = 0
        self.scanRange = scanInfo[1]
        self.tPerStep = scanInfo[2]
        self.scanning = True
        self.scanNo += 1
        self.scanParser['scanprogress'] = {'scanno': self.scanNo}
        self.progressParser['progress'] = {'name': name}
        try:
            newEntry = {key: '' for key in self.logbook[-1][-1].keys()}
            if 'Tags' in self.logbook[-1][-1].keys():
                newEntry['Tags'] = OrderedDict()
                for t in self.logbook[-1][-1]['Tags'].keys():
                    newEntry['Tags'][t] = False
        except:
            newEntry = {}
        entry = {'Scan Number': self.scanNo,
                 'Author': 'Automatic Entry',
                 'Text': self.startMessage.format(name,
                                                   self.scanRange[0],
                                                   self.scanRange[-1],
                                                   len(self.scanRange),
                                                   self.tPerStep)}
        for key in entry.keys():
            newEntry[key] = entry[key]
        logbooks.addEntry(self.logbook, **newEntry)
        logbooks.saveEntry(self.logbookPath, self.logbook, -1)
        self.notifyAllLogs(
                ['Notify', self.logbook[-1], len(self.logbook) - 1])
        with open('ManagerScan.ini', 'w') as scanfile:
            self.scanParser.write(scanfile)
        self.scanToNext()

    def setpoint(self, setpointInfo):
        name, self.scanPar = setpointInfo[0].split(':')
        self.scanner = self.connectors[name]
        value = setpointInfo[1]
        try:
            newEntry = {key: '' for key in self.logbook[-1][-1].keys()}
            if 'Tags' in self.logbook[-1][-1].keys():
                newEntry['Tags'] = OrderedDict()
                for t in self.logbook[-1][-1]['Tags'].keys():
                    newEntry['Tags'][t] = False
        except:
            newEntry = {}
        entry = {'Author': 'Automatic Entry',
                 'Text': self.setpointMessage.format(name, value)}
        for key in entry.keys():
            newEntry[key] = entry[key]
        logbooks.addEntry(self.logbook, **newEntry)
        logbooks.saveEntry(self.logbookPath, self.logbook, -1)
        self.notifyAllLogs(
                ['Notify', self.logbook[-1], len(self.logbook) - 1])
        self.scanner.add_instruction(
            ["Setpoint Change", self.scanPar, value])

    def stopScan(self):
        self.scanning = False
        self.scanner.scanning = False
        self.notifyAll(['idling'])

    def notifyAll(self, instruction):
        for instr in self.connectors.values():
            instr.add_instruction(instruction)

    def notifyAllLogs(self, instruction):
        for viewer in self.viewers:
            viewer.commQ.put(instruction)

    def scanToNext(self):
        if not self.scanning:
            return

        if self.curPos == len(self.scanRange):
            self.progress = 100
            self.scanning = False
            self.scanner.scanning = False
            try:
                os.remove('scanprogress.ini')
            except FileNotFoundError:
                pass
            return

        self.scanner.add_instruction(
            ["Scan Change", self.scanPar, self.scanRange[self.curPos], self.tPerStep])
        name = self.progressParser['progress']['name']
        self.progressParser['progress'] = {'curpos': self.curPos,
                                           'scanmin': self.scanRange[0],
                                           'scanmax': self.scanRange[-1],
                                           'scanlength': len(self.scanRange),
                                           'tperstep': self.tPerStep,
                                           'name': name}
        with open('scanprogress.ini', 'w') as scanprogressfile:
            self.progressParser.write(scanprogressfile)
        self.curPos += 1
        self.progress = int(self.curPos / len(self.scanRange) * 100)

def makeManager(PORT=5007):
    return Manager(PORT=PORT)


def main():
    try:
        m = makeManager(5004)
        style = "QLabel { background-color: green }"
        e=''
    except Exception as e:
        style = "QLabel { background-color: red }"

    from PyQt4 import QtCore,QtGui
    # Small visual indicator that this is running
    app = QtGui.QApplication(sys.argv)
    w = QtGui.QWidget()

    w.setWindowTitle('Manager')
    layout = QtGui.QGridLayout(w)
    label = QtGui.QLabel(e)
    label.setStyleSheet(style)
    layout.addWidget(label)
    w.show()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
