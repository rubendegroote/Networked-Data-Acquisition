# import numpy as np
# import pandas as pd
# import time
# import multiprocessing as mp
# from backend.helpers import emptyPipe

import numba as nb
import bisect
import time
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import chi2

def poiss_high(data, alpha=0.32):
    high = chi2.ppf(1 - alpha / 2, 2 * data + 2) / 2
    return high

def poiss_low(data, alpha=0.32):
    low = chi2.ppf(alpha / 2, 2 * data) / 2
    low = np.nan_to_num(low)
    return low


@nb.jit
def f_needs_sorted_args(x, y, bins):
    binned = [0.0]*lbins
    prev_index = 0
    for i in range(len(x)):
        index = prev_index
        for ind in range(index,lbins):
            if x[i] < bins[ind]:
                prev_index = index
                break
            else:
                index += 1
        binned[index] += y[i]
    return np.array(binned)



def pandas_f_2(x,y,bins):
    frame = pd.DataFrame({'x':x,'y':y})
    frame['sel'] = np.digitize(x,bins)
    result = frame.groupby('sel').agg(np.sum)

    return result


# @nb.jit
def f(x, y, bins):
    binned = [0.0]*lbins
    noe = [0.0]*lbins
    prev_index = 0
    for i in range(len(x)):
        for j in range(lbins):
            if (x[i] > bins[j] and (j==lbins-1 or x[i] <= bins[j+1])):
                binned[j] += y[i]
                # noe[j] += 1
    return np.array(binned)

import pandas as pd
def pandas_f(x,y,bins):
    frame = pd.DataFrame({'x':x,'y':y,'xerr':x,'ynoe':y,'ye1':y,'ye2':y})
    frame['sel'] = np.digitize(x,bins)
    groups = frame.groupby('sel')
    result = groups.agg({'x':np.mean,'xerr':np.std,
                       'y':np.sum,
                       'ye1':lambda x: poiss_high(np.sum(x)),
                       'ye2':lambda x: poiss_low(np.sum(x))})
    return groups,result

# def pandas_rolling_f(x,y,stepsize):

def get_bins(x,step):
    return np.linspace(b0,b1,(b1-b0) / step)

N = 10**4
step = 1

x = np.random.rand(N)*100
b0, b1 = x.min()//step,(x.max()+step)//step*step
# x = np.linspace(0,100,N)
y = 2*np.exp(-(x-50)**2/100)
y = y.astype(int)
bins = get_bins(x,step=step)

group, binned = pandas_f(x,y,bins-0.5)

minvalue = x.min()//step
for i in range(100):
    x_new = np.random.rand(2000)*100
    y_new = 2*np.exp(-(x_new-50)**2/100)
    y_new = y_new.astype(int)

    new_frame = pd.DataFrame({'x':x_new,'y':y_new})
    # Define new bins
    # determine what bin every row is in
    bins = get_bins(x_new,step)
    new_frame['sel'] = np.digitize(x_new,bins)

    ## align bin w.r.t. old bins:
    # if the new minimum is bigger than the old one: shift the new 
    # bin numbers to the right, otherwise shift the old ones to the left
    newmin = x.min() // step
    if newmin >= minvalue:
        new_frame['sel'] += newmin - minvalue
    else:
        binned['sel'] += minvalue - newmin
    minvalue = min(newmin,minvalue)

    print(new_frame['sel'])

    input()

    group, binned = pandas_f(x,y,bins-0.5)








# f_needs_sorted_args(x,y,bins)
# tic = time.time()
# sorter = x.argsort()
# x_sorted,y_sorted = x[sorter],y[sorter]
# binned = f_needs_sorted_args(x_sorted,y_sorted,bins)
# print('jit', time.time() - tic)
# plt.plot(bins,binned, 'o', label = '1')

# tic = time.time()
# binned = pandas_f(x,y,bins-0.5)
# print('pandas', time.time() - tic)
# print(binned.head())

# plt.errorbar(bins,binned[0],yerr=binned[1], fmt='d', label = 'pandas')

# tic = time.time()
# binned = pandas_f_2(x,y,bins-0.5)
# print('pandas', time.time() - tic)
# plt.errorbar(bins,binned[0],yerr=binned[1], fmt='d', label = 'pandas')

# f(x,y,bins)
# tic = time.time()
# binned = f(x,y,bins-0.5)
# print('jit', time.time() - tic)
# plt.plot(bins,binned, 'o', label = 'jit')

# plt.legend()
# plt.show()



# class Binner():
#     def __init__(self,data_daque):
#         self.data_daque = data_daque

#         self.binspars = []
#         self.bin_processes = {}
#         self.pipe_in = {}
#         self.pipe_out = {}

