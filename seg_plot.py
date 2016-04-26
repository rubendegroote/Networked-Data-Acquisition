#!/usr/bin/env python
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt


class bullseye_plot(object):
    """    Parameters
    ----------
    ax : axes
    data : list of int and float
        The intensity values for each of the 9 segments
    cmap : ColorMap or None, optional
        Optional argument to set the desired colormap
    norm : Normalize or None, optional """

    def __init__(self):
        super(bullseye_plot, self).__init__()

    def plot(self, ax, data, cmap=None, norm=None):

        ax.clear()

        linewidth = 13 # convert segment spacing to pixels here
        radius=12.5
        data = np.array(data).ravel()

        if cmap is None:
            cmap = plt.cm.jet

        if norm is None:
            norm = mpl.colors.Normalize(vmin=data.min(), vmax=data.max())

        theta = np.linspace(0, 2*np.pi, 768)

        r=np.array([1.5,5.5,12.5])

        # Create the bound for the segment 9
        for i in range(3):
            ax.plot(theta, np.repeat(r[i], theta.shape), '-k', lw=linewidth)

        # Create the bounds for the segments 8-5
        for i in range(4):
            theta_i = i*90*np.pi/180
            ax.plot([theta_i, theta_i], [r[0], r[1]], '-k', lw=linewidth)

        # Create the bounds for the segments  1-4
        for i in range(4):
            theta_i = i*90*np.pi/180
            ax.plot([theta_i, theta_i], [r[1], radius], '-k', lw=linewidth)

        # Fill the segments 1-4
        r0 = r[1:3]
        r0 = np.repeat(r0[:, np.newaxis], 192, axis=1).T
        for i in range(4):
            theta0 = theta[i*192:i*192+192]
            theta0 = np.repeat(theta0[:, np.newaxis], 2, axis=1)
            z = np.ones((192, 2))*data[i]
            ax.pcolormesh(theta0, r0, z, cmap=cmap, norm=norm)

        # Fill the segments 5-8
        r0 = r[0:2]
        r0 = np.repeat(r0[:, np.newaxis], 192, axis=1).T
        for i in range(4):
            theta0 = theta[i*192:i*192+192]
            theta0 = np.repeat(theta0[:, np.newaxis], 2, axis=1)
            z = np.ones((192, 2))*data[i+4]
            ax.pcolormesh(theta0, r0, z, cmap=cmap, norm=norm)

        # Fill the segment 9
        if data.size == 9:
            r0 = np.array([0, r[0]])
            r0 = np.repeat(r0[:, np.newaxis], theta.size, axis=1).T
            theta0 = np.repeat(theta[:, np.newaxis], 2, axis=1)
            z = np.ones((theta.size, 2))*data[8]
            ax.pcolormesh(theta0, r0, z, cmap=cmap, norm=norm)


        ax.set_ylim([0, radius])
        ax.set_yticklabels([])
        ax.set_xticklabels([])

        #self.canvas.draw()

if __name__ == '__main__':
    # Create fake data
    data=np.array([1.1E-13,1.2E-13,3E-13,4.3E-13,2.3E-13,1.2E-13,0.3E-13,0.7E-13,0.9E-13])


    print(data)
    print(max(data))


    # Make a figure and axes with dimensions as desired.
    fig = plt.figure(figsize=(7, 5))
    ax=plt.subplot(projection='polar')
    fig.canvas.set_window_title('test GUI')

    # Create the axis for the colorbars
    axl=fig.add_axes([0.85, 0.2, 0.05, 0.5])

    # Set the colormap and norm to correspond to the data for which the colorbar will be used.
    cmap = mpl.cm.jet
    #cmap = mpl.cm.hot

    norm = mpl.colors.Normalize(vmin=min(data), vmax=max(data))

    cb1 = mpl.colorbar.ColorbarBase(axl, cmap=cmap, norm=norm, orientation='vertical')
    cb1.set_label('Amperes')

    # Create the 9 segment model
    bullseye_plot(ax, data, cmap=cmap, norm=norm)
    ax.set_title('Segmented Faraday cup')

    plt.ion()

    while True:
        norm = mpl.colors.Normalize(vmin=min(data), vmax=max(data))
        cb1 = mpl.colorbar.ColorbarBase(axl, cmap=cmap, norm=norm, orientation='vertical')
        cb1.set_label('Amperes')

        for x in range(0,9):
            data[x] = np.random.random()
        print(data)
        bullseye_plot(ax, data, cmap=cmap, norm=norm)
        plt.draw()
        plt.pause(0.300)
