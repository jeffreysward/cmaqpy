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
    def __init__(self, start_datetime, end_datetime, appl, coord_name, grid_name, chem_mech ='cb6r3_ae7_aq', cctm_vrsn='v533', setup_yaml='dirpaths.yml', compiler='gcc', compiler_vrsn='9.3.1', new_mcip=True, verbose=False):
        self.appl = appl
        self.coord_name = coord_name
        self.grid_name = grid_name
        self.chem_mech = chem_mech
        self.cctm_vrsn = cctm_vrsn
        self.compiler = compiler
        self.compiler_vrsn = compiler_vrsn
        self.verbose = verbose
        self.cctm_runid = f'{self.cctm_vrsn}_{self.compiler}{self.compiler_vrsn}_{self.appl}'
        if self.verbose:
            print(f'Application name: {self.appl}\nCoordinate name: {self.coord_name}\nGrid name: {self.grid_name}')
            print(f'CCTM RUNID: {self.cctm_runid}')

        # Format the forecast start/end and determine the total time.
        self.start_datetime = utils.format_date(start_datetime)
        self.end_datetime = utils.format_date(end_datetime)
        self.delt = self.end_datetime - self.start_datetime
        if self.verbose:
            print(f'CMAQ run starting on: {self.start_datetime}')
            print(f'CMAQ run ending on: {self.end_datetime}')

        # Define the domain windowing paramters for MCIP
        if self.grid_name == '12OTC2':
            self.mcip_btrim = -1
            self.mcip_x0 = 141
            self.mcip_y0 = 15
            self.mcip_ncols = 273
            self.mcip_nrows = 246  
        elif self.grid_name == '4OTC2':
            self.mcip_btrim = -1
            self.mcip_x0 = 87
            self.mcip_y0 = 9
            self.mcip_ncols = 126
            self.mcip_nrows = 156
        else:
            # This will use the entire WRF domain
            self.mcip_btrim = 0
            self.mcip_x0 = 0
            self.mcip_y0 = 0
            self.mcip_ncols = 0
            self.mcip_nrows = 0

        # Set working and WRF model directory names
        dirs = fetch_yaml(setup_yaml)
        dirpaths = dirs.get('directory_paths')
        filepaths = dirs.get('file_paths')
        self.CMAQ_HOME = dirpaths.get('CMAQ_HOME')
        self.MCIP_SCRIPTS = f'{self.CMAQ_HOME}/PREP/mcip/scripts'
        self.ICON_SCRIPTS = f'{self.CMAQ_HOME}/PREP/icon/scripts'
        self.BCON_SCRIPTS = f'{self.CMAQ_HOME}/PREP/bcon/scripts'
        self.CCTM_SCRIPTS = f'{self.CMAQ_HOME}/CCTM/scripts'
        self.CMAQ_DATA = dirpaths.get('CMAQ_DATA')
        if new_mcip:
            self.MCIP_OUT = f'{self.CMAQ_DATA}/{self.appl}/mcip'
        else:
            self.MCIP_OUT = dirpaths.get('LOC_MCIP')
        self.CCTM_INPDIR = f'{self.CMAQ_DATA}/{self.appl}/input'
        self.CCTM_OUTDIR = f'{self.CMAQ_DATA}/{self.appl}/output_CCTM_{self.cctm_runid}'
        self.ICBC = f'{self.CCTM_INPDIR}/icbc'
        self.CCTM_GRIDDED = f'{self.CCTM_INPDIR}/emis/gridded_area/gridded'
        self.CCTM_RWC = f'{self.CCTM_INPDIR}/emis/gridded_area/rwc'
        self.CCTM_PT = f'{self.CCTM_INPDIR}/emis/inln_point'
        self.CCTM_LAND = f'{self.CCTM_INPDIR}/land'
        self.LOC_IC = dirpaths.get('LOC_IC')
        self.LOC_BC = dirpaths.get('LOC_BC')
        self.LOC_GRIDDED = dirpaths.get('LOC_GRIDDED')
        self.LOC_RWC = dirpaths.get('LOC_RWC')
        self.LOC_IN_PT = dirpaths.get('LOC_IN_PT')
        self.LOC_ERTAC = dirpaths.get('LOC_ERTAC')
        self.LOC_LAND = dirpaths.get('LOC_LAND')
        self.DIR_TEMPLATES = dirpaths.get('DIR_TEMPLATES')
        self.InMetDir = dirpaths.get('InMetDir')
        self.InGeoDir = dirpaths.get('InGeoDir')

        # Define the locations for CMAQ inputs
        self.GRIDDESC = filepaths.get('GRIDDESC')

        # Define the names of the CMAQ output files
        #### Maybe use this in the future

        # Define linux command aliai
        self.CMD_LN = 'ln -sf %s %s'
        self.CMD_CP = 'cp %s %s'
        self.CMD_MV = 'mv %s %s'
        self.CMD_RM = 'rm %s'
        self.CMD_GUNZIP = 'gunzip %s'
        self.CMD_ICON = f'{self.ICON_SCRIPTS}/run_icon.csh >& {self.MCIP_SCRIPTS}/run_icon_{self.appl}.log'
        self.CMD_BCON = f'{self.BCON_SCRIPTS}/run_bcon.csh >& {self.MCIP_SCRIPTS}/run_bcon_{self.appl}.log'
        self.CMD_CCTM = f'sbatch --requeue {self.CCTM_SCRIPTS}/submit_cctm.csh'

    def run_mcip(self, mcip_start_datetime=None, mcip_end_datetime=None, metfile_list=[], geo_file='geo_em.d01.nc', t_step=60, run_hours=4, setup_only=False):
        """
        Setup and run MCIP, which formats meteorological files (e.g. wrfout*.nc) for CMAQ.
        """
        ## SETUP MCIP
        if mcip_start_datetime is None:
            mcip_start_datetime = self.start_datetime
        if mcip_end_datetime is None:
            mcip_end_datetime = self.end_datetime
        # Set an 'MCIP APPL,' which will control file names
        mcip_sdatestr = mcip_start_datetime.strftime("%y%m%d")
        self.mcip_appl = f'{self.appl}_{mcip_sdatestr}'
        # Remove existing log file
        cmd = self.CMD_RM % (f'{self.MCIP_SCRIPTS}/run_mcip_{self.mcip_appl}.log')
        os.system(cmd)
        
        # Copy the template MCIP run script to the scripts directory
        run_mcip_path = f'{self.MCIP_SCRIPTS}/run_mcip_{self.mcip_appl}.csh'
        cmd = self.CMD_CP % (f'{self.DIR_TEMPLATES}/template_run_mcip.csh', run_mcip_path)
        os.system(cmd)

        # Write Slurm info
        mcip_slurm =  f'#SBATCH -J mcip_{self.appl}		# Job name\n'
        mcip_slurm += f'#SBATCH -o {self.MCIP_SCRIPTS}/run_mcip_{self.mcip_appl}.log\n'
        mcip_slurm += f'#SBATCH --nodes=1		# Total number of nodes requested\n' 
        mcip_slurm += f'#SBATCH --ntasks=1		# Total number of tasks to be configured for.\n' 
        mcip_slurm += f'#SBATCH --tasks-per-node=1	# sets number of tasks to run on each node.\n' 
        mcip_slurm += f'#SBATCH --cpus-per-task=1	# sets number of cpus needed by each task.\n'
        mcip_slurm += f'#SBATCH --get-user-env		# tells sbatch to retrieve the users login environment.\n' 
        mcip_slurm += f'#SBATCH -t {run_hours}:00:00		# Run time (hh:mm:ss)\n' 
        mcip_slurm += f'#SBATCH --mem=20000M		# memory required per node\n'
        mcip_slurm += f'#SBATCH --partition=default_cpu	# Which queue it should run on.\n'
        utils.write_to_template(run_mcip_path, mcip_slurm, id='%SLURM%') 

        # Write IO info to the MCIP run script
        mcip_io =  f'source {self.CMAQ_HOME}/config_cmaq.csh {self.compiler} {self.compiler_vrsn}\n'
        mcip_io += f'set APPL       = {mcip_sdatestr}\n'
        mcip_io += f'set CoordName  = {self.coord_name}\n'
        mcip_io += f'set GridName   = {self.grid_name}\n'
        mcip_io += f'set DataPath   = {self.CMAQ_DATA}\n'
        mcip_io += f'set InMetDir   = {self.InMetDir}\n'
        mcip_io += f'set InGeoDir   = {self.InGeoDir}\n'
        mcip_io += f'set OutDir     = {self.MCIP_OUT}\n'
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
        mcip_time =  f'set MCIP_START = {mcip_start_datetime.strftime("%Y-%m-%d_%H:%M:%S.0000")}\n'  # [UTC]
        mcip_time += f'set MCIP_END   = {mcip_end_datetime.strftime("%Y-%m-%d_%H:%M:%S.0000")}\n'  # [UTC]
        mcip_time += f'set INTVL      = {t_step}\n' # [min]
        utils.write_to_template(run_mcip_path, mcip_time, id='%TIME%')

        # Write domain windowing parameters to MCIP run script
        mcip_domain  = f'set BTRIM = {self.mcip_btrim}\n'
        mcip_domain += f'set X0    =  {self.mcip_x0}\n'
        mcip_domain += f'set Y0    =  {self.mcip_y0}\n'
        mcip_domain += f'set NCOLS =  {self.mcip_ncols}\n'
        mcip_domain += f'set NROWS =  {self.mcip_nrows}\n'
        utils.write_to_template(run_mcip_path, mcip_domain, id='%DOMAIN%')

        if self.verbose:
            print('Wrote MCIP run script to\n{run_mcip_path}')

        ## RUN MCIP
        if not setup_only:
            # Begin MCIP simulation clock
            simstart = datetime.datetime.now()
            if self.verbose:
                print('Starting MCIP at: ' + str(simstart))
                # sys.stdout.flush()
            os.system(f'sbatch --requeue {self.MCIP_SCRIPTS}/run_mcip_{self.mcip_appl}.csh')
            # Sleep until the run_mcip_{self.appl}.log file exists
            while not os.path.exists(f'{self.MCIP_SCRIPTS}/run_mcip_{self.mcip_appl}.log'):
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
                print(f'MCIP ran in: {utils.strfdelta(elapsed)}\n')
        return True

    def run_mcip_multiday(self, metfile_dir=None, metfile_list=[], geo_file='geo_em.d01.nc', t_step=60):
        """
        Run MCIP over multiple days. Per CMAQ convention, daily MCIP files contain
        25 hours each all the hours from the current day, and the first hour (00:00)
        from the following day. 
        """
        # Loop over each day
        for day_no in range(self.delt.days):
            success = False
            # Set the start datetime, end datetime, and metfile list for the day
            mcip_start_datetime = self.start_datetime + datetime.timedelta(day_no)
            mcip_end_datetime = self.start_datetime + datetime.timedelta(day_no + 1)
            if self.verbose:
                print(f'Working on MCIP for {mcip_start_datetime}')
            if metfile_dir is None:
                # If all the met data is stored in the same file, pass that file in 
                # using metfile_list and set metfile_dir=None
                metfile_list = metfile_list
            else:
                # Eventually, can add scripting here that assumes there's a different
                # wrfout file produced every day and they are all located in metfile_dir.
                pass

            # run mcip for that day
            self.run_mcip(mcip_start_datetime=mcip_start_datetime, mcip_end_datetime=mcip_end_datetime, metfile_list=metfile_list, geo_file=geo_file, t_step=t_step, setup_only=False) 
        

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

    def setup_inpdir(self):
        """
        Links all the necessary files to the locations in INPDIR where CCTM expects to find them. 
        """
        # Remove the existing input directory if it already exists and remake it
        utils.remove_dir(self.CCTM_INPDIR)
        utils.make_dirs(self.CCTM_INPDIR)

        # Make a list of the start dates for date-specific inputs
        start_datetimes_lst = [single_date for single_date in (self.start_datetime + datetime.timedelta(n) for n in range(self.delt.days))]

        # Link the GRIDDESC to $INPDIR
        cmd = self.CMD_LN % (self.GRIDDESC, f'{self.CCTM_INPDIR}/')
        cmd_gunzip = self.CMD_GUNZIP % (self.GRIDDESC)

        # Link Boundary Conditions to $INPDIR/icbc
        utils.make_dirs(self.ICBC)
        for date in start_datetimes_lst:
            local_bc_file = f'{self.LOC_BC}/*{date.strftime("%y%m%d")}'
            cmd = cmd + '; ' + self.CMD_LN % (local_bc_file, f'{self.ICBC}/')
            cmd_gunzip = cmd_gunzip + '; ' +  self.CMD_GUNZIP % (local_bc_file)
        
        # Link Initial Conditions to self.CCTM_OUTDIR
        utils.make_dirs(self.CCTM_OUTDIR)
        yesterday = start_datetimes_lst[0] - datetime.timedelta(days=1)
        local_ic_file = f'{self.LOC_IC}/CCTM_CGRID_*{yesterday.strftime("%Y%m%d")}.nc'
        cmd = cmd + '; ' + self.CMD_LN % (local_ic_file, f'{self.CCTM_OUTDIR}/CCTM_CGRID_{self.cctm_runid}_{yesterday.strftime("%Y%m%d")}.nc')
        local_init_medc_1_file = f'{self.LOC_IC}/CCTM_MEDIA_CONC_*{yesterday.strftime("%y%m%d")}.nc'
        cmd = cmd + '; ' + self.CMD_LN % (local_init_medc_1_file, f'{self.CCTM_OUTDIR}/CCTM_MEDIA_CONC_{self.cctm_runid}_{yesterday.strftime("%Y%m%d")}.nc')

        # Link gridded emissions to $INPDIR/emis/gridded_area/gridded
        utils.make_dirs(self.CCTM_GRIDDED)
        for date in start_datetimes_lst:
            local_gridded_file = f'{self.LOC_GRIDDED}/emis_mole_all_20*{date.strftime("%y%m%d")}*'
            cmd = cmd + '; ' + self.CMD_LN % (local_gridded_file, f'{self.CCTM_GRIDDED}/')
            cmd_gunzip = cmd_gunzip + '; ' +  self.CMD_GUNZIP % (local_gridded_file)

        # Link residential wood combustion to $INPDIR/emis/gridded_area/rwc
        utils.make_dirs(self.CCTM_RWC)
        for date in start_datetimes_lst:
            local_rwc_file = f'{self.LOC_RWC}/emis_mole_rwc_20*{date.strftime("%y%m%d")}*'
            cmd = cmd + '; ' + self.CMD_LN % (local_rwc_file, f'{self.CCTM_RWC}/')
            cmd_gunzip = cmd_gunzip + '; ' +  self.CMD_GUNZIP % (local_rwc_file)

        # Link point source emissions to $INPDIR/emis/inln_point 
        # and the associated stack groups to $INPDIR/emis/inln_point/stack_groups
        utils.make_dirs(f'{self.CCTM_PT}/stack_groups')
        # Link the ptnonertac sector
        for date in start_datetimes_lst:
            local_ptnonertac_file = f'{self.LOC_IN_PT}/ptnonertac_hourly/inln_mole_ptnonertac_20*{date.strftime("%y%m%d")}*'
            cmd = cmd + '; ' + self.CMD_LN % (local_ptnonertac_file, f'{self.CCTM_PT}/')
            cmd_gunzip = cmd_gunzip + '; ' +  self.CMD_GUNZIP % (local_ptnonertac_file)
        local_ptnonertac_stk_file = f'{self.LOC_IN_PT}/ptnonertac_hourly/stack_groups_ptnonertac_*'
        cmd = cmd + '; ' + self.CMD_LN % (local_ptnonertac_stk_file, f'{self.CCTM_PT}/stack_groups/')
        cmd_gunzip = cmd_gunzip + '; ' +  self.CMD_GUNZIP % (local_ptnonertac_stk_file)
        # Link the ptertac sector
        for date in start_datetimes_lst:
            local_ptertac_file = f'{self.LOC_ERTAC}/inln_mole_ptertac_smkfix_20*{date.strftime("%y%m%d")}*'
            cmd = cmd + '; ' + self.CMD_LN % (local_ptertac_file, f'{self.CCTM_PT}/')
            cmd_gunzip = cmd_gunzip + '; ' +  self.CMD_GUNZIP % (local_ptertac_file)
        local_ptertac_stk_file = f'{self.LOC_ERTAC}/stack_groups_ptertac_*'
        cmd = cmd + '; ' + self.CMD_LN % (local_ptertac_stk_file, f'{self.CCTM_PT}/stack_groups/')
        cmd_gunzip = cmd_gunzip + '; ' +  self.CMD_GUNZIP % (local_ptertac_stk_file)
        # Link the othpt sector
        for date in start_datetimes_lst:
            local_othpt_file = f'{self.LOC_IN_PT}/othpt/inln_mole_othpt_20*{date.strftime("%y%m%d")}*'
            cmd = cmd + '; ' + self.CMD_LN % (local_othpt_file, f'{self.CCTM_PT}/')
            cmd_gunzip = cmd_gunzip + '; ' +  self.CMD_GUNZIP % (local_othpt_file)
        local_othpt_stk_file = f'{self.LOC_IN_PT}/othpt/stack_groups_othpt_*'
        cmd = cmd + '; ' + self.CMD_LN % (local_othpt_stk_file, f'{self.CCTM_PT}/stack_groups/')
        cmd_gunzip = cmd_gunzip + '; ' +  self.CMD_GUNZIP % (local_othpt_stk_file)
        # Link the ptagfire sector
        for date in start_datetimes_lst:
            local_ptagfire_file = f'{self.LOC_IN_PT}/ptagfire/inln_mole_ptagfire_20*{date.strftime("%y%m%d")}*'
            cmd = cmd + '; ' + self.CMD_LN % (local_ptagfire_file, f'{self.CCTM_PT}/')
            cmd_gunzip = cmd_gunzip + '; ' +  self.CMD_GUNZIP % (local_ptagfire_file)
            local_ptagfire_stk_file = f'{self.LOC_IN_PT}/ptagfire/stack_groups_ptagfire_20*{date.strftime("%y%m%d")}*'
            cmd = cmd + '; ' + self.CMD_LN % (local_ptagfire_stk_file, f'{self.CCTM_PT}/stack_groups/')
            cmd_gunzip = cmd_gunzip + '; ' +  self.CMD_GUNZIP % (local_ptagfire_stk_file)
        # Link the ptfire sector
        for date in start_datetimes_lst:
            local_ptfire_file = f'{self.LOC_IN_PT}/ptfire/inln_mole_ptfire_20*{date.strftime("%y%m%d")}*'
            cmd = cmd + '; ' + self.CMD_LN % (local_ptfire_file, f'{self.CCTM_PT}/')
            cmd_gunzip = cmd_gunzip + '; ' +  self.CMD_GUNZIP % (local_ptfire_file)
            local_ptfire_stk_file = f'{self.LOC_IN_PT}/ptfire/stack_groups_ptfire_20*{date.strftime("%y%m%d")}*'
            cmd = cmd + '; ' + self.CMD_LN % (local_ptfire_stk_file, f'{self.CCTM_PT}/stack_groups/')
            cmd_gunzip = cmd_gunzip + '; ' +  self.CMD_GUNZIP % (local_ptfire_stk_file)
        # Link the ptfire_othna sector
        for date in start_datetimes_lst:
            local_ptfire_othna_file = f'{self.LOC_IN_PT}/ptfire_othna/inln_mole_ptfire_othna_20*{date.strftime("%y%m%d")}*'
            cmd = cmd + '; ' + self.CMD_LN % (local_ptfire_othna_file, f'{self.CCTM_PT}/')
            cmd_gunzip = cmd_gunzip + '; ' +  self.CMD_GUNZIP % (local_ptfire_othna_file)
            local_ptfire_othna_stk_file = f'{self.LOC_IN_PT}/ptfire_othna/stack_groups_ptfire_othna_20*{date.strftime("%y%m%d")}*'
            cmd = cmd + '; ' + self.CMD_LN % (local_ptfire_othna_stk_file, f'{self.CCTM_PT}/stack_groups/')
            cmd_gunzip = cmd_gunzip + '; ' +  self.CMD_GUNZIP % (local_ptfire_othna_stk_file)
        # Link the pt_oilgas sector
        for date in start_datetimes_lst:
            local_pt_oilgas_file = f'{self.LOC_IN_PT}/pt_oilgas/inln_mole_pt_oilgas_20*{date.strftime("%y%m%d")}*'
            cmd = cmd + '; ' + self.CMD_LN % (local_pt_oilgas_file, f'{self.CCTM_PT}/')
            cmd_gunzip = cmd_gunzip + '; ' +  self.CMD_GUNZIP % (local_pt_oilgas_file)
        local_pt_oilgas_stk_file = f'{self.LOC_IN_PT}/pt_oilgas/stack_groups_pt_oilgas_*'
        cmd = cmd + '; ' + self.CMD_LN % (local_pt_oilgas_stk_file, f'{self.CCTM_PT}/stack_groups/')
        cmd_gunzip = cmd_gunzip + '; ' +  self.CMD_GUNZIP % (local_pt_oilgas_stk_file)
        # Link the cmv_c3_12 sector
        for date in start_datetimes_lst:
            local_cmv_c3_12_file = f'{self.LOC_IN_PT}/cmv_c3_12/inln_mole_cmv_c3_12_20*{date.strftime("%y%m%d")}*'
            cmd = cmd + '; ' + self.CMD_LN % (local_cmv_c3_12_file, f'{self.CCTM_PT}/')
            cmd_gunzip = cmd_gunzip + '; ' +  self.CMD_GUNZIP % (local_cmv_c3_12_file)
        local_cmv_c3_12_stk_file = f'{self.LOC_IN_PT}/cmv_c3_12/stack_groups_cmv_c3_12_*'
        cmd = cmd + '; ' + self.CMD_LN % (local_cmv_c3_12_stk_file, f'{self.CCTM_PT}/stack_groups/')
        cmd_gunzip = cmd_gunzip + '; ' +  self.CMD_GUNZIP % (local_cmv_c3_12_stk_file)
        # Link the cmv_c1c2_12 sector
        for date in start_datetimes_lst:
            lcoal_cmv_c1c2_12_file = f'{self.LOC_IN_PT}/cmv_c1c2_12/inln_mole_cmv_c1c2_12_20*{date.strftime("%y%m%d")}*'
            cmd = cmd + '; ' + self.CMD_LN % (lcoal_cmv_c1c2_12_file, f'{self.CCTM_PT}/')
            cmd_gunzip = cmd_gunzip + '; ' +  self.CMD_GUNZIP % (lcoal_cmv_c1c2_12_file)
        lcoal_cmv_c1c2_12_stk_file = f'{self.LOC_IN_PT}/cmv_c1c2_12/stack_groups_cmv_c1c2_12_*'
        cmd = cmd + '; ' + self.CMD_LN % (lcoal_cmv_c1c2_12_stk_file, f'{self.CCTM_PT}/stack_groups/')
        cmd_gunzip = cmd_gunzip + '; ' +  self.CMD_GUNZIP % (lcoal_cmv_c1c2_12_stk_file)

        # Link files for emissions scaling and sea spray to $INPDIR/land
        utils.make_dirs(f'{self.CCTM_LAND}/toCMAQ_festc1.4_epic')
        for date in start_datetimes_lst:
            local_festc_file = f'{self.LOC_LAND}/toCMAQ_festc1.4_epic/us1_2016_cmaq12km_time20*{date.strftime("%y%m%d")}*'
            cmd = cmd + '; ' + self.CMD_LN % (local_festc_file, f'{self.CCTM_LAND}/toCMAQ_festc1.4_epic/')
            cmd_gunzip = cmd_gunzip + '; ' +  self.CMD_GUNZIP % (local_festc_file)
        cmd = cmd + '; ' + self.CMD_LN % (f'{self.LOC_LAND}/12US1_surf.12otc2.ncf', f'{self.CCTM_LAND}/')
        cmd = cmd + '; ' + self.CMD_LN % (f'{self.LOC_LAND}/beld41_feb2017_waterfix_envcan_12US2.12OTC2.ncf', f'{self.CCTM_LAND}/')
        
        # Run the gunzip commands
        os.system(cmd_gunzip)
        
        # Run the link commands
        os.system(cmd)
        
    
    def run_cctm(self, delete_existing_output='TRUE', new_sim='FALSE', tstep='010000', cctm_hours=24, n_procs=16, run_hours=24, setup_only=False):
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
        # Setup the input directory using the setup_inpdir method
        self.setup_inpdir()

        # Write CCTM setup options to the run script
        cctm_runtime =  f'#> Toggle Diagnostic Mode which will print verbose information to standard output\n'
        cctm_runtime += f'setenv CTM_DIAG_LVL 0\n'
        cctm_runtime += f'#> Source the config_cmaq file to set the run environment\n'
        cctm_runtime += f'source {self.CMAQ_HOME}/config_cmaq.csh {self.compiler} {self.compiler_vrsn}\n'
        cctm_runtime += f'#> Change back to the CCTM scripts directory\n'
        cctm_runtime += f'cd {self.CCTM_SCRIPTS}\n'
        cctm_runtime += f'#> Set General Parameters for Configuring the Simulation\n'
        cctm_runtime += f'set VRSN      = {self.cctm_vrsn}              #> Code Version - note this must be updated if using ISAM or DDM\n'
        cctm_runtime += f'set PROC      = mpi               #> serial or mpi\n'
        cctm_runtime += f'set MECH      = {self.chem_mech}      #> Mechanism ID\n'
        cctm_runtime += f'set APPL      = {self.appl}  #> Application Name (e.g. Gridname)\n\n'
        cctm_runtime += f'#> Define RUNID as any combination of parameters above or others. By default,\n'
        cctm_runtime += f'#> this information will be collected into this one string, $RUNID, for easy\n'
        cctm_runtime += f'#> referencing in output binaries and log files as well as in other scripts.\n'
        cctm_runtime += f'setenv RUNID  {self.cctm_runid}\n\n'
        cctm_runtime += f'#> Set Working, Input, and Output Directories\n'
        cctm_runtime += f'setenv WORKDIR {self.CCTM_SCRIPTS}    #> Working Directory. Where the runscript is.\n'
        cctm_runtime += f'setenv OUTDIR  {self.CCTM_OUTDIR}  #> Output Directory\n'
        cctm_runtime += f'setenv INPDIR  {self.CCTM_INPDIR} #> Input Directory\n'
        cctm_runtime += f'setenv GRIDDESC {self.GRIDDESC}    #> grid description file\n'
        cctm_runtime += f'setenv GRID_NAME {self.grid_name}         #> check GRIDDESC file for GRID_NAME options\n\n'
        cctm_runtime += f'#> Keep or Delete Existing Output Files\n'
        cctm_runtime += f'set CLOBBER_DATA = {delete_existing_output}\n'
        utils.write_to_template(run_cctm_path, cctm_runtime, id='%SETUP%')

        # Write CCTM start, end, and timestepping options to the run script
        cctm_time =  f'#> Set Start and End Days for looping\n'
        cctm_time += f'setenv NEW_START {new_sim}        #> Set to FALSE for model restart\n'
        cctm_time += f'set START_DATE = "{self.start_datetime.strftime("%Y-%m-%d")}"     #> beginning date\n'
        cctm_time += f'set END_DATE   = "{self.end_datetime.strftime("%Y-%m-%d")}"     #> ending date\n\n'
        cctm_time += f'#> Set Timestepping Parameters\n'
        cctm_time += f'set STTIME     = {self.start_datetime.strftime("%H%M%S")}            #> beginning GMT time (HHMMSS)\n'
        cctm_time += f'set NSTEPS     = {cctm_hours}0000            #> time duration (HHMMSS) for this run\n'
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

        # Write CCTM input input directory information
        cctm_files  = f'set ICpath    = {self.ICBC}                        #> initial conditions input directory\n' 
        cctm_files += f'set BCpath    = {self.ICBC}                        #> boundary conditions input directory\n'
        cctm_files += f'set EMISpath  = {self.CCTM_GRIDDED}   #> gridded emissions input directory\n'
        cctm_files += f'set EMISpath2 = {self.CCTM_RWC}       #> gridded surface residential wood combustion emissions directory\n'
        cctm_files += f'set IN_PTpath = {self.CCTM_PT}             #> point source emissions input directory\n'
        cctm_files += f'set IN_LTpath = $INPDIR/lightning                   #> lightning NOx input directory\n'
        cctm_files += f'set METpath   = {self.MCIP_OUT}                #> meteorology input directory\n' 
        cctm_files += f'#set JVALpath  = $INPDIR/jproc                      #> offline photolysis rate table directory\n'
        cctm_files += f'set OMIpath   = $BLD                                #> ozone column data for the photolysis model\n'
        cctm_files += f'set LUpath    = {self.CCTM_LAND}                        #> BELD landuse data for windblown dust model\n'
        cctm_files += f'set SZpath    = {self.CCTM_LAND}                        #> surf zone file for in-line seaspray emissions\n'
        utils.write_to_template(run_cctm_path, cctm_files, id='%FILES%')

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
            msg = utils.read_last(f'{self.MCIP_SCRIPTS}/run_mcip_{self.mcip_appl}.log', n_lines=1)
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
            msg = utils.read_last(f'{self.CCTM_SCRIPTS}/cctm_{self.appl}.log', n_lines=40)
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
            