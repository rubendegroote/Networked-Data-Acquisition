import pandas as pd
import time
import numpy as np
import logging

logging.basicConfig(format='%(asctime)s: %(message)s',
                    level=logging.INFO)

def GetFromQueue(q, name):
    if not q.empty():
        try:
            # try-except to keep this thread refreshing while
            # waiting for data (e.g. to notice stop commands that
            # would have terminated the DAQ process already)
            ret = q.get_nowait()

        except Exception as e:
            logging.critical('An error occured while getting from queue {}.'
                             .format(name))
            logging.critical(e)
            ret = None
    else:
        ret = None

    return ret

def emptyPipe(q):
    toSend = []
    now = time.time()
    while len(toSend) == 0 and time.time() - now < 1:
        time.sleep(0.01)
        while q.poll(0.0005):
            try:
                toSend.append(q.recv())
            except:  # What to do here?
                pass
    return toSend

def mass_concat(array, format):
    data = np.concatenate([d for d in array])
    data = pd.DataFrame(data, columns=format)
    return data

def flatten(array):
    return [l for sub in array for l in sub]

def save(data, name,artist):
    print('save')
    with pd.get_store(name+'_stream.h5') as store:
        store.append(artist, data.convert_objects())
    groups = data.groupby('scan', sort=False)
    for n, group in groups:
        if not n == -1:
            with pd.get_store(name+'_scan_'+ str(int(n))+ '.h5') as store:
                store.append(artist, group.convert_objects())

def save_csv(data,name,artist=''):
    for n, group in groups:
        if n == -1:
            with open(name+'_stream.csv', 'a') as f:
                group.to_csv(f,na_rep='nan')
        else:
            with open(name+'_scan' + str(int(n))+'.csv', 'a') as f:
                group.to_csv(f,na_rep='nan')
