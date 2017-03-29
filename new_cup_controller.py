from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtOpenGL import QGLWidget
import sys
import random

Y_IN = 250
Y_OUT = 100

ACT_WIDTH = 20
ACT_HEIGHT = 150

BEAMLINE_HEIGHT = 150

ELEM_Y_POS = 200
FE_WIDTH = 150
FE_HEIGHT = 30

## In this code I don't really properly separate what happens in
## the scene (i.e. valves moving) and in the view (the display of
## those moving valves). Since there are few moving parts I left
## it that way, but it sure made it harder than it had to be.


class View(QGraphicsView,QObject):
    def __init__(self,parent=None):
        super(View,self).__init__(parent)
        #self.resize(600,300)
        self.viewport=QGLWidget()
        self.setViewport(self.viewport)
        # self.setFixedSize(900,600)
        self.setAlignment(Qt.AlignTop|Qt.AlignLeft)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setWindowTitle('CRIS Beamline')
        self.setRenderHint(QPainter.Antialiasing)
        self.setSceneRect(self.x(),self.y(),self.width(),self.height())
        self.centerOn(0,0)

    
class SceneAndView:
    def __init__(self):
        self.scene = ClickGraphicsScene()
        self.view = View()
        self.view.setScene(self.scene)
        self.scene.setBackgroundBrush(QColor(255,255,255))

class ClickGraphicsScene(QGraphicsScene):
    update_sig = pyqtSignal()
    def __init__(self,*args,**kwargs):
        super(ClickGraphicsScene,self).__init__(*args,**kwargs)

    def mousePressEvent(self,event):
        position = event.buttonDownScenePos(event.button())
        item = self.itemAt(position.x(),position.y(),QTransform())
        if isinstance(item,Actuator):
            if item.hasRightClickFunction and event.button() == Qt.RightButton:
                item.RightClicked()
            else:
                item.toggle()
            self.update_sig.emit()

        super(ClickGraphicsScene,self).mousePressEvent(event)

class FixedElement(QGraphicsRectItem):
    def __init__(self,name,x, y):
        super(FixedElement,self).__init__()

        self.setRect(0,0,FE_WIDTH,FE_HEIGHT)
        self.pos = x, y

        self.children = []
        self.widget_children = []
        self.widget_proxies = []

        self.children.append(Label(parent = self, name = name))

        self.position()

        self.value = FixedElementValue(parent = self)
        self.valueproxy = QGraphicsProxyWidget()
        self.valueproxy.setWidget(self.value)
        self.valueproxy.setPos(self.x() + 2,self.y() + 2)

        self.children.append(self.valueproxy)

        pen = QPen()
        pen.setWidth(3)
        self.setPen(pen)


    def position(self):
        self.setPos(self.pos[0],self.pos[1])
        for child in self.children:
            child.position()

class FixedElementValue(QWidget):
    def __init__(self,parent):
        super(FixedElementValue,self).__init__()
        self.parent = parent

        w = self.parent.rect().width()

        self.buff = QLineEdit('0.0',parent = self)
        self.buff.setMaximumWidth(w/3)
        self.buff.move(0,0)

        self.set = QLineEdit('0.0',parent = self)
        self.set.setMaximumWidth(w/3)
        self.set.move(w/3,0)

        self.read = QLineEdit('0.0',parent = self)
        self.read.setReadOnly(True)
        self.read.setMaximumWidth(w/3)
        self.read.move(2*w/3,0)

        self.setMaximumWidth(self.parent.rect().width()-5)


class Actuator(QGraphicsRectItem):
    def __init__(self,name,x,height = ACT_HEIGHT):
        super(Actuator,self).__init__()
        self.brush_out = QBrush(Qt.green)
        self.brush_in = QBrush(Qt.red)
    
        pen = QPen()
        pen.setWidth(3)
        self.setPen(pen)

        self.hasRightClickFunction = False
        self.height = height
        self.setRect(0,0,ACT_WIDTH,self.height)
        
        self.inPos = (x,Y_IN - self.height/2)
        self.outPos = (x,Y_OUT - self.height/2)

        self.children = []
        self.children.append(Label(parent = self, name = name))

        self.moveOut()

    def moveIn(self):
        self.isIn = True
        self.setPos(self.inPos[0],self.inPos[1])
        self.setBrush(self.brush_in)
        for thing in self.children:
            thing.move()

    def moveOut(self):
        self.isIn = False
        self.setPos(self.outPos[0],self.outPos[1])
        self.setBrush(self.brush_out)
        for thing in self.children:
            thing.move()

    def toggle(self):
        if self.isIn:
            self.moveOut()
        else:
            self.moveIn()

    def RightClicked(self):
        pass

class Valve(Actuator):
    def __init__(self,name,x,height=ACT_HEIGHT):
        super(Valve,self).__init__(name,x,height)

class HorizontalValve(Actuator):
    def __init__(self,name,x,height=ACT_HEIGHT):
        super(HorizontalValve,self).__init__(name,x,height)
        self.setRect(0,0,self.height,ACT_WIDTH)

        self.inPos = (x + self.height,Y_OUT - self.height/2)
        self.outPos = (x             ,Y_OUT - self.height/2)

        self.moveOut()

class Cup(Actuator):
    def __init__(self,name,x,height=ACT_WIDTH):
        super(Cup,self).__init__(name,x,height)
        self.hasRightClickFunction = True
        self.children.append(ActuatorLine(parent = self))

    def RightClicked(self):
        print(1)

