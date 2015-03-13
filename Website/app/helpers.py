import pickle
import pandas as pd
import time
import numpy as np

def GetFromQueue(q,name):
    if not q.empty():
        try: # try-except to keep this thread refreshing while 
             # waiting for data (e.g. to notice stop commands that
             # would have terminated the DAQ process already)
            ret = q.get_nowait()

        except Exception as e:
            print('An error occured while getting from queue ' + name)
            print(e)
            ret = None
    else:
        ret = None
        
    return ret

def emptyPipe(q):
    toSend = []
    now = time.time()
    while len(toSend)==0 and time.time()-now < 5:
        try:
            toSend.append(q.recv())
        except:
            print(1)
        time.sleep(0.01)

    return toSend

def mass_concat(array,format):
    data = np.concatenate([d for d in array])
    data = pd.DataFrame(data,columns=format)
    return data

def flatten(array):
    return [l for sub in array for l in sub]

def save(data,name):
    # with pd.get_store(name+'.h5') as store:
        
    groups = data.groupby('scan', sort=False)
    for n, group in groups:
        if n == -1:
            with pd.get_store(name+'.h5') as store:
                store.append('stream',group.convert_objects())
        else:
            # with pd.get_store(name+'.h5') as store:
            #     print(store)
                # if not n in store:
                    # df = pd.DataFrame([group['time'][0],n],
                    #             columns = [['time'],['scan']])
                    # store.append('keys',df.convert_objects())
            with pd.get_store(name+'.h5') as store:
                store.append('scan'+str(int(n)),group.convert_objects())
