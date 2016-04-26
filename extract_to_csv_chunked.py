# import satlas as sat
import numpy as np
import matplotlib.pyplot as plt
import h5py
import pandas as pd
c = 299792458

def get_chunks_from_timebin(group, timebin):
    chunksize = timebin / (group[1, format.index(b'timestamp')] - group[0, format.index(b'timestamp')])
    chunks = np.arange(0, (np.ceil(group.shape[0]/chunksize)+1)*chunksize, chunksize)
    left_chunks = chunks[:-1]
    right_chunks = chunks[1:]
    return left_chunks, right_chunks

def determine_max_min_freq(wavemeter, iscool, mass, timebin=600):
    left_wavemeter, right_wavemeter = get_chunks_from_timebin(wavemeter, timebin)
    left_iscool, right_iscool = get_chunks_from_timebin(iscool, timebin)

    selection_wavemeter = [b'wavenumber_1', b'timestamp']
    selection_iscool = [b'timestamp', b'voltage']

    format_wavemeter = list(wavemeter.attrs['format'])
    indices_wavemeter = sorted([format.index(sel) for sel in selection_wavemeter if sel in format_wavemeter])

    format_iscool = list(iscool.attrs['format'])
    indices_iscool = sorted([format.index(sel) for sel in selection_iscool if sel in format_iscool])

    min_freq = np.inf
    max_freq = -np.inf

    for l_w, r_w, l_i, r_i in zip(left_wavemeter, right_wavemeter, left_iscool, right_iscool):
        d = pd.DataFrame()
        l_w, r_w = int(l_w), int(r_w)
        l_i, r_i = int(l_i), int(r_i)

        wavemeter_data = wavemeter[l_w:r_w, indices_wavemeter]
        wavemeter = wavemeter > 13380
        iscool_data = iscool[l_i:r_i, indices_wavemeter]
        
        d = d.append(pd.DataFrame(wavemeter_data, columns=format_wavemeter[indices_wavemeter]), ignore_index=True)
        d = d.append(pd.DataFrame(iscool_data, columns=format_iscool[indices_iscool]), ignore_index=True)

        d = d.set_index('timestamp')
        d.sort_index(inplace=True)

        d['wavenumber_1'].fillna(method='ffill', inplace=True)
        d['wavenumber_1'].fillna(method='bfill', inplace=True)
        d['voltage'].fillna(method='ffill', inplace=True)
        d['voltage'].fillna(method='bfill', inplace=True)
        
        corrected_frequency = dopplerfactor(mass, d['voltage'].values)*d['wavenumber_1'].values * 3 * c * 100 * 10**-6
        
        min_freq = min(min_freq, min(frequency))
        max_freq = max(max_freq, max(frequency))
    return min_freq, max_freq

