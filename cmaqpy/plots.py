import matplotlib.pyplot as plt
import cartopy.crs as ccrs
from matplotlib import cm
import monet as m
import pandas as pd


def pollution_plot(da, vmin=0, vmax=12, cmap=cm.get_cmap('YlOrBr'),
                   extent=None, cbar_label='PM$_{2.5}$ ($\mu g/m^{3}$)', figsize=(15,7),
                   titlestr='Title', savefig=False, figpath='./pollution_plot.png'):
    """
    Creates a filled colormap across a user-defined section of the domain 
    (defaults to the full domain).
    """
    if extent is None:
        extent = [da.longitude.min(), da.longitude.max(), da.latitude.min(), da.latitude.max() - 2]
    ax = m.plots.draw_map(states=True, resolution='10m',  linewidth=0.5, figsize=figsize, extent=extent, subplot_kw={'projection': ccrs.PlateCarree()})
    p = da.plot(x='longitude', y='latitude', ax=ax, robust=True, 
                vmin=vmin, vmax=vmax, cmap=cmap,
                cbar_kwargs={'label': cbar_label, 
                             'extend': 'neither'},
                )
    if titlestr is not None:
        ax.set_title(titlestr)
    if savefig:
        plt.savefig(figpath, dpi=300, transparent=True, bbox_inches='tight')
    else:
        plt.show()


def conc_compare(da1, da2, extent=None,
                 vmin1=0, vmax1=10, vmin2=-1, vmax2=1, cmap1=cm.get_cmap('YlOrBr'), cmap2=cm.get_cmap('bwr'),
                 cbar_label1='PM$_{2.5}$ ($\mu g/m^{3}$)', cbar_label2='PM$_{2.5}$ Difference (%)',
                 titlestr1=None, titlestr2=None,
                 figsize=(15,7), savefig=False, figpath1='./conc_compare1.png', figpath2='./conc_compare2.png'):
    """
    Creates two filled colormaps for concentration comparisons.
    """
    # f, (ax1, ax2) = plt.subplots(nrows=2, ncols=1, figsize=fsize)
    if extent is None:
        extent = [da1.longitude.min(), da1.longitude.max(), da1.latitude.min(), da1.latitude.max() - 2]
    f1, ax1 = m.plots.draw_map(states=True, resolution='10m', figsize=figsize,  linewidth=0.5, extent=extent, subplot_kw={'projection': ccrs.PlateCarree()}, return_fig=True)
    f2, ax2 = m.plots.draw_map(states=True, resolution='10m', figsize=figsize,  linewidth=0.5,  extent=extent, subplot_kw={'projection': ccrs.PlateCarree()}, return_fig=True)
    # f.axes.append(ax2)
    da1.plot(x='longitude', y='latitude', ax=ax1, robust=True, 
            vmin=vmin1, vmax=vmax1, cmap=cmap1,
            cbar_kwargs={'label': cbar_label1, 'extend': 'neither'},
            )
    da2.plot(x='longitude', y='latitude', ax=ax2, robust=True, 
            vmin=vmin2, vmax=vmax2, cmap=cmap2,
            cbar_kwargs={'label': cbar_label2, 'extend': 'neither'},
            )

    if titlestr1 is not None:
        ax1.set_title(titlestr1)
    if titlestr2 is not None:
        ax2.set_title(titlestr2)
    if savefig:
        f1.savefig(figpath1, dpi=300, transparent=True, bbox_inches='tight')
        f2.savefig(figpath2, dpi=300, transparent=True, bbox_inches='tight')
    else:
        f1.show()
        f2.show()


