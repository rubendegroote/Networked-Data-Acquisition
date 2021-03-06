import numpy as np
import sys, os
import time
from backend.helpers import extract_scan,calcHist
import matplotlib.pyplot as plt, mpld3
import threading as th
from http.server import HTTPServer,BaseHTTPRequestHandler,SimpleHTTPRequestHandler
import socketserver
from config.absolute_paths import CONFIG_PATH, SCAN_PATH
import shutil
from backend.dispatcher import Dispatcher
from backend.helpers import try_call
from os.path import join, dirname, normpath, isdir
from os import listdir
import configparser

##### CHANGE THIS IF YOU WANT TO SEE SOMETHING ELSE
binsize = 5
x_dev_browser = 'wavemeter_pdl'
x_col_browser = 'wavenumber_1'
y_dev_browser = 'cris'
y_col_browser = 'Counts'

CHUNK_SIZE = 5*10**4

def copy_data(src_path, dest_path):
    if not os.path.isdir(dest_path):
        os.makedirs(dest_path)
        # only copy files if they weren't copied before, i.e. if this
        # folder did not exist before
        for f in os.listdir(src_path):
            src_file = os.path.join(src_path, f)
            dst_file = os.path.join(dest_path, f)
            shutil.copyfile(src_file, dst_file) 

def plot_scan(file_path):
    try:
        df = extract_scan([file_path],[x_col_browser,y_col_browser], [x_dev_browser,y_dev_browser])
    except FileNotFoundError:
        print(file_path, ' was not extracted during static browser plotting, probably no data for requested columns')
        return

    df = df.rename(columns={'wavenumber_1': 'x', 'Counts': 'y'})
    df = df[df['x'] > 10000]
    off = df['x'].mean()
    df['x'] -= off
    df['x'] *= 29979.2458

    start = df['x'].min()
    stop = df['x'].max()
    bins = np.linspace(start,stop,(stop-start)/binsize)
    if not len(bins) == 0:
        df = calcHist(df,bins,errormode = 'sqrt',data_mode = 'mean')

        with open(os.path.join(file_path,'plot.csv'), 'w') as dfile:
            df.to_csv(dfile)

        fig = plt.figure()
        plt.errorbar(x=df['x'].values,y=df['y'].values,
            xerr=df['xerr'].values,yerr=[df['yerr_t'].values,df['yerr_b'].values], 
            fmt='rd')
        plt.title('Offset {} cm-1'.format(off))
        plt.xlabel('Frequency (MHz) w.r.t. mean')
        plt.ylabel('Counts per trigger')
        plt.xlim([start,stop])
        plt.ylim([0.9*(df['y']-df['yerr_b']).min(),1.1*(df['y'] + df['yerr_t']).max()])
       
        with open(os.path.join(file_path,'plot.html'), 'w') as sf:
            sf.write(mpld3.fig_to_html(fig))

        fig.clf()

class OverviewHandler(BaseHTTPRequestHandler):
    def __init__(self,*args,**kwargs):
        super(OverviewHandler,self).__init__(*args,**kwargs)
        self.scan_parser = configparser.ConfigParser()
        self.scan_parser.read(SCAN_PATH)
        
    def do_GET(self):
        try:
            last_scan = int(self.scan_parser['last_scan']['last_scan'])
        except:
            self.wfile.write(bytes('No scans yet','utf-8'))
            return
        mass = int(self.scan_parser['last_scan']['mass'])
        scanner_name = self.scan_parser['scanner']['scanner']
        scanning = self.scan_parser['scanning']['scanning']

        scan_mass = dict(self.scan_parser['scan_mass'])
        for key,val in scan_mass.items():
            scan_mass[key] = eval(val)
        scan_ranges = dict(self.scan_parser['scan_ranges'])
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

