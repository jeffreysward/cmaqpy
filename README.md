This repository holds python code to help facilitate running and processing CMAQ simulations.

## Run a new simulation on the 12-km domain
### SMOKE
If you want to run a new simulation, first edit the `examples/ex_run_onetime.py` script. To make it easy on yourself, I suggest opening your `NEI_HOME` directory in a separate VSCode window, so you can quickly navigate around the `intermed`, `reports`, and `smoke_out` directories.  

1. Prepare the `{ertac_case}__fs_ff10_future.csv` and the `{ertac_case}_fs_ff10_hourly_future.csv`. Note that you might have to delete comments associated with Tri-Center Naniwa Energy.  
2. Change `appl`. The available options are commented out in the example script.    
3. Change `ertac_case`. The only options that I have developed thus far are `CONUS2016_Base` (the base case) and `CONUS2016_S0` (the with renewables case).    
4. Run `ex_run_onetime.py`. This step should take about 2 hours to run and creates the grid-specific `stack_groups_ptertac` file.     

Then, edit the `examples/ex_run_daily.py` script

1. Change `appl`  
2. Change `ertac_case`  
3. Run `ex_run_daily.py`. This step should take about xx minutes to run and creates a grid-specific `inln_mole_ptertac` for each day in the month. NEI designed it's scripts to easily process the full year, so it's easiest to process data in monthly incriments. 
4. If this is not the base case, I manually rename the `smoke_out` directory to append the scenario (e.g., `ptertac_s0`). Yes, I know, there must be a better way of doing this...  

To visualize the point source emissions, you must transfer these files to the CMAQ grid by running `runsmoke.run_inlineto2d`. Note that you must run this fucntion separately for each day that you would like processed.

### CCTM
Finally, edit `examples/ex_run_cctm.py`

1. If not rerunning MCIP, specify the location of your MCIP files using the `LOC_MCIP` variable in `data/dirpaths.yml`  
2. If not rerunning MCIP, set `new_mcip=False` in your `CMAQModel` instance  
3. Specify the location of your initial and boundary conditions using the `LOC_IC` and `LOC_BC` variables in `data/dirpaths.yml`
3. Specify the location of your ptertac in-line emissiions files using the `LOC_ERTAC` variable in `data/dirpaths.yml`   
3. Change `appl` 

### Combine
In order to visualize the data CCTM data properly, you need to postprocess the data using the CMAQ `combine` utility program which is located in `${CMAQ_HOME}/POST/combine`. Unfortunately, I have yet to add this step to the `runcamq` module so you have to manually edit `combine/scripts/run_combine.csh`
1. Change `APPL`  
2. Change `START_DATE`  
3. Change `END_DATE`  
4. Run the script using `sbatch run_combine.csh`, which should take several minutes per day of simulaiton time with the default calcualtions. 

## Run a new simulation on the 4-km domian
### SMOKE
If you want to run the 4-km domain after running a simulation on the 12-km domain, many of the steps remain the same. Start by editing the `cmaqpy/examples/ex_run_onetime.py` script.
1. Change `appl`. The available options are commented out in the example script.  
2. Change `ertac_case`. The only options that I have developed thus far are `CONUS2016_Base` (the base case) and `CONUS2016_S0` (the with renewables case).  
3. Run `ex_run_onetime.py`. This step should take about 2 hours to run, and creates the grid-specific `stack_groups_ptertac*` file.    

Then, edit the `examples/ex_run_daily.py` script

1. Change `appl`  
2. Change `ertac_case`  
3. Run `ex_run_daily.py`. This step should take about an hour to run and creates a grid-specific `inln_mole_ptertac` for each day in the month.  
4. If this is not the base case, I manually rename the `smoke_out` directory to append the scenario (e.g., `ptertac_s0`).  

### MCIP
If you need to run MCIP, edit the `examples/ex_run_mcip.py` script  

1. Change `appl`
2. Make sure that the start and end dates are correct.
3. Run `ex_run_mcip.py`. Each day takes just over a minute to run on Magma.

### ICON
If you need to run ICON, edit the `examples/ex_run_icon.py` script. 

1. Change `appl`
2. Make sure that the start and end dates are correct. 
3. Change the `coarse_grid_appl`

Note that I'm just using the simulations transferred to us from NYDEC as boundary conditions, so I just simply change the `LOC_IC` variable in `data/dirpaths.yml` rather than actually run ICON. 

### BCON
If you need to run BCON, edit the `examples/ex_run_bcon.py` script

1. Change `appl`
2. Make sure that the start and end dates are correct. 
3. Check the `coarse_grid_appl`

### CCTM
Finally, edit `examples/ex_run_cctm.py`

1. If not running MCIP, specify the location of your MCIP files using the `LOC_MCIP` variable in `data/dirpaths.yml` and set `new_mcip=False` in your `CMAQModel` instance.  
2. If not running BCON, specify the location of you BCON files using the `LOC_BC` variable in `data/dirpaths.yml` and set `new_bcon=False` in your `CMAQModel` instance.
3. Specify the name of your ptertac in-line emissiions files in the `LOC_ERTAC` variable in `data/dirpaths.yml`.   
4. Change `appl`
