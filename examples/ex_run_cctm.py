"""
This example shows how to run the CCTM benchmark case using the `CMAQModel` class.

You should run this inside a tmux window because this ties up the terminal.
"""

from cmaqpy.runcmaq import CMAQModel

# Specify the start/end times
start_datetime = 'August 06, 2016'  # first day that you want run
end_datetime = 'August 14, 2016'  # last day you want run

# Specify if you want to run the 12 km or the 4 km domain
appl = '2016_12OTC2'
# appl = '2016_4OTC2'

# Specify if you want to run or just setup cctm
setup_only = True

# Define the coordinate name (must match that in GRIDDESC)
coord_name = 'LAM_40N97W'
if appl == '2016_12OTC2':
    grid_name = '12OTC2'
elif appl == '2016_4OTC2':
    grid_name = '4OTC2'

# Create a CMAQModel object
cmaq_sim = CMAQModel(start_datetime, end_datetime, appl, coord_name, grid_name, new_mcip=True, verbose=True)

# Call the "run_cctm" method
if appl == '2016_12OTC2':
    cmaq_sim.run_cctm(delete_existing_output='TRUE', new_sim='FALSE', tstep='010000', 
    cctm_hours=24, n_procs=48, gb_mem=50, run_hours=72, setup_only=setup_only)
elif appl == '2016_4OTC2':
    cmaq_sim.run_cctm(delete_existing_output='TRUE', new_sim='FALSE', tstep='010000', 
    cctm_hours=24, n_procs=48, gb_mem=50, run_hours=72, setup_only=setup_only)
