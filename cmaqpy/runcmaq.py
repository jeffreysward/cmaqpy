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

        # Format the forecast start/end and determine the total time.
        self.start_datetime = utils.format_date(start_datetime)
        self.end_datetime = utils.format_date(end_datetime)
        self.delt = self.end_datetime - self.start_datetime
        if self.verbose:
            print(f'Forecast starting on: {self.forecast_start}')
            print(f'Forecast ending on: {self.forecast_end}')

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
        self.CMD_MCIP = f'./run_mcip.csh >&! run_mcip_{self.appl}.log'
        self.CMD_ICON = f'./run_icon.csh >&! run_icon_{self.appl}.log'
        self.CMD_BCON = f'./run_bcon.csh >&! run_bcon_{self.appl}.log'
        self.CMD_CCTM = f'sbatch --requeue submit_cctm.csh'

    def run_mcip(self, metfile_list=[], geo_file='', t_step=60, setup_only=False):
        """
        Setup and run MCIP, which formats meteorological files (e.g. wrfout*.nc) for CMAQ.
        """
        ## SETUP MCIP
        # Copy the template MCIP run script to the scripts directory
        run_mcip_path = f'{self.MCIP_SCRIPTS}/run_micp.csh'
        cmd = self.CMD_CP % (f'{self.DIR_TEMPLATES}/template_run_mcip.csh', run_mcip_path)
        os.system(cmd)

        # Try to open the MCIP run script as readonly,
        # and print an error & exit if you cannot.
        try:
            run_mcip = utils.read_script(run_mcip_path)
        except IOError as e:
            print(f'Problem reading run_micp.csh')
            print(f'\t{e}')

        # Write IO info to the MCIP run script
        mcip_io =  f'source {self.CMAQ_HOME}/config_cmaq.csh {self.compiler} {self.compiler_vrsn}\n'
        mcip_io += f'set APPL       = {self.appl}\n'
        mcip_io += f'set CoordName  = {self.coord_name}\n'
        mcip_io += f'set GridName   = {self.grid_name}\n'
        mcip_io += f'set DataPath   = {self.CMAQ_DATA}\n'
        mcip_io += f'set InMetDir   = {self.InMetDir}\n'
        mcip_io += f'set InGeoDir   = {self.InGeoDir}\n'
        mcip_io += f'set OutDir     = $DataPath/$GridName/mcip\n'
        mcip_io += f'set ProgDir    = $CMAQ_HOME/PREP/mcip/src\n'
        mcip_io += f'set WorkDir    = $OutDir\n'

        with open(run_mcip_path, 'w') as run_script:
            run_script.write(run_mcip.replace('%IO%', mcip_io))

        # Write met info to the MCIP run script
        mcip_met = f'set InMetFiles = ( ' 
        for metfile in metfile_list:
            mcip_met += f'{self.InMetDir}/{metfile} \\n'
        mcip_met += f' )\n'
        mcip_met += f'set IfGeo      = "F"\n'
        mcip_met += f'set InGeoFile  = {self.InGeoDir}/{geo_file}\n'

        with open(run_mcip_path, 'w') as run_script:
            run_script.write(run_mcip.replace('%MET%', mcip_met))

        # Write start/end info to MCIP run script
        mcip_time =  f'set MCIP_START = {self.start_datetime.strftime("%Y-%m-%d_%H:%M:%S.0000")}\n'  # [UTC]
        mcip_time += f'set MCIP_END   = {self.end_datetime.strftime("%Y-%m-%d_%H:%M:%S.0000")}\n'  # [UTC]
        mcip_time += f'set INTVL      = {t_step}\n' # [min]

        with open(run_mcip_path, 'w') as run_script:
            run_script.write(run_mcip.replace('%TIME%', mcip_time))

        if self.verbose:
            print('Done writing MCIP run script!\n')

        ## RUN MCIP
        if not setup_only:
            os.system(self.CMD_MCIP)
            # Sleep until the run_mcip_{self.appl}.log file exists
            while not os.path.exists(f'{self.MCIP_SCRIPTS}/run_mcip_{self.appl}.log'):
                time.sleep(1)
            # Begin MCIP simulation clock
            simstart = datetime.datetime.now()
            if self.verbose:
                print('Starting MCIP at: ' + str(simstart))
                sys.stdout.flush()
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

    def run_icon(self, type='regrid', coarse_grid_name='coarse', cctm_pfx='CCTM_CONC_v53_', setup_only=False):
        """
        Setup and run ICON, which produces initial conditions for CMAQ.
        """
        ## SETUP ICON
        # Copy the template ICON run script to the scripts directory
        run_icon_path = f'{self.ICON_SCRIPTS}/run_icon.csh'
        cmd = self.CMD_CP % (f'{self.DIR_TEMPLATES}/template_run_icon.csh', run_icon_path)
        os.system(cmd)

        # Try to open the ICON run script as readonly,
        # and print an error & exit if you cannot.
        try:
            run_icon = utils.read_script(run_icon_path)
        except IOError as e:
            print(f'Problem reading run_icon.csh')
            print(f'\t{e}')

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

        with open(run_icon_path, 'w') as run_script:
            run_script.write(run_icon.replace('%RUNTIME%', icon_runtime))

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

        with open(run_icon_path, 'w') as run_script:
            run_script.write(run_icon.replace('%INFILES%', icon_files))

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

        # Try to open the BCON run script as readonly,
        # and print an error & exit if you cannot.
        try:
            run_bcon = utils.read_script(run_bcon_path)
        except IOError as e:
            print(f'Problem reading run_bcon.csh')
            print(f'\t{e}')

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

        with open(run_bcon_path, 'w') as run_script:
            run_script.write(run_bcon.replace('%RUNTIME%', bcon_runtime))       

        # Write input file info to the run script
        bcon_files =  f'    setenv SDATE           {self.start_datetime.strftime("%Y%j")}\n'
        bcon_files += f'    setenv STIME           {self.start_datetime.strftime("%H%M%S")}\n'
        bcon_files += f'    setenv RUNLEN          {self.delt.strftime("%H%M%S")}\n'   
        
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

        with open(run_bcon_path, 'w') as run_script:
            run_script.write(run_bcon.replace('%INFILES%', bcon_files))
        
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

    def run_cctm(self, cctm_vrsn='v533', delete_existing_output='TRUE', new_sim='TRUE', tstep='010000', n_procs=16, setup_only=False):
        """
        Setup and run CCTM, CMAQ's chemical transport model.
        """
        ## SETUP CCTM
        # Copy the template CCTM run script to the scripts directory
        run_cctm_path = f'{self.CCTM_SCRIPTS}/run_cctm.csh'
        cmd = self.CMD_CP % (f'{self.DIR_TEMPLATES}/template_run_cctm.csh', run_cctm_path)
        os.system(cmd)

        # Try to open the BCON run script as readonly,
        # and print an error & exit if you cannot.
        try:
            run_cctm = utils.read_script(run_cctm_path)
        except IOError as e:
            print(f'Problem reading run_cctm.csh')
            print(f'\t{e}')

        # Write CCTM setup options to the run script
        cctm_runtime =  f'#> Toggle Diagnostic Mode which will print verbose information to standard output\n'
        cctm_runtime += f'setenv CTM_DIAG_LVL 0\n'
        cctm_runtime += f'#> Source the config_cmaq file to set the run environment\n'
        cctm_runtime += f'source {self.CMAQ_HOME}/config_cmaq.csh {self.compiler} {self.compiler_vrsn}\n'
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
        cctm_runtime += f'setenv OUTDIR  {self.CMAQ_DATA}/output_CCTM_$RUNID  #> Output Directory\n'
        cctm_runtime += f'setenv INPDIR  {self.CMAQ_DATA}/{self.appl} #> Input Directory\n'
        cctm_runtime += f'setenv GRIDDESC $INPDIR/GRIDDESC    #> grid description file\n'
        cctm_runtime += f'setenv GRID_NAME {self.grid_name}         #> check GRIDDESC file for GRID_NAME options\n'
        cctm_runtime += f'#> Keep or Delete Existing Output Files\n'
        cctm_runtime += f'set CLOBBER_DATA = {delete_existing_output}\n' 

        with open(run_cctm_path, 'w') as run_script:
            run_script.write(run_cctm.replace('%SETUP%', cctm_runtime))

        # Write CCTM start, end, and timestepping options to the run script
        cctm_time =  f'#> Set Start and End Days for looping\n'
        cctm_time += f'setenv NEW_START {new_sim}        #> Set to FALSE for model restart\n'
        cctm_time += f'set START_DATE = "{self.start_datetime.strftime("%Y-%m-%d")}"     #> beginning date\n'
        cctm_time += f'set END_DATE   = "{self.end_datetime.strftime("%Y-%m-%d")}"     #> ending date\n'
        cctm_time += f'#> Set Timestepping Parameters\n'
        cctm_time += f'set STTIME     = {self.start_datetime.strftime("%H%M%S")}            #> beginning GMT time (HHMMSS)\n'
        cctm_time += f'set NSTEPS     = {self.delt.strftime("%H%M%S")}            #> time duration (HHMMSS) for this run\n'
        cctm_time += f'set TSTEP      = {tstep}            #> output time step interval (HHMMSS)\n'

        with open(run_cctm_path, 'w') as run_script:
            run_script.write(run_cctm.replace('%TIME%', cctm_time))

        # Control domain subsetting among processors -- these will always be closest to a square
        if n_procs == 8:
            cctm_proc = '@ NPCOL  =  2; @ NPROW =  4'
        elif n_procs == 12:
            cctm_proc = '@ NPCOL  =  3; @ NPROW =  4'
        elif n_procs == 16:
            cctm_proc = '@ NPCOL  =  4; @ NPROW =  4'
        if n_procs == 24:
            cctm_proc = '@ NPCOL  =  4; @ NPROW =  6'
        if n_procs == 32:
            cctm_proc = '@ NPCOL  =  4; @ NPROW =  8'
        if n_procs == 48:
            cctm_proc = '@ NPCOL  =  6; @ NPROW =  8'
        else:
            print(f'No {n_procs} processor setup has been specified. Use [8, 12, 16, 24, 32, or 48].')
            raise ValueError

        with open(run_cctm_path, 'w') as run_script:
            run_script.write(run_cctm.replace('%PROC%', cctm_proc))
        
        ## RUN CCTM
        if not setup_only:
            os.system(self.CMD_CCTM)
            # Sleep until the run_cctm_{self.appl}.log file exists
            while not os.path.exists(f'{self.CCTM_SCRIPTS}/run_cctm_{self.appl}.log'): #!!!!!! THIS IS NOT ACTUALLY THE NAME OF THE LOG FILE
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
            msg = utils.read_last(f'{self.MCIP_SCRIPTS}run_mcip_{self.appl}.log', n_lines=1)
            complete = 'NORMAL TERMINATION' in msg
            # Not sure what the correct failure message should be!
            failed = False
        elif program == 'icon':
            msg = utils.read_last(f'{self.ICON_SCRIPTS}run_icon_{self.appl}.log', n_lines=5)
            complete = '>>---->  Program  ICON completed successfully  <----<<' in msg
            # Not sure what the correct failure message should be!
            failed = False
        elif program == 'bcon':
            msg = utils.read_last(f'{self.BCON_SCRIPTS}run_bcon_{self.appl}.log', n_lines=5)
            complete = '>>---->  Program  BCON completed successfully  <----<<' in msg
            # Not sure what the correct failure message should be!
            # failed = '-------------------------------------------' in msg
        elif program == 'cctm':
            msg = utils.read_last(f'{self.MCIP_SCRIPTS}run_mcip_{self.appl}.log', n_lines=40)
            complete = '|>---   PROGRAM COMPLETED SUCCESSFULLY   ---<|' in msg
            # Not sure what the correct failure message should be!
            # failed = '-------------------------------------------' in msg
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