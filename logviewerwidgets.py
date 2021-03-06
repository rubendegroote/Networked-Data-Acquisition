from PyQt5 import QtCore, QtGui, QtWidgets
import os
IMG_PATH = './resources/'

class CollapsibleArrow(QtWidgets.QPushButton):
    clicked_sig = QtCore.pyqtSignal()
    def __init__(self, parent=None, path=None):
        super(CollapsibleArrow,self).__init__(parent=parent)

        self.isCollapsed = False
        self.setMaximumSize(24, 24)
        self.setStyleSheet("QFrame {\
        background-color: QLinearGradient( x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #44a, stop: 1 #66c);\
        border-top: 1px solid rgba(192, 192, 192, 255);\
        border-left: 1px solid rgba(192, 192, 192, 255);\
        border-right: 1px solid rgba(32, 32, 32, 255);\
        border-bottom: 1px solid rgba(64, 64, 64, 255);\
        margin: 0px, 0px, 0px, 0px;\
        padding: 0px, 0px, 0px, 0px;}\
        QFrame:hover {background-color: QLinearGradient( x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #44a, stop: 1 #66c);\
        }")
        self.arrowNameTrue = IMG_PATH + 'minimizeBlue.png'
        self.arrowNameFalse = IMG_PATH + 'maximizeBlue.png'

        self.setToolTip('Click to maximize/minimize.')

    def setArrow(self, arrowDir=True):
        if arrowDir:
            # self.setIcon(QtGui.QIcon(self.arrowNameTrue))
            self.isCollapsed = True
        else:
            # self.setIcon(QtGui.QIcon(self.arrowNameFalse))
            self.isCollapsed = False

    def mousePressEvent(self, event):
        self.clicked_sig.emit()
        return super(CollapsibleArrow, self).mousePressEvent(event)


class TitleLabel(QtWidgets.QLabel):
    def __init__(self, parent=None, text=''):
        super(TitleLabel,self).__init__(parent=parent, text=text)
        self.setStyleSheet("TitleLabel {background-color: rgba(0, 0, 0, 0);\
        color: white;\
        border-left: 0px transparent;\
        border-top: 0px transparent;\
        border-right: 0px transparent;\
        border-bottom: 0px transparent;\
        }")


class TitleFrame(QtWidgets.QFrame):
    def __init__(self, parent=None, text='', path=None):
        super(TitleFrame,self).__init__(parent=parent)

        self.titleLabel = None
        self.arrow = None
        self.path = path
        self.initTitleFrame(text)

    def initArrow(self):
        self.arrow = CollapsibleArrow(self, self.path)

    def initTitleLabel(self, text):
        self.titleLabel = TitleLabel(self, text)
        self.newLabel = TitleLabel(self, 'New!')
        self.newLabel.setHidden(True)

        self.titleLabel.setMinimumHeight(24)
        self.titleLabel.setMinimumWidth(350)
        self.titleLabel.move(QtCore.QPoint(24, 0))

        self.newLabel.setMinimumHeight(24)
        self.newLabel.setMinimumWidth(350)
        self.newLabel.move(QtCore.QPoint(150, 0))

    def initTitleFrame(self, text):
        self.setContentsMargins(0, 0, 0, 0)
        self.setMinimumHeight(24)
        self.setStyleSheet("QFrame {\
        background-color: QLinearGradient( x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #44a, stop: 1 #66c);\
        border-top: 1px solid rgba(192, 192, 192, 255);\
        border-left: 1px solid rgba(192, 192, 192, 255);\
        border-right: 1px solid rgba(64, 64, 64, 255);\
        border-bottom: 1px solid rgba(64, 64, 64, 255);\
        margin: 0px, 0px, 0px, 0px;\
        padding: 0px, 0px, 0px, 0px;\
        }")

        self.initArrow()
        self.initTitleLabel(text)

    def mouseDoubleClickEvent(self, event):
        self.emit(QtCore.SIGNAL('doubleClicked()'))
        return super(TitleFrame, self).mouseDoubleClickEvent(event)


