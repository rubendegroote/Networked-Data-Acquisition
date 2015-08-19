from PyQt4 import QtCore, QtGui
import sys
import numpy as np
import pyqtgraph as pg
import pandas as pd
# import pyqtgraph.dockarea as dock

# from picbutton import PicButton

a = pd.read_hdf('copy_of_Server_scan_61.h5', key='ABU')
print(a)
