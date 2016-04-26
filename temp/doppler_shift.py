import numpy as np

mu = 1.66053904 * 10**(-27)
e = 1.60217662 * 10**(-19)
c = 299792458



def doppler_shift(x,V,m):
    m = m * mu
    beta = np.sqrt(1 - (m**2 * c**4)/(e*V + m*c**2)**2)
    factor = (1-beta)/np.sqrt(1-beta**2)
    return x/factor


wn = 40114.01
print(doppler_shift(wn,29945.545,62.9295975)/3)

wn = 71927.28 - 40114.01
print(doppler_shift(wn,29945.545,62.9295975)/2)