class FrameLayout(QtWidgets.QFrame):
    def __init__(self, parent=None, text=None, path=None):
        super(FrameLayout,self).__init__(parent=parent)

        self.text = text
        self.path = ''
        self.isCollapsed = False
        self.mainLayout = None
        self.titleFrame = None
        self.contentFrame = None
        self.contentLayout = None
        self.label = None
        self.arrow = None

        self.initFrameLayout()

    def text(self):
        return self.text

    def addWidget(self, widget):
        self.contentLayout.addWidget(widget)

    def initMainLayout(self):
        self.mainLayout = QtWidgets.QVBoxLayout()
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.mainLayout.setSpacing(0)
        self.setLayout(self.mainLayout)

    def initTitleFrame(self):
        self.titleFrame = TitleFrame(text=self.text, path=self.path)
        self.mainLayout.addWidget(self.titleFrame)

    def initContentFrame(self):
        self.contentFrame = QtGui.QFrame()
        self.contentFrame.setContentsMargins(0, 0, 0, 0)
        self.contentFrame.setStyleSheet("QFrame {\
        border-top: 1px solid rgba(64, 64, 64, 255);\
        border-left: 1px solid rgba(64, 64, 64, 255);\
        border-right: 1px solid rgba(192, 192, 192, 255);\
        border-bottom: 1px solid rgba(192, 192, 192, 255);\
        margin: 0px, 0px, 0px, 0px;\
        padding: 0px, 0px, 0px, 0px;\
        }")

        self.contentLayout = QtWidgets.QVBoxLayout()
        self.contentLayout.setContentsMargins(0, 0, 0, 0)
        self.contentLayout.setSpacing(0)
        self.contentFrame.setLayout(self.contentLayout)
        self.mainLayout.addWidget(self.contentFrame)

    def toggleCollapsed(self):
        if self.isCollapsed:
            self.show()
        else:
            self.collapse()

    def collapse(self):
        self.contentFrame.setVisible(False)
        self.setVisible(True)
        self.isCollapsed = True
        self.arrow.setArrow(False)

    def show(self):
        self.contentFrame.setVisible(True)
        self.isCollapsed = False
        self.arrow.setArrow(True)
        self.titleFrame.newLabel.setHidden(True)

    def setText(self, text):
        self.label.setText(text)

    def initFrameLayout(self):
        self.setContentsMargins(0, 0, 0, 0)
        self.setStyleSheet("QFrame {\
        border: 0px solid;\
        margin: 0px, 0px, 0px, 0px;\
        padding: 0px, 0px, 0px, 0px;\
        }")

        self.initMainLayout()
        self.initTitleFrame()
        self.initContentFrame()
        self.arrow = self.titleFrame.arrow
        self.label = self.titleFrame.titleLabel
        self.arrow.clicked_sig.connect(self.toggleCollapsed)


