import pyqtgraph as pg
from PyQt4 import QtCore,QtGui
import os
PATH = "./resources/"


class PicButton(QtGui.QPushButton):
    def __init__(self,iconName,size,checkable = False):
        super(PicButton, self).__init__()
        self.setStyleSheet(
            "QPushButton:checked {background-color: QLinearGradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #eef, stop: 1 #ccf)}")
        self.setCheckable(checkable)
        self.setMaximumWidth(size)
        self.setMinimumWidth(size)
        self.setMaximumHeight(size)
        self.setMinimumHeight(size)
        self.setIconSize( QtCore.QSize(0.95*size, 0.95*size))
        self.setIcon(iconName)


    def setIcon(self,iconName):
        super(PicButton, self).setIcon(QtGui.QIcon(PATH+iconName))



class PicSpinBox(pg.SpinBox):
    def __init__(self, iconName, step=0.01,value=0, integer = False, parent=None):
        value = float(value)
        super(PicSpinBox, self).__init__(parent,value=value,int=integer,step=step)
        self.pic = QtGui.QToolButton(self)
        self.pic.setIcon(QtGui.QIcon(PATH+iconName))
        self.pic.setStyleSheet('border: 0px; padding: 0px;')
        self.pic.setCursor(QtCore.Qt.ArrowCursor)

        frameWidth = self.style().pixelMetric(QtGui.QStyle.PM_DefaultFrameWidth)
        buttonSize = self.pic.sizeHint()

        self.setStyleSheet('QLineEdit {padding-right: %dpx; }' % (buttonSize.width() + frameWidth + 1))
        self.setMinimumSize(max(self.minimumSizeHint().width(), buttonSize.width() + frameWidth*2 + 2),
                            max(self.minimumSizeHint().height(), buttonSize.height() + frameWidth*2 + 2))

        self.setAlignment(QtCore.Qt.AlignLeft)

    def resizeEvent(self, event):
        buttonSize = self.pic.sizeHint()
        frameWidth = self.style().pixelMetric(QtGui.QStyle.PM_DefaultFrameWidth)
        self.pic.move(self.rect().right() - frameWidth - 1.6*buttonSize.width(),
                         (self.rect().bottom() - buttonSize.height() + 1)/2)
        super(PicSpinBox, self).resizeEvent(event)

