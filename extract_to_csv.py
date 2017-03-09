# import satlas as sat
import numpy as np
import matplotlib.pyplot as plt
import h5py
import pandas as pd
 
def beta(mass, V):
    """Calculates the beta-factor for a mass in amu
    and applied voltage in Volt.
 
    Parameters
    ----------
    mass : float
        Mass in amu.
    V : float
        voltage in volt.
 
    Returns
    -------
    float
        Relativistic beta-factor.
    """
    c = 299792458.0
    q = 1.60217657 * (10 ** (-19))
    AMU2KG = 1.66053892 * 10 ** (-27)
    mass = mass * AMU2KG
    top = mass ** 2 * c ** 4
    bottom = (mass * c ** 2 + q * V) ** 2
    beta = np.sqrt(1 - top / bottom)
    return beta
 
def dopplerfactor(mass, V):
    """Calculates the Doppler shift of the laser frequency for a
    given mass in amu and voltage in V.
 
    Parameters
    ----------
    mass : float
        Mass in amu.
    V : float
        Voltage in volt.
 
    Returns
    -------
    float
        Doppler factor.
    """
    betaFactor = beta(mass, V)
    dopplerFactor = np.sqrt((1.0 - betaFactor) / (1.0 + betaFactor))
    return dopplerFactor
 
file = 'server_data.h5'
data = pd.DataFrame()
mass_selection = [203]
masses = {
        63: 0,
        65: 0,
        69: 0,
        71: 0,
        73: 0,
        75: 0,
        76: 75.945275,
        77: 0}
names = ['CRIS', 'wavemeter', 'iscool']
binsize = 0.0005 / 3
chunksize = 10**4
scans = [40, 41, 42, 43, 44, 45]
import tqdm
with h5py.File(file, 'r') as f:
    d = pd.DataFrame()
    for scan in tqdm.tqdm(f[names[0]]):
        if scan != '-1' and scan in scans:
            for name in names:
                if scan in f[name]:
                    if b'mass' in f[name][scan].attrs['format']:
                        format = list(f[name][scan].attrs['format'])
                        index = format.index(b'mass')
                        mass = f[name][scan][-1, index]
                        if mass in mass_selection:
                            selection = [b'Counts', b'timestamp', b'wavenumber_1', b'scan_number', b'voltage']
                            indices = sorted([format.index(sel) for sel in selection if sel in format])
                            format = np.array([form.decode('utf-8') for form in format])
                            temp = f[name][scan]
                            ranges = np.arange(0, (np.ceil(temp.shape[0]/chunksize)+1)*chunksize, chunksize)
                            left = ranges[:-1]
                            right = ranges[1:]-1
                            for l, r in zip(left, right):
                                l, r = int(l), int(r)
                                d = d.append(pd.DataFrame(temp[l:r, indices], columns=format[indices]), ignore_index=True)
    if not d.empty:
        d = d[d['wavenumber_1'] > 13383*3]
        d = d.set_index('timestamp')
        d.sort_index(inplace=True)
        # d = d[np.bitwise_or(d['Counts']<3, np.isnan(d['Counts']))]

        d['wavenumber_1'].fillna(method='ffill', inplace=True)
        d['wavenumber_1'].fillna(method='bfill', inplace=True)
        d['voltage'].fillna(method='ffill', inplace=True)
        d['voltage'].fillna(method='bfill', inplace=True)
        d = d[~np.isnan(d['Counts'])]

        c = 299792458

        d['corrected_wavenumber'] = pd.Series(dopplerfactor(masses[mass], d['voltage'].values)*d['wavenumber_1'].values*3, index=d.index)

        left = d['corrected_wavenumber'].min()
        right = d['corrected_wavenumber'].max()
        bins = np.arange(left-binsize/2, right + binsize/2 + binsize, binsize)
        bin_means = bins[0] + np.diff(bins).cumsum()
        bin_means = (bin_means-13383*3) * c * 100 * 10**-6
        bin_selection = np.digitize(d['corrected_wavenumber'].values, bins)

        bin_std = np.zeros(len(bins)-1)
        entries = max([(bin_selection == number).sum() for number in np.unique(bin_selection)])
        counts = np.zeros((len(bins)-1, entries))
        counts = np.zeros(len(bin_means))
        entries = np.zeros(len(counts))
        for i, number in enumerate(np.unique(bin_selection)):
            data = d['Counts'][bin_selection == number]
            counts[number - 1] = data.sum()
            entries[number - 1] = len(d['Counts'][bin_selection == number])
        d = pd.DataFrame({'counts': counts, 'entries': entries, 'wavelength': bin_means})
        d.to_csv(str(mass) + 'Cu.csv')