class LogEntryWidget(FrameLayout):
    submitSig = QtCore.pyqtSignal()  # emitted when the new entry is updated
    submitTagSig = QtCore.pyqtSignal()
    addFieldSig = QtCore.pyqtSignal()
    def __init__(self, text='Placeholder text', entry=None, number=0):
        super(LogEntryWidget, self).__init__(text=text, path='')

        self.entry = entry
        self.chooseColor()
        self.toggleCollapsed()
        self.number = number

        self.tags = set()
        self.selected = -1

        self.labels = {}
        self.texts = {}
        self.tags = {}

        self.visibleProp = list(self.entry[-1].keys())
        self.unEditableProp = ['Time', 'Scan Number', 'Mass']

        self.widget = QtWidgets.QWidget(self)
        self.grid = QtWidgets.QGridLayout()
        self.versionLabel = QtWidgets.QLabel('Version')
        self.versionLabel.setStyleSheet('border: 0px;')
        self.versionSelect = QtGui.QComboBox(parent=None)
        self.versionSelect.setToolTip('Choose the entry version you want to load.')
        options = [snap['Time'] for snap in self.entry]
        self.versionSelect.clear()
        self.versionSelect.addItems(options)
        self.versionSelect.setCurrentIndex(self.selected)
        self.versionSelect.currentIndexChanged.connect(self.selectDifferentVersion)
        self.grid.addWidget(self.versionLabel, 1, 0)
        self.grid.addWidget(self.versionSelect, 1, 1)

    def selectDifferentVersion(self):
        self.selected = int(self.versionSelect.currentIndex())
        self.clearFrame()
        self.createFrame()

    def createFrame(self):
        teller = 2
        
        options = [snap['Time'] for snap in self.entry]
        
        self.versionSelect.currentIndexChanged.disconnect(self.selectDifferentVersion)
        self.versionSelect.clear()
        self.versionSelect.addItems(options)
        self.versionSelect.setCurrentIndex(self.selected)
        self.versionSelect.currentIndexChanged.connect(self.selectDifferentVersion)
        
        for pkey in sorted(self.entry[self.selected].keys()):
            propname = str(pkey)
            if pkey.lower() == 'text':
                self.texts[pkey] = QtWidgets.QTextEdit()
                self.texts[pkey].setToolTip('Type here to help future analysis with your info!')
                self.texts[pkey].setText(self.entry[self.selected][pkey])
            elif pkey.lower() == 'tags':
                for tag, value in self.entry[self.selected][pkey].items():
                    self.tags[tag] = QtGui.QCheckBox(tag)
                    self.tags[tag].setChecked(value)
                    self.tags[tag].stateChanged.connect(self.confirmTags)

            elif pkey.lower() in self.unEditableProp:
                if pkey.lower() == 'time':
                    self.texts[pkey] = QtWidgets.QLabel(self.entry[self.selected][pkey])
                else:
                    self.texts[pkey] = QtWidgets.QLabel(str(self.entry[self.selected][pkey]))
                self.texts[pkey].setStyleSheet("border: 0px;")
            else:
                self.texts[pkey] = QtWidgets.QLineEdit(str(self.entry[self.selected][pkey]))
                self.texts[pkey].setToolTip('Type here to help future analysis with your info!')

            if not pkey.lower() == 'tags':
                self.labels[pkey] = QtWidgets.QLabel(text=propname)
                self.labels[pkey].setStyleSheet("border: 0px;")
                self.grid.addWidget(self.labels[pkey], teller, 0)
                self.grid.addWidget(self.texts[pkey], teller, 1)
                teller = teller + 1

        self.addTagButton = QtWidgets.QPushButton(text='Add tag')
        self.addTagButton.setToolTip('Click here to add a tag to all logbook entries.')
        self.addTagButton.clicked.connect(self.submitTagSig.emit)
        self.grid.addWidget(self.addTagButton, teller, 0)

        for box in self.tags.values():
            self.grid.addWidget(box, teller, 1)
            teller = teller + 1

        self.addFieldButton = QtWidgets.QPushButton(text='Add field')
        self.addFieldButton.setToolTip('Click here to add a field to all logbook entries.')
        self.addFieldButton.clicked.connect(self.addFieldSig.emit)
        self.grid.addWidget(self.addFieldButton, teller, 0)

        self.editButton = QtWidgets.QPushButton(text='Edit')
        self.editButton.setToolTip('Click this to edit this entry/confirm your changes.')
        self.editButton.clicked.connect(self.editEntry)
        self.grid.addWidget(self.editButton, teller, 1)

        for (key, textItem) in self.texts.items():
            try:
                textItem.setDisabled(True)
            except RuntimeError:
                pass # this sometimes points to a deleted widget if a field was added to the entry later

        self.confirmed = True
        self.widget.setLayout(self.grid)
        self.addWidget(self.widget)

    def clearFrame(self):
        for i in reversed(range(self.grid.count())):
            if i > 1:
                widget = self.grid.itemAt(i).widget()
                widget.deleteLater()
                self.grid.removeWidget(widget)
                widget.setParent(None)

    def showNew(self):
        self.titleFrame.newLabel.setVisible(True)
        self.versionSelect.setCurrentIndex(-1)

    def confirmTags(self):
        for (key, box) in self.tags.items():
            self.entry[-1]['Tags'][key] = box.isChecked()

        self.submitSig.emit()

    def confirmEntry(self):
        for (key, textItem) in self.texts.items():
            textItem.setDisabled(True)
            try:
                newText = textItem.text()
            except AttributeError:
                newText = textItem.toPlainText()

            if key == 'Time':
                pass
            else:
                self.entry[-1][key] = newText

        for (key, box) in self.tags.items():
            box.setDisabled(True)
            self.entry[-1]['Tags'][key] = box.isChecked()

        self.confirmed = True

        self.editButton.setText('Edit')
        self.editButton.clicked.disconnect(self.confirmEntry)
        self.editButton.clicked.connect(self.editEntry)

        self.submitSig.emit()

    def editEntry(self):
        for text in self.texts.values():
            text.setEnabled(True)

        for box in self.tags.values():
            box.setEnabled(True)

        self.confirmed = False

        self.editButton.setText('Confirm')
        self.editButton.clicked.disconnect(self.editEntry)
        self.editButton.clicked.connect(self.confirmEntry)

    def getEntry(self):
        return self.entry

    def chooseColor(self):
        IMG_PATH = "\\\\cern.ch\\dfs\\Users\\c\\CRIS\\Documents\\Networked-Data-Acquisition\\resources\\"

        self.titleFrame.setStyleSheet("QFrame {\
        background-color: QLinearGradient( x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #43aa44, stop: 1 #66cc66);\
        border-top: 1px solid rgba(192, 192, 192, 255);\
        border-left: 1px solid rgba(192, 192, 192, 255);\
        border-right: 1px solid rgba(64, 64, 64, 255);\
        border-bottom: 1px solid rgba(64, 64, 64, 255);\
        margin: 0px, 0px, 0px, 0px;\
        padding: 0px, 0px, 0px, 0px;\
        }")

        self.arrow.setStyleSheet("QFrame {\
        background-color: QLinearGradient( x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #43aa44, stop: 1 #66cc66);\
        border-top: 1px solid rgba(192, 192, 192, 255);\
        border-left: 1px solid rgba(192, 192, 192, 255);\
        border-right: 1px solid rgba(32, 32, 32, 255);\
        border-bottom: 1px solid rgba(64, 64, 64, 255);\
        margin: 0px, 0px, 0px, 0px;\
        padding: 0px, 0px, 0px, 0px;}\
        QFrame:hover {background-color: QLinearGradient( x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #43aa44, stop: 1 #66cc66);\
        }")

        self.arrow.arrowNameTrue = IMG_PATH + 'minimizeGreen.png'
        self.arrow.arrowNameFalse = IMG_PATH + 'maximizeGreen.png'
