
fwhm = float(10) / 30000
dist = 3*fwhm

path = "\\\\cern.ch\\dfs\\Users\\c\\CRIS\\Documents\\HFS Simulator\\hfs_peaks.txt"
with open(path,'r') as f:
    peaks = f.readline()
peaks = peaks.split('\t')

peaks = sorted([float(p) for p in peaks if not p == ''])

starts = []
stops = []
i = 0
while i < len(peaks):
    print(starts,stops)
    peak = peaks[i]
    left = peak - dist
    right = peak + dist
    starts.append(left)
    for j,peak2 in enumerate(peaks[i+1:]):
        print(peak,peak2)
        input()
        left2 = peak2-dist
        right2 = peak2+dist
        if right >= left2:
            pass
        else:
            stops.append(right)
            i = i+j+1
            break
    else:
        stops.append(right2)
        break

stops_to_add = []
for i,stop in enumerate(stops[:-1]):
    starts.append(stop)
    stops_to_add.append(starts[i+1])

stops.extend(stops_to_add)
starts = sorted(starts)
stops = sorted(stops)