"""
This example shows how to process wrfout files with MCIP using the `CMAQModel` class.

Note that MCIP will fail if your `start_datetime` is not AFTER the fist timestep of 
your wrfout*.nc file.
"""

from cmaqpy.runcmaq import CMAQModel

start_datetime = 'August 05, 2016 01:00:00'  # second timestep in the wrfout file
end_datetime = 'August 15, 2016 23:00:00'  # second to last timestep in the wrfout file
appl = '2016_12OTC2'
coord_name = 'LAM_40N97W'
grid_name = '12OTC2'

# Create a CMAQModel object
cmaq_sim = CMAQModel(start_datetime, end_datetime, appl, coord_name, grid_name, verbose=True)
# Specify the meteorolocial files
metfile_list = ['wrfout_d01_2016-08-05_00:00:00']
# Call the "run_mcip" method in "setup_only" mode
cmaq_sim.run_mcip(metfile_list=metfile_list, geo_file='geo_em.d01.nc', t_step=60, setup_only=False)