class Label(QGraphicsTextItem):
    def __init__(self,name,parent):
        super(Label, self).__init__()
        self.setPlainText(name)
        self.parent = parent

        self.move()

    def move(self):
        xpos = self.parent.x() + self.parent.rect().width()/2 - self.boundingRect().width()
        ypos = self.parent.y() - self.boundingRect().height()
        self.setPos(xpos,ypos)

    def position(self):
        self.move()

class ActuatorLine(QGraphicsLineItem):
    def __init__(self,parent,length=80):
        super(ActuatorLine,self).__init__()
        self.parent = parent
        self.length = length
        self.create_line()

        pen = QPen()
        pen.setWidth(3)
        self.setPen(pen)

    def create_line(self):
        self.setLine(self.parent.x() + 0.8*self.parent.rect().width(),
                     self.parent.y() - self.length,
                     self.parent.x() + 0.8*self.parent.rect().width(),
                     self.parent.y())

    def move(self):
        self.create_line()

class BeamLine:
    def __init__(self,parent=None):
        self.sceneView = SceneAndView()
        self.sceneView.view.setSceneRect(0,0,900,600)
        self.sceneView.scene.update_sig.connect(self.update)

        self.cups = {}
        self.valves = {}
        self.hor_valves = {}
        self.tuning_elements = {}

        self.addValve(name = 'Valve1', x = 75)
        self.addValve(name = 'Valve2', x = 405)
        self.addValve(name = 'Valve3', x = 200, hor = True)
        self.addValve(name = 'Valve4', x = 1250)

        self.addCup(name = 'Cup1', x = 475)

        self.addTuningElement(name = 'U1', x = 100,
                              y = ELEM_Y_POS)
        self.addTuningElement(name = 'U2', x = 100,
                              y = ELEM_Y_POS+3*FE_HEIGHT)
        self.addTuningElement(name = 'D1', x = 100 + FE_WIDTH,
                              y = ELEM_Y_POS)
        self.addTuningElement(name = 'D1', x = 100 + FE_WIDTH,
                              y = ELEM_Y_POS+3*FE_HEIGHT)


        self.addTuningElement(name = 'QT1', x = 500,
                              y = ELEM_Y_POS)
        self.addTuningElement(name = 'QT2', x = 500,
                              y = ELEM_Y_POS+3*FE_HEIGHT)
        self.addTuningElement(name = 'QT3', x = 500 + FE_WIDTH,
                              y = ELEM_Y_POS)
        self.addTuningElement(name = 'QT4', x = 500 + FE_WIDTH,
                              y = ELEM_Y_POS+3*FE_HEIGHT)
        self.addTuningElement(name = 'QT5', x = 500 + 2* + FE_WIDTH,
                              y = ELEM_Y_POS)
        self.addTuningElement(name = 'QT6', x = 500 + 2* + FE_WIDTH,
                              y = ELEM_Y_POS+3*FE_HEIGHT)

        self.addTuningElement(name = 'B1', x = 1050,
                              y = ELEM_Y_POS)
        self.addTuningElement(name = 'B2', x = 1050,
                              y = ELEM_Y_POS+3*FE_HEIGHT)

        self.draw_beamline()

        font = QFont()
        font.setPointSize(24)
        self.sees_beam_text = self.sceneView.scene.addText('Currently hit: ', font)
        self.sees_beam_text.setPos(100,400)

        self.update()

    def draw_beamline(self):
        self.sceneView.scene.addLine(0,Y_IN+BEAMLINE_HEIGHT/2, 2500, Y_IN+BEAMLINE_HEIGHT/2)
        self.sceneView.scene.addLine(0,Y_IN-BEAMLINE_HEIGHT/2, 2500, Y_IN-BEAMLINE_HEIGHT/2)

    def addValve(self, name, x, hor = False):
        if hor:
            valve = HorizontalValve(name, x)
            self.hor_valves[name] = valve
        else:
            valve = Valve(name, x)
            self.valves[name] = valve

        self.sceneView.scene.addItem(valve)
        for thing in valve.children:
            self.sceneView.scene.addItem(thing)
      
    def addCup(self, name, x):
        self.cups[name] = Cup(name, x)
        self.sceneView.scene.addItem(self.cups[name])
        for thing in self.cups[name].children:
            self.sceneView.scene.addItem(thing)

    def addTuningElement(self, name, x, y):
        tuningElem = FixedElement(name,x,y)
        self.tuning_elements[name] = tuningElem
        self.sceneView.scene.addItem(tuningElem)

        for thing in self.tuning_elements[name].children:
            self.sceneView.scene.addItem(thing)


    def update(self):
        cups_in = {n:c for n,c in self.cups.items() if c.isIn}
        valves_in = {n:v for n,v in self.valves.items() if v.isIn}

        things_in = {**cups_in,**valves_in}

        if not len(things_in) == 0:
            sees_beam = min(things_in.items(), key=lambda x: x[1].x())[0]
            self.sees_beam_text.setHtml("Currently hit: " + sees_beam)
            if isinstance(things_in[sees_beam],Valve):
                self.sees_beam_text.setDefaultTextColor(Qt.red)
            elif isinstance(things_in[sees_beam],Cup):
                self.sees_beam_text.setDefaultTextColor(Qt.darkYellow)
        else:
            self.sees_beam_text.setDefaultTextColor(Qt.darkGreen)
            self.sees_beam_text.setHtml("Currently hits nothing")

if __name__=='__main__':
    app=QApplication(sys.argv)
    w=BeamLine()
    w.sceneView.view.show()
    sys.exit(app.exec_())
