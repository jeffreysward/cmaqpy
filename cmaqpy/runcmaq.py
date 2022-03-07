import datetime
import os
import sys
import time
from . import utils
from .data.fetch_data import fetch_yaml


class CMAQModel:
    """
    This class provides a framework for running the CMAQ Model.
    """
    def __init__(self, start_datetime, end_datetime, appl, coord_name, grid_name, chem_mech ='cb6r3_ae7_aq', setup_yaml='dirpaths.yml', compiler='gcc', compiler_vrsn='9.3.1', verbose=False):
        self.appl = appl
        self.coord_name = coord_name
        self.grid_name = grid_name
        self.chem_mech = chem_mech
        self.compiler = compiler
        self.compiler_vrsn = compiler_vrsn
        self.verbose = verbose
        if self.verbose:
            print(f'Application name: {self.appl}\nCoordinate name: {self.coord_name}\nGrid name: {self.grid_name}')

        # Format the forecast start/end and determine the total time.
        self.start_datetime = utils.format_date(start_datetime)
        self.end_datetime = utils.format_date(end_datetime)
        self.delt = self.end_datetime - self.start_datetime
        if self.verbose:
            print(f'CMAQ run starting on: {self.start_datetime}')
            print(f'CMAQ run ending on: {self.end_datetime}')

        # Set working and WRF model directory names
        dirs = fetch_yaml(setup_yaml)
        dirpaths = dirs.get('directory_paths')
        self.CMAQ_HOME = dirpaths.get('CMAQ_HOME')
        self.MCIP_SCRIPTS = f'{self.CMAQ_HOME}/PREP/mcip/scripts'
        self.ICON_SCRIPTS = f'{self.CMAQ_HOME}/PREP/icon/scripts'
        self.BCON_SCRIPTS = f'{self.CMAQ_HOME}/PREP/bcon/scripts'
        self.CCTM_SCRIPTS = f'{self.CMAQ_HOME}/CCTM/scripts'
        self.CMAQ_DATA = dirpaths.get('CMAQ_DATA')
        self.DIR_TEMPLATES = dirpaths.get('DIR_TEMPLATES')
        self.InMetDir = dirpaths.get('InMetDir')
        self.InGeoDir = dirpaths.get('InGeoDir')

        # Define the names of the CMAQ output files

        # Define linux command aliai
        self.CMD_LN = 'ln -sf %s %s'
        self.CMD_CP = 'cp %s %s'
        self.CMD_MV = 'mv %s %s'
        self.CMD_RM = 'rm %s'
        self.CMD_MCIP = f'sbatch --requeue {self.MCIP_SCRIPTS}/run_mcip.csh'
        self.CMD_ICON = f'{self.ICON_SCRIPTS}/run_icon.csh >& {self.MCIP_SCRIPTS}/run_icon_{self.appl}.log'
        self.CMD_BCON = f'{self.BCON_SCRIPTS}/run_bcon.csh >& {self.MCIP_SCRIPTS}/run_bcon_{self.appl}.log'
        self.CMD_CCTM = f'sbatch --requeue {self.CCTM_SCRIPTS}/submit_cctm.csh'

    def run_mcip(self, mcip_start_datetime=None, mcip_end_datetime=None, metfile_list=[], geo_file='geo_em.d01.nc', t_step=60, run_hours=4, setup_only=False):
        """
        Setup and run MCIP, which formats meteorological files (e.g. wrfout*.nc) for CMAQ.
        """
        ## SETUP MCIP
        # Copy the template MCIP run script to the scripts directory
        run_mcip_path = f'{self.MCIP_SCRIPTS}/run_mcip.csh'
        cmd = self.CMD_CP % (f'{self.DIR_TEMPLATES}/template_run_mcip.csh', run_mcip_path)
        os.system(cmd)

        # Write Slurm info
        mcip_slurm =  f'#SBATCH -J mcip_{self.appl}		# Job name'
        mcip_slurm =+ f'#SBATCH -o {self.MCIP_SCRIPTS}/run_mcip_{self.appl}_%j.log'
        mcip_slurm =+ f'#SBATCH --nodes=1		# Total number of nodes requested' 
        mcip_slurm =+ f'#SBATCH --ntasks=1		# Total number of tasks to be configured for.' 
        mcip_slurm =+ f'#SBATCH --tasks-per-node=1	# sets number of tasks to run on each node.' 
        mcip_slurm =+ f'#SBATCH --cpus-per-task=1	# sets number of cpus needed by each task.'
        mcip_slurm =+ f'#SBATCH --get-user-env		# tells sbatch to retrieve the users login environment.' 
        mcip_slurm =+ f'#SBATCH -t {run_hours}:00:00		# Run time (hh:mm:ss)' 
        mcip_slurm =+ f'#SBATCH --mem=20000M		# memory required per node'
        mcip_slurm =+ f'#SBATCH --partition=default_cpu	# Which queue it should run on.'
        utils.write_to_template(run_mcip_path, mcip_slurm, id='%SLURM%') 

        # Write IO info to the MCIP run script
        mcip_io =  f'source {self.CMAQ_HOME}/config_cmaq.csh {self.compiler} {self.compiler_vrsn}\n'
        mcip_io += f'set APPL       = {self.appl}\n'
        mcip_io += f'set CoordName  = {self.coord_name}\n'
        mcip_io += f'set GridName   = {self.grid_name}\n'
        mcip_io += f'set DataPath   = {self.CMAQ_DATA}\n'
        mcip_io += f'set InMetDir   = {self.InMetDir}\n'
        mcip_io += f'set InGeoDir   = {self.InGeoDir}\n'
        mcip_io += f'set OutDir     = $DataPath/$APPL/mcip\n'
        mcip_io += f'set ProgDir    = $CMAQ_HOME/PREP/mcip/src\n'
        mcip_io += f'set WorkDir    = $OutDir\n'
        utils.write_to_template(run_mcip_path, mcip_io, id='%IO%')

        # Write met info to the MCIP run script
        mcip_met = f'set InMetFiles = ( ' 
        for ii, metfile in enumerate(metfile_list):
            if ii < len(metfile_list) - 1:
                mcip_met += f'$InMetDir/{metfile} \\\n'
            else:
                mcip_met += f'$InMetDir/{metfile} )\n'
        mcip_met += f'set IfGeo      = "F"\n'
        mcip_met += f'set InGeoFile  = {self.InGeoDir}/{geo_file}\n'
        utils.write_to_template(run_mcip_path, mcip_met, id='%MET%')

        # Write start/end info to MCIP run script
        if mcip_start_datetime is None:
            mcip_start_datetime = self.start_datetime
        else:
            mcip_start_datetime = utils.format_date(mcip_start_datetime)
        if mcip_end_datetime is None:
            mcip_end_datetime = self.end_datetime
        else:
            mcip_end_datetime = utils.format_date(mcip_end_datetime)
        mcip_time =  f'set MCIP_START = {mcip_start_datetime.strftime("%Y-%m-%d_%H:%M:%S.0000")}\n'  # [UTC]
        mcip_time += f'set MCIP_END   = {mcip_end_datetime.strftime("%Y-%m-%d_%H:%M:%S.0000")}\n'  # [UTC]
        mcip_time += f'set INTVL      = {t_step}\n' # [min]
        utils.write_to_template(run_mcip_path, mcip_time, id='%TIME%')

        if self.verbose:
            print('Done writing MCIP run script!\n')

        ## RUN MCIP
        if not setup_only:
            # Begin MCIP simulation clock
            simstart = datetime.datetime.now()
            if self.verbose:
                print('Starting MCIP at: ' + str(simstart))
                sys.stdout.flush()
            os.system(self.CMD_MCIP)
            # Sleep until the run_mcip_{self.appl}.log file exists
            while not os.path.exists(f'{self.MCIP_SCRIPTS}/run_mcip_{self.appl}.log'):
                time.sleep(1)
            mcip_sim = self.finish_check('mcip')
            while mcip_sim != 'complete':
                if mcip_sim == 'failed':
                    return False
                else:
                    time.sleep(2)
                    mcip_sim = self.finish_check('mcip')
            elapsed = datetime.datetime.now() - simstart
            if self.verbose:
                print(f'MCIP ran in: {utils.strfdelta(elapsed)}')
        return True

    def run_mcip_multiday(self, metfile_dir=None, metfile_list=[], geo_file='geo_em.d01.nc', t_step=60):
        """
        Run MCIP over multiple days. Per CMAQ convention, daily MCIP files contain
        25 hours each all the hours from the current day, and the first hour (00:00)
        from the following day. 
        """
        # Loop over each day
        success = True
        for day_no in range(self.delt.days):
            # Set the start datetime, end datetime, and metfile list for the day
            mcip_start_datetime = self.start_datetime + datetime.timedelta(day_no)
            mcip_end_datetime = self.start_datetime + datetime.timedelta(day_no + 1)
            if metfile_dir is None:
                # If all the met data is stored in the same file, pass that file in 
                # using metfile_list and set metfile_dir=None
                metfile_list = metfile_list
            else:
                # Eventually, can add scripting here that assumes there's a different
                # wrfout file produced every day and they are all located in metfile_dir.
                pass

            # run mcip for that day
            while success:
                success = self.run_mcip(self, mcip_start_datetime=mcip_start_datetime, mcip_end_datetime=mcip_end_datetime, metfile_list=metfile_list, geo_file=geo_file, t_step=t_step, setup_only=False)  
        

    def run_icon(self, type='regrid', coarse_grid_name='coarse', cctm_pfx='CCTM_CONC_v53_', setup_only=False):
        """
        Setup and run ICON, which produces initial conditions for CMAQ.
        """
        ## SETUP ICON
        # Copy the template ICON run script to the scripts directory
        run_icon_path = f'{self.ICON_SCRIPTS}/run_icon.csh'
        cmd = self.CMD_CP % (f'{self.DIR_TEMPLATES}/template_run_icon.csh', run_icon_path)
        os.system(cmd)

        # Write ICON runtime info to the run script.
        icon_runtime = f'#> Source the config_cmaq file to set the run environment\n'
        icon_runtime += f'source {self.CMAQ_HOME}/config_cmaq.csh {self.compiler} {self.compiler_vrsn}\n'
        #> Code Version
        icon_runtime += f'set VRSN     = v532\n'
        #> Application Name                    
        icon_runtime += f'set APPL       = {self.appl}\n'
        #> Initial conditions type [profile|regrid]
        icon_runtime += f'ICTYPE   = {type}\n'
        #> check GRIDDESC file for GRID_NAME options
        icon_runtime += f'setenv GRID_NAME {self.grid_name}\n'
        #> grid description file path
        icon_runtime += f'setenv GRIDDESC {self.CMAQ_DATA}/{self.appl}/mcip/GRIDDESC\n'
        #> GCTP spheroid, use 20 for WRF-based modeling
        icon_runtime += f'setenv IOAPI_ISPH 20\n'
        #> turn on excess WRITE3 logging [ options: T | F ]
        icon_runtime += f'setenv IOAPI_LOG_WRITE F\n'
        #> support large timestep records (>2GB/timestep record) [ options: YES | NO ]     
        icon_runtime += f'setenv IOAPI_OFFSET_64 YES\n'
        #> output file directory   
        icon_runtime += f'OUTDIR   = {self.CMAQ_DATA}/{self.appl}/icon\n'
        #> define the model execution id
        icon_runtime += f'setenv EXECUTION_ID $EXEC\n'
        utils.write_to_template(run_icon_path, icon_runtime, id='%RUNTIME%')

        # Write input file info to the run script
        icon_files =  f'    setenv SDATE           {self.start_datetime.strftime("%Y%j")}\n'
        icon_files += f'    setenv STIME           {self.start_datetime.strftime("%H%M%S")}\n'
        icon_files += f'if ( $ICON_TYPE == regrid ) then\n'
        icon_files += f'    setenv CTM_CONC_1 {self.CMAQ_DATA}/{coarse_grid_name}/cctm/{cctm_pfx}{self.start_datetime.strftime("%Y%m%d")}.nc\n'
        icon_files += f'    setenv MET_CRO_3D_CRS {self.CMAQ_DATA}/{coarse_grid_name}/mcip/METCRO3D_{self.start_datetime.strftime("%y%m%d")}\n'
        icon_files += f'    setenv MET_CRO_3D_FIN {self.CMAQ_DATA}/{self.appl}/mcip/METCRO3D_{self.start_datetime.strftime("%y%m%d")}.nc\n'
        icon_files += f'    setenv INIT_CONC_1    "$OUTDIR/ICON_$VRSN_{self.appl}_{type}_{self.start_datetime.strftime("%Y%m%d")} -v"\n'
        icon_files += f'endif\n'
        icon_files += f'if ( $ICON_TYPE == profile ) then\n'
        icon_files += f'    setenv IC_PROFILE $BLD/avprofile_cb6r3m_ae7_kmtbr_hemi2016_v53beta2_m3dry_col051_row068.csv\n'
        icon_files += f'    setenv MET_CRO_3D_FIN {self.CMAQ_DATA}/{self.appl}/mcip/METCRO3D_{self.start_datetime.strftime("%y%m%d")}.nc\n'
        icon_files += f'    setenv INIT_CONC_1    "$OUTDIR/ICON_$VRSN_{self.appl}_{type}_{self.start_datetime.strftime("%Y%m%d")} -v"\n'
        icon_files += f'endif\n'
        utils.write_to_template(run_icon_path, icon_files, id='%INFILES%')

        ## RUN ICON
        if not setup_only:
            os.system(self.CMD_ICON)
            # Sleep until the run_icon_{self.appl}.log file exists
            while not os.path.exists(f'{self.ICON_SCRIPTS}/run_icon_{self.appl}.log'):
                time.sleep(1)
            # Begin ICON simulation clock
            simstart = datetime.datetime.now()
            if self.verbose:
                print('Starting ICON at: ' + str(simstart))
                sys.stdout.flush()
            icon_sim = self.finish_check('icon')
            while icon_sim != 'complete':
                if icon_sim == 'failed':
                    return False
                else:
                    time.sleep(2)
                    icon_sim = self.finish_check('icon')
            elapsed = datetime.datetime.now() - simstart
            if self.verbose:
                print(f'ICON ran in: {utils.strfdelta(elapsed)}')
        return True

    def run_bcon(self, type='regrid', coarse_grid_name='coarse', cctm_pfx='CCTM_CONC_v53_', setup_only=False):
        """
        Setup and run BCON, which produces boundary conditions for CMAQ.
        """
        ## SETUP BCON
        # Copy the template BCON run script to the scripts directory
        run_bcon_path = f'{self.BCON_SCRIPTS}/run_bcon.csh'
        cmd = self.CMD_CP % (f'{self.DIR_TEMPLATES}/template_run_bcon.csh', run_bcon_path)
        os.system(cmd)

        # Write BCON runtime info to the run script.
        bcon_runtime =  f'#> Source the config_cmaq file to set the run environment\n'
        bcon_runtime += f'source {self.CMAQ_HOME}/config_cmaq.csh {self.compiler} {self.compiler_vrsn}\n'
        bcon_runtime += f'#> Code Version\n'
        bcon_runtime += f'set VRSN     = v532\n'
        bcon_runtime += f'#> Application Name\n'                    
        bcon_runtime += f'set APPL     = {self.appl}\n'
        bcon_runtime += f'#> Boundary condition type [profile|regrid]\n'                     
        bcon_runtime += f'set BCTYPE   = {type}\n'
        bcon_runtime += f'#> check GRIDDESC file for GRID_NAME options\n'                 
        bcon_runtime += f'setenv GRID_NAME {self.grid_name}\n'
        bcon_runtime += f'#> grid description file\n'                    
        bcon_runtime += f'setenv GRIDDESC {self.CMAQ_DATA}/{self.appl}/mcip/GRIDDESC\n'
        bcon_runtime += f'#> GCTP spheroid, use 20 for WRF-based modeling\n' 
        bcon_runtime += f'setenv IOAPI_ISPH 20\n'                     
        bcon_runtime += f'#> turn on excess WRITE3 logging [ options: T | F ]\n'
        bcon_runtime += f'setenv IOAPI_LOG_WRITE F\n'
        bcon_runtime += f'#> support large timestep records (>2GB/timestep record) [ options: YES | NO ]\n'     
        bcon_runtime += f'setenv IOAPI_OFFSET_64 YES\n'
        bcon_runtime += f'#> output file directory\n'   
        bcon_runtime += f'set OUTDIR   = {self.CMAQ_DATA}/{self.appl}/bcon\n'
        bcon_runtime += f'#> define the model execution id\n'
        bcon_runtime += f'setenv EXECUTION_ID $EXEC\n'
        utils.write_to_template(run_bcon_path, bcon_runtime, id='%RUNTIME%')    

        # Write input file info to the run script
        bcon_files =  f'    setenv SDATE           {self.start_datetime.strftime("%Y%j")}\n'
        bcon_files += f'    setenv STIME           {self.start_datetime.strftime("%H%M%S")}\n'
        bcon_files += f'    setenv RUNLEN          {utils.strfdelta(self.delt, fmt="{H:02}{M:02}{S:02}")}\n'   
        
        bcon_files += f' if ( $BCON_TYPE == regrid ) then\n'
        bcon_files += f'     setenv CTM_CONC_1 {self.CMAQ_DATA}/{coarse_grid_name}/cctm/{cctm_pfx}{self.start_datetime.strftime("%Y%m%d")}.nc\n'
        bcon_files += f'     setenv MET_CRO_3D_CRS {self.CMAQ_DATA}/{coarse_grid_name}/mcip/METCRO3D_{self.start_datetime.strftime("%y%m%d")}\n'
        bcon_files += f'     setenv MET_BDY_3D_FIN {self.CMAQ_DATA}/{self.appl}/mcip/METBDY3D_{self.start_datetime.strftime("%y%m%d")}.nc\n'
        bcon_files += f'     setenv BNDY_CONC_1    "$OUTDIR/BCON_$VRSN_{self.appl}_{type}_{self.start_datetime.strftime("%Y%m%d")} -v"\n'
        bcon_files += f' endif\n'
        
        bcon_files += f' if ( $BCON_TYPE == profile ) then\n'
        bcon_files += f'     setenv BC_PROFILE $BLD/avprofile_cb6r3m_ae7_kmtbr_hemi2016_v53beta2_m3dry_col051_row068.csv\n'
        bcon_files += f'     setenv MET_BDY_3D_FIN {self.CMAQ_DATA}/{self.appl}/mcip/METBDY3D_{self.start_datetime.strftime("%y%m%d")}.nc\n'
        bcon_files += f'     setenv BNDY_CONC_1    "$OUTDIR/BCON_$VRSN_{self.appl}_{type}_{self.start_datetime.strftime("%Y%m%d")} -v"\n'
        bcon_files += f' endif\n'
        utils.write_to_template(run_bcon_path, bcon_files, id='%INFILES%')
        
        ## RUN BCON
        if not setup_only:
            os.system(self.CMD_BCON)
            # Sleep until the run_bcon_{self.appl}.log file exists
            while not os.path.exists(f'{self.BCON_SCRIPTS}/run_bcon_{self.appl}.log'):   
                time.sleep(1)
            # Begin BCON simulation clock
            simstart = datetime.datetime.now()
            if self.verbose:
                print('Starting BCON at: ' + str(simstart))
                sys.stdout.flush()
            bcon_sim = self.finish_check('bcon')
            while bcon_sim != 'complete':
                if bcon_sim == 'failed':
                    return False
                else:
                    time.sleep(2)
                    bcon_sim = self.finish_check('bcon')
            elapsed = datetime.datetime.now() - simstart
            if self.verbose:
                print(f'BCON ran in: {utils.strfdelta(elapsed)}')
        return True

    def run_cctm(self, cctm_vrsn='v533', delete_existing_output='TRUE', new_sim='TRUE', tstep='010000', n_procs=16, run_hours=24, setup_only=False):
        """
        Setup and run CCTM, CMAQ's chemical transport model.
        """
        ## SETUP CCTM
        # Copy the template CCTM run script to the scripts directory
        run_cctm_path = f'{self.CCTM_SCRIPTS}/run_cctm.csh'
        cmd = self.CMD_CP % (f'{self.DIR_TEMPLATES}/template_run_cctm.csh', run_cctm_path)
        os.system(cmd)
        # Copy the template CCTM submission script to the scripts directory
        submit_cctm_path = f'{self.CCTM_SCRIPTS}/submit_cctm.csh'
        cmd = self.CMD_CP % (f'{self.DIR_TEMPLATES}/template_submit_cctm.csh', submit_cctm_path)
        os.system(cmd)

        # Write CCTM setup options to the run script
        cctm_runtime =  f'#> Toggle Diagnostic Mode which will print verbose information to standard output\n'
        cctm_runtime += f'setenv CTM_DIAG_LVL 0\n'
        cctm_runtime += f'#> Source the config_cmaq file to set the run environment\n'
        cctm_runtime += f'source {self.CMAQ_HOME}/config_cmaq.csh {self.compiler} {self.compiler_vrsn}\n'
        cctm_runtime += f'#> Change back to the CCTM scripts directory\n'
        cctm_runtime += f'cd {self.CCTM_SCRIPTS}\n'
        cctm_runtime += f'#> Set General Parameters for Configuring the Simulation\n'
        cctm_runtime += f'set VRSN      = {cctm_vrsn}              #> Code Version - note this must be updated if using ISAM or DDM\n'
        cctm_runtime += f'set PROC      = mpi               #> serial or mpi\n'
        cctm_runtime += f'set MECH      = {self.chem_mech}      #> Mechanism ID\n'
        cctm_runtime += f'set APPL      = {self.appl}  #> Application Name (e.g. Gridname)\n'
        cctm_runtime += f'#> Define RUNID as any combination of parameters above or others. By default,\n'
        cctm_runtime += f'#> this information will be collected into this one string, $RUNID, for easy\n'
        cctm_runtime += f'#> referencing in output binaries and log files as well as in other scripts.\n'
        cctm_runtime += f'setenv RUNID  {cctm_vrsn}_{self.compiler}{self.compiler_vrsn}_{self.appl}\n'
        cctm_runtime += f'#> Set Working, Input, and Output Directories\n'
        cctm_runtime += f'setenv WORKDIR {self.CCTM_SCRIPTS}    #> Working Directory. Where the runscript is.\n'
        cctm_runtime += f'setenv OUTDIR  {self.CMAQ_DATA}/{self.appl}/output_CCTM_$RUNID  #> Output Directory\n'
        cctm_runtime += f'setenv INPDIR  {self.CMAQ_DATA}/{self.appl}/input #> Input Directory\n'
        cctm_runtime += f'setenv GRIDDESC $INPDIR/GRIDDESC    #> grid description file\n'
        cctm_runtime += f'setenv GRID_NAME {self.grid_name}         #> check GRIDDESC file for GRID_NAME options\n'
        cctm_runtime += f'#> Keep or Delete Existing Output Files\n'
        cctm_runtime += f'set CLOBBER_DATA = {delete_existing_output}\n'
        utils.write_to_template(run_cctm_path, cctm_runtime, id='%SETUP%')

        # Write CCTM start, end, and timestepping options to the run script
        cctm_time =  f'#> Set Start and End Days for looping\n'
        cctm_time += f'setenv NEW_START {new_sim}        #> Set to FALSE for model restart\n'
        cctm_time += f'set START_DATE = "{self.start_datetime.strftime("%Y-%m-%d")}"     #> beginning date\n'
        cctm_time += f'set END_DATE   = "{self.end_datetime.strftime("%Y-%m-%d")}"     #> ending date\n'
        cctm_time += f'#> Set Timestepping Parameters\n'
        cctm_time += f'set STTIME     = {self.start_datetime.strftime("%H%M%S")}            #> beginning GMT time (HHMMSS)\n'
        cctm_time += f'set NSTEPS     = {utils.strfdelta(self.delt, fmt="{H:02}{M:02}{S:02}")}            #> time duration (HHMMSS) for this run\n'
        cctm_time += f'set TSTEP      = {tstep}            #> output time step interval (HHMMSS)\n'
        utils.write_to_template(run_cctm_path, cctm_time, id='%TIME%')

        # Control domain subsetting among processors -- these will always be closest to a square
        if n_procs == 8:
            cctm_proc = '@ NPCOL  =  2; @ NPROW =  4'
        elif n_procs == 12:
            cctm_proc = '@ NPCOL  =  3; @ NPROW =  4'
        elif n_procs == 16:
            cctm_proc = '@ NPCOL  =  4; @ NPROW =  4'
        elif n_procs == 24:
            cctm_proc = '@ NPCOL  =  4; @ NPROW =  6'
        elif n_procs == 32:
            cctm_proc = '@ NPCOL  =  4; @ NPROW =  8'
        elif n_procs == 48:
            cctm_proc = '@ NPCOL  =  6; @ NPROW =  8'
        else:
            print(f'No {n_procs} processor setup has been specified. Use [8, 12, 16, 24, 32, or 48].')
            raise ValueError
        utils.write_to_template(run_cctm_path, cctm_proc, id='%PROC%')

        # Write CCTM submission script
        cctm_sub =  f'#!/bin/csh\n'
        cctm_sub += f'\n'
        cctm_sub += f'#SBATCH -J cctm_{self.appl}                  # Job name\n'
        # cctm_sub += f'#SBATCH -o {self.CCTM_SCRIPTS}/out.cctm_{self.appl}              # Name of stdout output file\n'
        cctm_sub += f'#SBATCH -o /dev/null              # Name of stdout output file\n'
        # cctm_sub += f'#SBATCH -e {self.CCTM_SCRIPTS}/errors.cctm_{self.appl}           # Name of stderr output file\n'
        cctm_sub += f'#SBATCH -e /dev/null           # Name of stderr output file\n'
        cctm_sub += f'#SBATCH --ntasks={n_procs}             # Total number of tasks to be configured for.\n'
        cctm_sub += f'#SBATCH --tasks-per-node={n_procs}     # sets number of tasks to run on each node.\n'
        cctm_sub += f'#SBATCH --cpus-per-task=1       # sets number of cpus needed by each task (if task is "make -j3" number should be 3).\n'
        cctm_sub += f'#SBATCH --get-user-env          # tells sbatch to retrieve the users login environment. \n'
        cctm_sub += f'#SBATCH -t {run_hours}:00:00             # Run time (hh:mm:ss)\n'
        cctm_sub += f'#SBATCH --mem=20000M            # memory required per node\n'
        cctm_sub += f'#SBATCH --partition=default_cpu # Which queue it should run on.\n'
        cctm_sub += f'\n'
        cctm_sub += f'{self.CCTM_SCRIPTS}/run_cctm.csh >&! {self.CCTM_SCRIPTS}/cctm_{self.appl}.log\n'
        utils.write_to_template(submit_cctm_path, cctm_sub, id='%ALL%')

        if self.verbose:
            print('Done writing CCTM scripts!\n')
        
        ## RUN CCTM
        if not setup_only:
            os.system(self.CMD_CCTM)
            # Sleep until the run_cctm_{self.appl}.log file exists
            while not os.path.exists(f'{self.CCTM_SCRIPTS}/cctm_{self.appl}.log'):
                time.sleep(1)
            # Begin CCTM simulation clock
            simstart = datetime.datetime.now()
            if self.verbose:
                print('Starting CCTM at: ' + str(simstart))
                sys.stdout.flush()
            cctm_sim = self.finish_check('cctm')
            while cctm_sim != 'complete':
                if cctm_sim == 'failed':
                    return False
                else:
                    time.sleep(2)
                    cctm_sim = self.finish_check('cctm')
            elapsed = datetime.datetime.now() - simstart
            if self.verbose:
                print(f'CCTM ran in: {utils.strfdelta(elapsed)}')
                sys.stdout.flush()
        return True

    def finish_check(self, program):
        """
        Check if a specified CMAQ subprogram has finished running.

        :param program: string
            CMAQ subprogram name whose status is to be checked.
        :return: 'running' or 'complete' or 'failed' string
            Run status of the program.

        """
        if program == 'mcip':
            msg = utils.read_last(f'{self.MCIP_SCRIPTS}/run_mcip_{self.appl}.log', n_lines=1)
            complete = 'NORMAL TERMINATION' in msg
            failed = 'Error running mcip' in msg
        elif program == 'icon':
            msg = utils.read_last(f'{self.ICON_SCRIPTS}/run_icon_{self.appl}.log', n_lines=5)
            complete = '>>---->  Program  ICON completed successfully  <----<<' in msg
            # Not sure what the correct failure message should be!
            failed = False
        elif program == 'bcon':
            msg = utils.read_last(f'{self.BCON_SCRIPTS}/run_bcon_{self.appl}.log', n_lines=5)
            complete = '>>---->  Program  BCON completed successfully  <----<<' in msg
            # Not sure what the correct failure message should be!
            # failed = '-------------------------------------------' in msg
        elif program == 'cctm':
            msg = utils.read_last(f'{self.MCIP_SCRIPTS}/run_mcip_{self.appl}.log', n_lines=40)
            complete = '|>---   PROGRAM COMPLETED SUCCESSFULLY   ---<|' in msg
            failed = 'Runscript Detected an Error' in msg
        else:
            complete = False
            failed = False
        if failed:
            print(f'\nCMAQPyError: {program} has failed. Last message was:\n{msg}')
            return 'failed'
        elif complete:
            return 'complete'
        else:
            return 'running'
            