import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.io.shapereader as shpreader
from matplotlib import cm
from matplotlib import colors
import monet as m
import numpy as np
import pandas as pd
import wrf as wrfpy
import xarray as xr


def get_proj(ds):
    """
    Extracts information about the CMAQ grid projection from the proj4_srs attribute
    in an output file dataset.

    :param ds:
    :return:
    """
    proj_params = ds.proj4_srs
    proj_params = proj_params.replace(' ', '')
    proj_params = proj_params.split('+')
    proj = proj_params[1].split('=')[1]
    truelat1 = float(proj_params[2].split('=')[1])
    truelat2 = float(proj_params[3].split('=')[1])
    central_latitude = float(proj_params[4].split('=')[1])
    central_longitude = float(proj_params[5].split('=')[1])

    if proj == 'lcc':
        cartopy_crs = ccrs.LambertConformal(central_longitude=central_longitude,
                                            central_latitude=central_latitude,
                                            standard_parallels=[truelat1, truelat2])
        return cartopy_crs
    else:
        raise ValueError('Your projection is not the expected Lambert Conformal.')


def get_domain_boundary(ds, cartopy_crs):
    """
    Finds the boundary of the WRF domain.

    :param ds:
    :param cartopy_crs:
    :return:
    """
    # Rename the lat-lon corrdinates to get wrf-python to recognize them
    variables = {'latitude': 'XLAT',
                 'longitude': 'XLONG'}
    try:
        ds = xr.Dataset.rename(ds, variables)
    except ValueError:
        print(f'Variables {variables} cannot be renamed, '
                f'those on the left are not in this dataset.')

    # I need to manually convert the boundaries of the WRF domain into Plate Carree to set the limits.
    # Get the raw map bounds using a wrf-python utility
    raw_bounds = wrfpy.util.geo_bounds(ds)

    # Get the projected bounds telling cartopy that the input coordinates are lat/lon (Plate Carree)
    projected_bounds = cartopy_crs.transform_points(ccrs.PlateCarree(),
                                                    np.array([raw_bounds.bottom_left.lon, raw_bounds.top_right.lon]),
                                                    np.array([raw_bounds.bottom_left.lat, raw_bounds.top_right.lat]))
    return projected_bounds


def conc_map(plot_var, cmap=cm.get_cmap('bwr'), figsize=(8,8), ax=None, cartopy_crs=None, proj_bounds=None,
    vmin=-1, vmax=1, cbar_args={}, savefig=False, figpath='conc_map.png'):
    """
    Creates a filled colormap across the full domain in the native (Lambert
    Conformal) map projection.
    """
    if ax is None:
        # Create a figure
        fig = plt.figure(figsize=figsize)

        # Set the GeoAxes to the projection used by WRF
        ax = fig.add_subplot(1, 1, 1, projection=cartopy_crs)

    # Normalize the values, so that the colorbar plots correctly
    norm = colors.Normalize(vmin=vmin, vmax=vmax)

    # Create the pcolormesh 
    cn = ax.pcolormesh(wrfpy.to_np(plot_var.longitude), wrfpy.to_np(plot_var.latitude), wrfpy.to_np(plot_var),
                       transform=ccrs.PlateCarree(), 
                       cmap=cmap,
                       norm=norm,
                       )
    if proj_bounds is not None:
        # Format the projected bounds so they can be used in the xlim and ylim attributes
        proj_xbounds = [proj_bounds[0, 0], proj_bounds[1, 0]]
        proj_ybounds = [proj_bounds[0, 1], proj_bounds[1, 1]]

        # Finally, set the x and y limits
        ax.set_xlim(proj_xbounds)
        ax.set_ylim(proj_ybounds)

    # Download and add the states, coastlines, and lakes
    shapename = 'admin_1_states_provinces_lakes'
    states_shp = shpreader.natural_earth(resolution='10m',
                                        category='cultural', 
                                        name=shapename)
    # Add features to the maps
    ax.add_geometries(
        shpreader.Reader(states_shp).geometries(),
        ccrs.PlateCarree(),
        facecolor='none',
        linewidth=.5, 
        edgecolor="black"
        )

    # Add features to the maps
    # ax.add_feature(cfeature.LAKES)
    # ax.add_feature(cfeature.OCEAN)

    # Add color bars
    if "cbar_ticks" not in cbar_args:
        cbar_args["cbar_ticks"] = None
    if "cbar_label" not in cbar_args:
        cbar_args["cbar_label"] = 'Concentration'
    if "shrink" not in cbar_args:
        cbar_args["shrink"] = 1
    if "pad" not in cbar_args:
        cbar_args["pad"] = 0.05

    cbar = plt.colorbar(cn,
                        ax=ax,
                        ticks=cbar_args["cbar_ticks"],
                        label=cbar_args["cbar_label"],
                        shrink=cbar_args["shrink"],
                        pad=cbar_args["pad"]
                        )

    # Save the figure(s)
    if savefig:
        plt.savefig(figpath, dpi=300, transparent=True, bbox_inches='tight')


def pollution_plot(da, vmin=0, vmax=12, cmap=cm.get_cmap('YlOrBr'),
                   extent=None, cbar_label='PM$_{2.5}$ ($\mu g/m^{3}$)', figsize=(15,7),
                   titlestr='Title', savefig=False, figpath='./pollution_plot.png'):
    """
    Creates a filled colormap using the Plate Carree projectsion across a 
    user-defined section of the domain (defaults to the full domain) using 
    the monit package paradigm.
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