class FileServer(Dispatcher):
    def __init__(self, name='file_server'):
        super(FileServer, self).__init__(name)
        
        self.save_path = self.config_parser['paths']['data_path']
        self.serve_path = self.config_parser['paths']['filserver_path']

        if not os.path.isdir(self.serve_path):
            os.makedirs(self.serve_path)

        self.row = 0

        self.paths_dict = {}
        self.scans = []
        self.masses = []
        self.current_scan = None

        self.survey_thread = th.Timer(0, self.survey_directory)
        self.survey_thread.start()

        self.run_servers()

    def run_servers(self):
        self.server_thread = th.Thread(target = self.run)
        self.server_thread.daemon = True
        self.server_thread.start()

        self.server_thread_2 = th.Thread(target = self.run_plots)
        self.server_thread_2.daemon = True
        self.server_thread_2.start()

    def stop(self):
        self.server.shutdown()
        self.httpd.shutdown()

        super(FileServer,self).stop()

    def run(self):
        self.server =  HTTPServer(('0.0.0.0', 10000), OverviewHandler)
        self.server.serve_forever()

    def run_plots(self):
        os.chdir(self.serve_path)

        self.httpd = socketserver.TCPServer(("0.0.0.0", 20000), SimpleHTTPRequestHandler)
        self.httpd.serve_forever()

    def survey_directory(self):
        ## not elegant, but robust...
        # in diiiiire need of refactoring
        for dirname in listdir(self.save_path):
            if not isdir(self.save_path+dirname):
                continue
            sub_path = join(self.save_path, dirname)
            if not normpath(sub_path) == normpath(self.serve_path):
                if dirname == 'stream':
                    continue
                mass = int(float(dirname))
                for subdirname in listdir(sub_path):
                    full_path = join(sub_path,subdirname) 
                    if not isdir(full_path):
                        continue

                    scan = int(subdirname.strip('scan_'))
                    if not scan in self.scans:
                        with open(join(self.save_path,'scanning.txt'),'r') as f1:
                            line = f1.readline()
                            scanning = int(line) == 1
                            if scanning:
                                self.current_scan = int(float(f1.readline()))
                            else:
                                self.current_scan = None

                        if scanning and scan == self.current_scan:
                            pass
                        else:
                            print(mass,scan)
                            time.sleep(0.1) ## one can never be too sure that the saving is done ;)
                            
                            path_to_serve = self.change_path_to_serve(full_path)
                            copy_data(full_path, path_to_serve)
                            plot_scan(path_to_serve)
                            
                            self.paths_dict[scan] = full_path
                            self.masses.append(mass)
                            self.scans.append(scan)
        if self.looping:
            self.survey_thread = th.Timer(5, self.survey_directory)
            self.survey_thread.start()
    
    def change_path_to_serve(self,path):
        return self.serve_path + path.strip(self.save_path)    

    @try_call
    def get_status(self,params):
        return {'masses':self.masses,
                'available_scans':self.scans}

    @try_call
    def scan_format(self,params):
        self.row = 0
        scans = params['scans']
        frmt = []
        for scan in scans:
            file_path = self.paths_dict[scan]
            for f in os.listdir(file_path):
                if 'metadata' in f and 'ds' in f:
                    dev = f
                    dev = dev.replace('metadata_','')
                    dev = dev.replace('_ds.txt','')
                    with open(os.path.join(file_path,f), 'r') as mf:
                        mass_info = mf.readline()
                        scan_info = mf.readline()
                        frmt = frmt + [dev + ': ' + n for n in eval(mf.readline())]
        frmt = list(set(frmt))
        return {'format': frmt}

    @try_call
    def request_data(self,params):
        scan_numbers = params['scan_numbers']

        x_dev,x_col = params['x'].split(': ')
        y_dev,y_col = params['y'].split(': ')

        file_paths = [self.paths_dict[scan] for scan in scan_numbers]

        if self.row == 0:
            self.data = extract_scan(file_paths,[x_col,y_col], [x_dev,y_dev])

        stop = self.row+CHUNK_SIZE
        progress = int(100*(stop/len(self.data)))
        data = [self.data['timestamp'][self.row:stop],
                self.data[x_col][self.row:stop],
                self.data[y_col][self.row:stop]]

        chunk = [list(d.values) for d in data]

        if stop >= len(self.data):
            self.row = 0
            return {'data': chunk,'done':True, 'progress':100}
        else:
            self.row = stop
            return {'data': chunk,'done':False, 'progress':progress}

def makeFileServer():
    return FileServer()

if __name__ == '__main__':
    main()
