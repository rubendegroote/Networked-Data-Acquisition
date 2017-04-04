import numpy as np
import h5py as hp
import configparser
import sys, os
import time
from backend.helpers import extract_scan,calcHist
import matplotlib.pyplot as plt, mpld3
from mpld3 import plugins
import threading as th
import configparser
from http.server import HTTPServer,BaseHTTPRequestHandler,SimpleHTTPRequestHandler
import socketserver


##### CHANGE THIS IF YOU WANT TO SEE SOMETHING ELSE
binsize = 1500
x = 'wavemeter_pdl: wavenumber_1'
y = 'cris: Counts'



CONFIG_PATH = "\\\\cern.ch\\dfs\\Users\\c\\CRIS\\Documents\\Networked-Data-Acquisition\\Config files\\config.ini"
config_parser = configparser.ConfigParser()
config_parser.read(CONFIG_PATH)
save_path = config_parser['paths']['data_path']

SCAN_PATH = "\\\\cern.ch\\dfs\\Users\\c\\CRIS\\Documents\\Networked-Data-Acquisition\\Config files\\scan_init.ini"
PLOTS_PATH = 'C:\\DAQ tests\\browser\\'


def plot_scan(s,m):

    directory = PLOTS_PATH + '\\{}\\'.format(m)

    if not os.path.exists(directory):
        os.makedirs(directory)
    if not os.path.exists(directory+'\\data\\'):
        os.makedirs(directory+'\\data\\')

    try:
        df = extract_scan(save_path+'server_data.h5',[s],
            [y,x])
    except:
        return

    df = df.rename(columns={'wavenumber_1': 'x', 'Counts': 'y'})
    off = df['x'].mean()
    df['x'] -= off
    df['x'] *= 29979.2458

    start = df['x'].min()
    stop = df['x'].max()
    bins = np.linspace(start,stop,(stop-start)/binsize)
    if not len(bins) == 0:
        df = calcHist(df,bins,errormode = 'sqrt',data_mode = 'mean')

        with open(directory + '\\data\\{}.csv'.format(s), 'w') as dfile:
            df.to_csv(dfile)

        fig = plt.figure()
        plt.errorbar(x=df['x'].values,y=df['y'].values,
            xerr=df['xerr'].values,yerr=[df['yerr_t'].values,df['yerr_b'].values], 
            fmt='rd')
        plt.title('Scan {} - offset {}cm-1'.format(s,off))
        plt.xlabel('Frequency (MHz) w.r.t. mean')
        plt.ylabel('Counts per trigger')
        plt.xlim([start,stop])
        plt.ylim([0.9*(df['y']-df['yerr_b']).min(),1.1*(df['y'] + df['yerr_t']).max()])
       
        with open(directory + '{}.html'.format(s), 'w') as sf:
            sf.write(mpld3.fig_to_html(fig))

        fig.clf()

class OverviewHandler(BaseHTTPRequestHandler):
    def __init__(self,*args,**kwargs):
        super(OverviewHandler,self).__init__(*args,**kwargs)

    def do_GET(self):
        
        scan_parser = configparser.ConfigParser()
        scan_parser.read(SCAN_PATH)

        last_scan = int(scan_parser['last_scan']['last_scan'])
        mass = int(scan_parser['last_scan']['mass'])
        scanner_name = scan_parser['scanner']['scanner']
        scanning = scan_parser['scanning']['scanning']

        scan_mass = dict(scan_parser['scan_mass'])
        for key,val in scan_mass.items():
            scan_mass[key] = eval(val)
        scan_ranges = dict(scan_parser['scan_ranges'])
        for key,val in scan_ranges.items():
            scan_ranges[key] = eval(val)

        to_write = ''
        to_write += 'Last scan:\t{}\t on mass {}\n\n'.format(last_scan,mass)
        to_write += 'Scans so far:\n'
        for key, val in scan_mass.items():
            to_write += '\tMass:\t {}\t  Scans {}\n'.format(key, str(sorted([int(v) for v in val])))
        to_write += '\nScan ranges used:\n'
        for key, val in scan_ranges.items():
            descr = ''
            for v in val:
                if not descr == '':
                    descr += ', and '
                descr += 'from {} to {} in {} steps of {} {}, {} times'.format(v[0],v[1],v[2],v[3],v[4],v[5])
            to_write += '\t Scan:\t {}\t'.format(key) + descr + '\n'
        if int(scanning)==1:
            to_write += '\nCurrently scanning the {}\n'.format(scanner_name)
        else:
            to_write += '\nNot currently scanning\n'

        self.wfile.write(bytes(to_write,'utf-8'))

def run():
    with HTTPServer(('0.0.0.0', 10000), OverviewHandler) as server:
        server.serve_forever()

def run_plots():
    os.chdir(PLOTS_PATH)
    with socketserver.TCPServer(("0.0.0.0", 20000), SimpleHTTPRequestHandler) as httpd:
        httpd.serve_forever()

def main():
    server_thread = th.Thread(target = run)
    server_thread.setDaemon(True)
    server_thread.start()

    server_thread_2 = th.Thread(target = run_plots)
    server_thread_2.setDaemon(True)
    server_thread_2.start()

    scans = []
    while True:
        # try:
        with open(save_path+'server_scanning.txt','r') as f1:
            line = f1.readline()
            scanning = int(line) == 1

        with open(save_path+'server_scans.txt','r') as f:
            lines = f.readlines()
            for i,line in enumerate(reversed(lines)):
                if i == 0 and scanning:
                    pass
                else:
                    s = line.strip('\n').split(';')[0]
                    m = line.strip('\n').split(';')[1]
                    if not int(s) == -1 and not s in scans:
                        scans.append(s)
                        plot_scan(s,m)
        # except Exception as e:
        #     print(e)

        time.sleep(1)


if __name__ == '__main__':
    main()
