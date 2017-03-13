import h5py 
import pandas as pd
import matplotlib.pyplot as plt
import time

def extract_scan(path,scan_number,columns,filename=None):
    if not type(scan_number)==str:
        scan_number = str(int(scan_number))
   
    devices = [c.split(': ')[0] for c in columns]
    columns = [c.split(': ')[-1] for c in columns]

    dfs = []
    with h5py.File(path) as store:
        for dev,col in zip(devices,columns):
            try:
                start = time.time()
                for scanno in store[dev].keys():
                    dfs.append(pd.DataFrame())
                    dfs[-1][col] = store[dev][scanno][col].value
                    dfs[-1]['time'] = store[dev][scanno]['timestamp'].value
                    print('extracted {} in {}s'.format(col,round(time.time() - start,1)))
            except:
                print('failed getting {} {}'.format(dev,col))

    dataframe = pd.concat(dfs)
    dataframe['time'] = dataframe['time'] - dataframe['time'].values[0]
    dataframe = dataframe.sort_values(by='time')
    for col in columns:
        if not col == 'Counts':
            dataframe[col] = dataframe[col].fillna(method='ffill')
    dataframe = dataframe.dropna()
    dataframe = dataframe.reset_index()

    if filename is not None:
        dataframe.to_csv(filename)

    return dataframe

def print_summary(self,path):
    with h5py.File(path) as store:
        self.devices = list(store.keys())
        self.scans = {}
        self.scans_all = {}
        self.columns = {}
        self.columns_all = {}
        for dev in self.devices:
            scans = list(store[dev].keys())
            self.scans[dev] = sorted(list(set([s.split('_')[0] for s in scans])))
            self.scans_all[dev] = {}
            self.columns_all[dev] = {}
            for s in self.scans[dev]:
                self.scans_all[dev][s] = [name for name in scans if s in name]
                self.columns_all[dev][s] = list(store[dev][self.scans_all[dev][s][0]].keys())
            all_cols = []
            for cols in self.columns_all[dev].values():
                all_cols.extend(cols)
            self.columns[dev] = list(set(all_cols))

    ret = 'File summary:\n'
    ret += 'path: {}\n'.format(self.path)
    ret += 'devices: {}\n'.format(self.devices)
    ret += 'scans:\n'
    for dev in self.devices:
        ret +='\t{}: {} \n'.format(dev,self.scans[dev])
    ret += 'columns:\n'
    for dev in self.devices:
        ret +='\t{}: {} \n'.format(dev,self.columns[dev])
    
    print(ret)


def main():
    filename = 'C:\\DAQ tests\\Data\\test\\server_data.h5'
    data = extract_scan(filename,scan_number = -1,
                               columns=['test2: wavenumber_1','test2: Counts','test3: mass'],
                               filename = 'test.csv') 
    plt.plot(data['wavenumber_1'],data['Counts'],'rd')
    plt.plot(data['wavenumber_1'],data['mass'],'k-')
    plt.show()

if __name__ == '__main__':
    main()
