This repository holds python code to help facilitate running and processing CMAQ simulations.

If you want to run a new simulation, first edit the `cmaqpy/examples/ex_run_onetime.py` script

1. Prepare the `{ertac_case}__fs_ff10_future.csv` and the `{ertac_case}_fs_ff10_hourly_future.csv`. Note that you might have to delete comments associated with Tri-Center Naniwa Energy.  
2. Change `appl`  
3. Change `ertac_case`  
4. Run `ex_run_onetime.py`  

Then, edit the `cmaqpy/examples/ex_run_daily.py` script

1. Change `appl`  
2. Change `ertac_case`  
3. Run `ex_run_daily.py`

To visualize the point source emissions, you must transfer these files to the CMAQ grid by running `cmaqpy/run_inlineto2d.csh`. Set directories and the processing date directly within the script.

Finally, edit `cmaqpy/examples/ex_run_cctm.py`

1. If not rerunning MCIP, specify the location of your MCIP files using the `LOC_MCIP` variable in `cmaqpy/data/dirpaths.yml`  
2. If not rerunning MCIP, set `new_mcip=False` in your `CMAQModel` instance  
3. Specify the location of your ptertac in-line emissiions files using the `LOC_ERTAC` variable in `cmaqpy/data/dirpaths.yml`   
3. Change `appl` 

In order to visualize the data CCTM data properly, you need to postprocess the data using the CMAQ `combine` utility program which is located in `${CMAQ_HOME}/POST/combine`. Unfortunately, I have yet to add this step to the `runcamq` module so you have to manually edit `combine/scripts/run_combine.csh`
1. Change `APPL`  
2. Change `START_DATE`  
3. Change `END_DATE`  
4. Run the script using `sbatch run_combine.csh`, which should take several minutes per day of simulaiton time with the default calcualtions. 
