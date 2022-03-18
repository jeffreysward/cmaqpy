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

Finally, edit `cmaqpy/examples/ex_run_cctm.py`

1. If not rerunning MCIP, specify the location of your MCIP files using the `LOC_MCIP` variable in `cmaqpy/data/dirpaths.yml`  
2. If not rerunning MCIP, set `new_mcip=False` in your `CMAQModel` instance  
3. Specify the location of your ptertac files using the `LOC_ERTAC` variable in `cmaqpy/data/dirpaths.yml`   
3. Change `appl`  
4. Change `ertac_case` 
