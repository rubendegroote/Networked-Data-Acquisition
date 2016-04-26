import numpy as np
import matplotlib.pyplot as plt
import os

print(os.getcwd())


data = np.genfromtxt('mainz_scan.txt',delimiter = '\t',dtype=float)

print(data)

x = np.array([float(d) for d in data.T[0]])
x = 1/x * 10**7 - 40114.01/3
y = np.array([float(d) for d in data.T[1]])

plt.plot(x,y)
plt.show()