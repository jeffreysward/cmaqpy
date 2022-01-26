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
    def __init__(self, start_datetime, end_datetime, appl, coord_name, grid_name,setup_yaml='dirpaths.yml', compiler='gcc', compiler_vrsn='9.3.1', verbose=False):
        self.appl = appl
        self.coord_name = coord_name
        self.grid_name = grid_name
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
        self.MCIP_SCRIPTS = f'{self.CMAQ_HOME}PREP/mcip/scripts/'
        self.ICON_SCRIPTS = f'{self.CMAQ_HOME}PREP/icon/scripts/'
        self.BCON_SCRIPTS = f'{self.CMAQ_HOME}PREP/bcon/scripts/'
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

    def run_mcip(self, metfile_list=[], geo_file='', t_step=60):
        """
        Setup and run MCIP.
        """
        ## SETUP MCIP
        # Copy the template MCIP run script to the scripts directory
        run_mcip_path = f'{self.MCIP_SCRIPTS}run_micp.csh'
        cmd = self.CMD_CP % (f'{self.DIR_TEMPLATES}template_run_mcip.csh', run_mcip_path)
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
        mcip_io += f'set APPL       = {self.appl}'
        mcip_io += f'set CoordName  = {self.coord_name}'
        mcip_io += f'set GridName   = {self.grid_name}'
        mcip_io += f'set DataPath   = {self.CMAQ_DATA}'
        mcip_io += f'set InMetDir   = {self.InMetDir}'
        mcip_io += f'set InGeoDir   = {self.InGeoDir}'
        mcip_io += f'set OutDir     = $DataPath/$GridName/mcip'
        mcip_io += f'set ProgDir    = $CMAQ_HOME/PREP/mcip/src'
        mcip_io += f'set WorkDir    = $OutDir'

        with open(run_mcip_path, 'w') as run_script:
            run_script.write(run_mcip.replace('%IO%', mcip_io))

        # Write met info to the MCIP run script
        mcip_met = f'set InMetFiles = ( ' 
        for metfile in metfile_list:
            mcip_met += f'{self.InMetDir}/{metfile} \\n'
        mcip_met += f' )'
        mcip_met += f'set IfGeo      = "F"'
        mcip_met += f'set InGeoFile  = {self.InGeoDir}/{geo_file}'

        with open(run_mcip_path, 'w') as run_script:
            run_script.write(run_mcip.replace('%MET%', mcip_met))

        # Write start/end info to MCIP run script
        mcip_time =  f'set MCIP_START = {self.start_datetime.strftime("%Y-%m-%d_%H:%M:%S.0000")}'  # [UTC]
        mcip_time += f'set MCIP_END   = {self.end_datetime.strftime("%Y-%m-%d_%H:%M:%S.0000")}'  # [UTC]
        mcip_time += f'set INTVL      = {t_step}' # [min]

        with open(run_mcip_path, 'w') as run_script:
            run_script.write(run_mcip.replace('%TIME%', mcip_time))

        if self.verbose:
            print('Done writing MCIP run script!\n')

        ## RUN MCIP
        os.system(self.CMD_MCIP)
        # Sleep until the run_mcip_{self.appl}.log file exists
        while not os.path.exists(f'{self.MCIP_SCRIPTS}/run_mcip_{self.appl}.log'):
            time.sleep(1)
        # Begin geogrid simulation clock
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

    def run_icon(self, type='regrid'):
        # #ICON
        # APPL     = 09NE                    #> Application Name
        # ICTYPE   = profile                  #> Initial conditions type [profile|regrid]
        # #> Horizontal grid definition 
        # setenv GRID_NAME 09NE               #> check GRIDDESC file for GRID_NAME options
        # setenv GRIDDESC $CMAQ_DATA/mcip/$APPL/GRIDDESC #> grid description file 
        # setenv IOAPI_ISPH 20                     #> GCTP spheroid, use 20 for WRF-based modeling

        # #> I/O Controls
        # setenv IOAPI_LOG_WRITE F     #> turn on excess WRITE3 logging [ options: T | F ]
        # setenv IOAPI_OFFSET_64 YES   #> support large timestep records (>2GB/timestep record) [ options: YES | NO ]

        # OUTDIR   = $CMAQ_HOME/data/icon       #> output file directory

        # set DATE = "2018-01-01"
        # set YYYYJJJ  = `date -ud "${DATE}" +%Y%j`   #> Convert YYYY-MM-DD to YYYYJJJ
        # set YYMMDD   = `date -ud "${DATE}" +%y%m%d` #> Convert YYYY-MM-DD to YYMMDD
        # set YYYYMMDD = `date -ud "${DATE}" +%Y%m%d` #> Convert YYYY-MM-DD to YYYYMMDD
        # #   setenv SDATE           ${YYYYJJJ}
        # #   setenv STIME           000000

        # if ( $ICON_TYPE == regrid ) then
        #     setenv CTM_CONC_1 /work/MOD3EVAL/sjr/CCTM_CONC_v53_intel18.0_2016_CONUS_test_${YYYYMMDD}.nc
        #     setenv MET_CRO_3D_CRS /work/MOD3DATA/2016_12US1/met/mcip_v43_wrf_v381_ltng/METCRO3D.12US1.35L.${YYMMDD}
        #     setenv MET_CRO_3D_FIN /work/MOD3DATA/SE53BENCH/met/mcip/METCRO3D_${YYMMDD}.nc
        #     setenv INIT_CONC_1    "$OUTDIR/ICON_${VRSN}_${APPL}_${ICON_TYPE}_${YYYYMMDD} -v"
        # endif

        # if ( $ICON_TYPE == profile ) then
        #     setenv IC_PROFILE $BLD/avprofile_cb6r3m_ae7_kmtbr_hemi2016_v53beta2_m3dry_col051_row068.csv
        #     setenv MET_CRO_3D_FIN $CMAQ_DATA/mcip/$APPL/METCRO3D_${YYMMDD}.nc
        #     setenv INIT_CONC_1    "$OUTDIR/ICON_${VRSN}_${APPL}_${ICON_TYPE}_${YYYYMMDD} -v"
        # endif
        pass

    def run_bcon(self, type='regrid'):
        # #BCON
        # set APPL     = 09NE                     #> Application Name
        # set BCTYPE   = profile                  #> Boundary condition type [profile|regrid]

        # #> Horizontal grid definition 
        # setenv GRID_NAME 09NE                   #> check GRIDDESC file for GRID_NAME options
        # setenv GRIDDESC $CMAQ_DATA/mcip/$APPL/GRIDDESC #> grid description file 
        # setenv IOAPI_ISPH 20                     #> GCTP spheroid, use 20 for WRF-based modeling

        # #> I/O Controls
        # setenv IOAPI_LOG_WRITE F     #> turn on excess WRITE3 logging [ options: T | F ]
        # setenv IOAPI_OFFSET_64 YES   #> support large timestep records (>2GB/timestep record) [ options: YES | NO ]

        # set OUTDIR   = $CMAQ_HOME/data/bcon       #> output file directory

        # set DATE = "2018-01-01"

        # if ( $BCON_TYPE == regrid ) then
        #     setenv CTM_CONC_1 /work/MOD3EVAL/sjr/CCTM_CONC_v53_intel18.0_2016_CONUS_test_${YYYYMMDD}.nc
        #     setenv MET_CRO_3D_CRS /work/MOD3DATA/2016_12US1/met/mcip_v43_wrf_v381_ltng/METCRO3D.12US1.35L.${YYMMDD}
        #     setenv MET_BDY_3D_FIN /work/MOD3DATA/SE53BENCH/met/mcip/METBDY3D_${YYMMDD}.nc
        #     setenv BNDY_CONC_1    "$OUTDIR/BCON_${VRSN}_${APPL}_${BCON_TYPE}_${YYYYMMDD} -v"
        # endif

        # if ( $BCON_TYPE == profile ) then
        #     setenv BC_PROFILE $BLD/avprofile_cb6r3m_ae7_kmtbr_hemi2016_v53beta2_m3dry_col051_row068.csv
        #     setenv MET_BDY_3D_FIN $CMAQ_DATA/mcip/$APPL/METBDY3D_${YYMMDD}.nc
        #     setenv BNDY_CONC_1    "$OUTDIR/BCON_${VRSN}_${APPL}_${BCON_TYPE}_${YYYYMMDD} -v"
        # endif
        pass

    def run_cctm(self, ):
        pass

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