import matplotlib.pyplot as plt
import cartopy.crs as ccrs
from matplotlib import cm
import monet as m

def pollution_plot(da, vmin=0, vmax=12, cmap=cm.get_cmap('YlOrBr'), cbar_label='PM$_{2.5}$ ($\mu g/m^{3}$)', titlestr='Title', savefig=False, figpath='./pollution_plot.png'):
    # This creates a more involved plot
    extent = [da.longitude.min(), da.longitude.max(), da.latitude.min(), da.latitude.max() - 2]
    ax = m.plots.draw_map(states=True, resolution='10m',  linewidth=0.5, figsize=(15,7), extent=extent, subplot_kw={'projection': ccrs.PlateCarree()})
    p = da.plot(x='longitude', y='latitude', ax=ax, robust=True, 
                vmin=vmin, vmax=vmax, cmap=cmap,
                cbar_kwargs={'label': cbar_label},
                )
    if titlestr is not None:
        ax.set_title(titlestr)
    if savefig:
        plt.savefig(figpath)
    else:
        plt.show()