def prof_change(gen_idx, gen_df1, gen_df2, date=None, column_names=['Base Case', 'w/ Renewables'],
               figsize=(7,3), colors=['purple','orange'], linewidth=2, linestyles=['-','-.'], 
               titlestr1='', ylabelstr='Power (MW)', 
               savefig=False, outfile_pfix='../cmaqpy/data/plots/gen_profs_'):
    """
    Plots changes in generation or emissions profiles for a user-specified unit.
    """
    if date is None:
        change_df1 = pd.concat([gen_df1.iloc[gen_idx,5:], gen_df2.iloc[gen_idx,5:]], axis=1)
    else:
        change_df1 = pd.concat([gen_df1.loc[gen_idx,pd.Timestamp(f'{date} 00'):pd.Timestamp(f'{date} 23')], gen_df2.loc[gen_idx,pd.Timestamp(f'{date} 00'):pd.Timestamp(f'{date} 23')]], axis=1)
    change_df1.columns = column_names

    f = plt.figure(figsize=figsize)
    ax1 = f.gca()
    change_df1.plot(color=colors, linewidth=linewidth, style=linestyles, ax=ax1)

    ax1.legend(loc='lower center', bbox_to_anchor=(0.5, -0.5), ncol=2)
    ax1.set_title(f'{gen_df1["NYISO Name"][gen_idx]} {titlestr1}')
    ax1.set_ylabel(ylabelstr)
    if savefig:
        plt.savefig(f'{outfile_pfix}{gen_df1["NYISO Name"][gen_idx]}.png', dpi=300, transparent=True, bbox_inches='tight')
    else:
        plt.show()


def prof_compare(gen_idx1, gen_idx2, gen_df1, gen_df2, date=None, column_names=['Base Case', 'w/ Renewables'],
               figsize=(7,7), colors=['purple','orange'], linewidth=2, linestyles=['-','-.'], 
               titlestr1='(baseload/load following)', titlestr2='(peaking)', ylabelstr='Power (MW)', 
               savefig=False, outfile_pfix='../cmaqpy/data/plots/gen_profs_'):

    """
    Compares changes in generation or emissions for two user-specified units.
    """
    if date is None:
        change_df1 = pd.concat([gen_df1.iloc[gen_idx1,5:], gen_df2.iloc[gen_idx1,5:]], axis=1)
    else:
        change_df1 = pd.concat([gen_df1.loc[gen_idx1,pd.Timestamp(f'{date} 00'):pd.Timestamp(f'{date} 23')], gen_df2.loc[gen_idx1,pd.Timestamp(f'{date} 00'):pd.Timestamp(f'{date} 23')]], axis=1)
    change_df1.columns = column_names
    if date is None:
        change_df2 = pd.concat([gen_df1.iloc[gen_idx2,5:], gen_df2.iloc[gen_idx2,5:]], axis=1)
    else:
        change_df2 = pd.concat([gen_df1.loc[gen_idx2,pd.Timestamp(f'{date} 00'):pd.Timestamp(f'{date} 23')], gen_df2.loc[gen_idx2,pd.Timestamp(f'{date} 00'):pd.Timestamp(f'{date} 23')]], axis=1)
    change_df2.columns = column_names

    _, (ax1, ax2) = plt.subplots(nrows=2, ncols=1, sharex=True, figsize=figsize)
    change_df1.plot(color=colors, linewidth=linewidth, style=linestyles, ax=ax1)
    change_df2.plot(color=colors, linewidth=linewidth, style=linestyles, ax=ax2)

    ax1.get_legend().remove()
    ax2.legend(loc='lower center', bbox_to_anchor=(0.5, -0.5), ncol=2)
    ax1.set_title(f'{gen_df1["NYISO Name"][gen_idx1]} {titlestr1}')
    ax2.set_title(f'{gen_df1["NYISO Name"][gen_idx2]} {titlestr2}')
    ax1.set_ylabel(ylabelstr)
    ax2.set_ylabel(ylabelstr)
    if savefig:
        plt.savefig(f'{outfile_pfix}{gen_df1["NYISO Name"][gen_idx1]}_{gen_df1["NYISO Name"][gen_idx2]}.png', dpi=300, transparent=True, bbox_inches='tight')
    else:
        plt.show()