def calculate_chunked_histogram(bins, wavemeter, iscool, cris, mass, timebin=600):
    left_wavemeter, right_wavemeter = get_chunks_from_timebin(wavemeter, timebin)
    left_iscool, right_iscool = get_chunks_from_timebin(iscool, timebin)
    left_cris, right_cris = get_chunks_from_timebin(cris, timebin)

    selection_wavemeter = [b'wavenumber_1', b'timestamp']
    selection_iscool = [b'timestamp', b'voltage']
    selection_cris = [b'timestamp', b'Counts']

    format_wavemeter = list(wavemeter.attrs['format'])
    indices_wavemeter = sorted([format.index(sel) for sel in selection_wavemeter if sel in format_wavemeter])

    format_iscool = list(iscool.attrs['format'])
    indices_iscool = sorted([format.index(sel) for sel in selection_iscool if sel in format_iscool])

    format_cris = list(cris.attrs['format'])
    indices_cris = sorted([format.index(sel) for sel in selection_cris if sel in format_cris])

    bin_std = np.zeros(len(bins)-1)
    bin_mean = np.zeros(len(bin_std))
    counts = np.zeros(len(bin_std))
    entries = np.zeros(len(bin_std))

    for lw, rw, li, ri, lc, rc in zip(left_wavemeter, right_wavemeter, left_iscool, right_iscool, left_cris, right_cris):
        lw, rw, li, ri, lc, rc = int(lw), int(rw), int(li), int(ri), int(lc), int(rc)
        
        d = pd.DataFrame()
        
        wavemeter_data = wavemeter[lw:rw, indices_wavemeter]
        wavemeter_data = wavemeter_data > 13380
        iscool_data = iscool[li:ri, indices_iscool]
        cris_data = cris[lc:rc, indices_cris]

        d = d.append(pd.DataFrame(wavemeter_data, columns=format_wavemeter[indices_wavemeter]), ignore_index=True)
        d = d.append(pd.DataFrame(iscool_data, columns=format_iscool[indices_iscool]), ignore_index=True)
        d = d.append(pd.DataFrame(cris_data, columns=format_cris[indices_cris]), ignore_index=True)

        d = d.set_index('timestamp')
        d.sort_index(inplace=True)

        d['wavenumber_1'].fillna(method='ffill', inplace=True)
        d['wavenumber_1'].fillna(method='bfill', inplace=True)
        d['voltage'].fillna(method='ffill', inplace=True)
        d['voltage'].fillna(method='bfill', inplace=True)

        corrected_frequency = dopplerfactor(mass, d['voltage'].values)*d['wavenumber_1'].values * 3 * c * 100 * 10**-6

        bin_selection = np.digitize(corrected_frequency, bins)

        for number in np.unique(bin_selection):
            counts = d['Counts'][bin_selection == number]
            freq = corrected_frequency[bin_selection == number]
            events = len(counts)

            mean_freq = np.mean(corrected_frequency[bin_selection == number])
            #std_freq = np.sqrt(np.mean((freq - mean_freq)**2))

            bin_mean[number - 1] = (entries[number - 1] * bin_mean[number - 1] + events * mean_freq) / (entries[number - 1] + events)

            counts[number - 1] += data.sum()
            entries[number - 1] += events

    return bin_mean, bin_std, counts, entries

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
 
filename = 'server_data.h5'
masses = {
        63: 0,
        65: 0,
        69: 0,
        71: 0,
        73: 0,
        75: 0,
        76: 75.945275,
        77: 76.94785,
        78: 78}
names = ['CRIS', 'wavemeter', 'iscool']
binsize = 3

scans = [105,110,139,140,141,90,91,89,88,79,78,77]
# import tqdm
with h5py.File(filename, 'r') as f:
    # Determine frequencies for bin calculation
    min_freq, max_freq = np.inf, -np.inf
    for scan in f[names[0]]:
        if scan != '-1' and int(scan) in scans:
            format = list(f['iscool'][scan].attrs['format'])
            index = format.index(b'mass')
            mass = masses[int(f['iscool'][scan][-1, index])]
            index = format.index(b'voltage')
            print(index)
            iscool = masses[int(f['iscool'][scan][-1, index])]
            left, right = determine_max_min_freq(f['wavemeter'][scan], iscool, mass)
            min_freq = min(min_freq, left)
            max_freq = max(max_freq, right)

    bins = np.arange(min_freq - binsize/2, max_freq + binsize/2 + binsize, binsize)

    # Pre-allocate the arrays for the bin mean, the number of counts and the number of entries
    # Note that the standard deviation of the bin mean is not yet calculated!
    bin_means = np.zeros(len(bins)-1)
    bin_std = np.zeros(len(bins)-1)
    counts = np.zeros(len(bins)-1)
    entries = np.zeros(len(bins)-1)
    for scan in f[names[0]]:
        if scan != '-1' and int(scan) in scans:
            bin_means_t, bin_std_t, counts_t, entries_t = calculate_chunked_histogram(bins, f['wavemeter'][scan], f['iscool'][scan], f['CRIS'][scan], mass)
            bin_means = (entries * bin_means + bin_means_t * entries_t) / (entries + entries_t)
            counts += counts_t
            entries += entries_t

    d = pd.DataFrame({'counts': counts, 'entries': entries, 'wavelength': bin_means})
    d.to_csv(str(mass) + 'Cu.csv')