#         self.get_chunk_thread = th.Timer(0, self.get_chunks)
#         self.get_chunk_thread.start()

#     def add_binpar(self,binpar,stepsize):
#         if not binpar in self.binpars:
#             self.binpars.append(binpar)

#             flag = mp.Event()
#             self.cont_flags[binpar] = flag
#             self.cont_flags[binpar].set()

#             outp, inp = mp.Pipe(duplex=False)
#             self.pipe_in[binpar] = inp
#             self.pipe_out[binpar] = outp

#             self.bin_processes[binpar] = mp.Process(t arget = continuously_bin, 
#                 args = (shared,outp,binpar,stepsize,flag))
#             self.bin_processes[binpar].start()

#     def remove_binpar(self,binpar):
#         if binpar in self.binpars:
#             self.binpars.remove(binpar)
#             self.cont_flags[binpar].clear()

#             time.sleep(0.1)
#             del self.bin_processes[binpar]
#             del self.cont_flags[binpar]
#             del self.pipe_in[binpar]
#             del self.pipe_out[binpar]

#     def get_chunks(self):
#         chunk = emptyPipe(save_output)
#         data = {}
#         for info in to_save:
#             form,new_data = info
#             if col in form:
#                 data[col] = np.append((data,new_data))
#             else:
#                 data[col] = new_data

#         new_frame = pd.DataFrame(data)
#         self.data = pd.concat(self.frame,new_frame)
#         self.shared.cols = self.data.columns
#         self.shared.data = self.data.values

#         for pipe in self pipe_in:
#             pipe.send((data.keys(),data.values()))

#         self.get_chunk_thread = th.Timer(0, self.get_chunks)
#         self.get_chunk_thread.start()

# def continuously_bin(shared, pipe, binpar, stepsize, flag):
#     minvalue = -np.inf
#     bins = []
#     group = None
#     binned = pd.DataFrame()
#     agg_func, agg_func_err = None, None

#     data_mode, error_mode, stepsize = shared.data_mode, shared.error_mode, stepsize
#     while flag.is_set():
#         new_frame = pd.DataFrame()
#         if not group:
#             # first time we are here
#             cols, values = shared.cols,shared.data
#         else:
#             cols, values = emptyPipe(pipe)

#         new_frame[cols] = values

#         agg_func, agg_func_err = define_aggs(cols)
#         args = (agg, agg_func_err, data_mode, error_mode, setpsize)

#         ## Define new bins
#         # determine what bin every row is in
#         new_frame['bin_assignment'] = new_frame[binpar] // step

#         ## align bin w.r.t. old bins:
#         # if the new minimum is bigger than the old one: shift the new 
#         # bin numbers to the right, otherwise shift the old ones to the left
#         newmin = new_frame[binpar][0] // binsize
#         if newmin >= minvalue:
#             new_frame['bin_assignment'] += newmin - minvalue
#         else:
#             binned['bin_assignment'] += minvalue - newmin
#         minvalue = min(newmin,minvalue)

#         # group new data
#         newgroup = pd.groupbBy(new_frame,'bin_assignment')
#         # rebin the affected data and store it in the new binned data
        
#         if group:
#             group = pd.concat((group,newgroup))
#             binned[newgroup.keys()] = bin(group[newgroup.keys()],args)
#         else:
#             group = newgroup
#             binned = bin(newgroup,args)

#         shared.binned = binned

# def define_aggs(columns):
#     columns = list(columns)
#     agg_func = {}
#     agg_func_err = {}
#     for c in columns:
#         if c ==  'y':
#             agg_func[c] = np.sum
#             if error_mode == 'std'
#                 agg_func_err[c+'_err'] = np.sum

#         else:
#             agg_func[c] = np.mean
#             agg_func_err[c+'_err'] = np.std
#     return agg_func, agg_func_err

# def bin(groups,agg_func,agg_func_err,data_mode,error_mode):
#     ## assumes x is the label for the binpar and y is counts
#     binned = pd.DataFrame()
#     binned[agg_func.keys()] = groups.agg(agg_func.values())
#     binned[agg_func_err.keys()] = groups.agg(agg_func_err.values())

#     if 'y' in agg_func.keys()
#         if error_mode == 'poisson':
#             binned['y_err_b'] = binned['y'] - poiss_low(binned['y'])
#             binned['y_err_t'] = poiss_high(binned['y']) - binned['y']

#             if data_mode == 'mean':
#                 binned['y_err_b'] /= binned['noe']
#                 binned['y_err_t'] /= binned['noe']

#     if data_mode == 'mean':
#         binned[agg_func_err.keys()] /= binned['noe']

#     return binned

