import pandas as pd
import os


def save_csv(data, name, mQ):
    mQ.put('Converting {} ({} rows)'.format(name, len(data)))
    f = name.strip(".h5") + '.csv'
    with open(f, "w") as myfile:
        data.to_csv(myfile, index=True, na_rep='Nan', sep=';')
    mQ.put(
        'Converted all-data-file {} ({} bytes)'.format(f, os.path.getsize(f)))
    return f


def save_groups_csv(data, name, mQ):
    groups = data.groupby('scan', sort=False)
    number = len([1 for (n, g) in groups if n > 0])
    fs = []
    mQ.put("{} scans found.".format(number))
    for n, group in groups:
        if not n == -1:
            mQ.put('Extracting and saving scan {} on server...'
                   .format(str(int(n))))
            f = name.strip('.h5') + '_scan_' + str(int(n)) + '.csv'
            fs.append(f)
            with open(f, "w") as myfile:
                group.to_csv(myfile, index=True, na_rep='Nan', sep=';')
            mQ.put('Saved scan file {} ({} bytes) on server.'
                   .format(f, os.path.getsize(f)))

    return fs


def read(name):
    if ".h5" in name:
        f = pd.get_store(name)
        data = pd.concat([f[k] for k in f.keys()])
        return data
    elif ".csv" in name:
        return pd.read_csv(name)
    else:
        return None


def convert(name, mQ, full=True, groups=True):
    df = read(name)
    if full:
        n = [save_csv(df, name, mQ)]
    else:
        n = []

    if groups:
        scans = save_groups_csv(df, name, mQ)
    else:
        scans = []

    return n + scans
