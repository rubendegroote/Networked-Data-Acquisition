import zlib
import numpy as np
import sys
import time

data  = [np.zeros(5*10**6),np.zeros(5*10**6),np.zeros(5*10**6)]


compressed = [zlib.compress(d) for d in data]

print([zlib.decompress(d) for d in data])