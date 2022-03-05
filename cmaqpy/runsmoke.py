"""
A Class for processing EGU emissions using SMOKE.
"""
import datetime
import os
import sys
import time
from . import utils
from .data.fetch_data import fetch_yaml


class SMOKEModel():
    """
    This Class provides a framework for running the ptegu/ptertac sectors in SMOKE.
    """
    def __init__(self, appl, sector='ptertac', run_months=[8], emisinv_a='ff10_future.csv', emisinv_b='2016fh_proj_from_egunoncems_2016version1_ERTAC_Platform_POINT_calcyear2014_27oct2019.csv', emisinv_c='egunoncems_2016version1_ERTAC_Platform_POINT_27oct2019.csv', emishour_a='ff10_hourly_future.csv', setup_yaml='dirpaths.yml', compiler='gcc', compiler_vrsn='9.3.1', verbose=False):
        self.appl = appl
        self.sector = sector
        self.run_months = run_months
        self.emisinv_a = emisinv_a
        self.emisinv_b = emisinv_b
        self.emisinv_c = emisinv_c
        self.emishour_a = emishour_a
        self.compiler = compiler
        self.compiler_vrsn = compiler_vrsn
        self.verbose = verbose
        if self.verbose:
            print(f'Application: {self.appl}; Processing {self.sector} for months {self.run_months}')

        # Set model directory names
        dirs = fetch_yaml(setup_yaml)
        dirpaths = dirs.get('directory_paths')
        self.NEI_CASE = dirpaths.get('NEI_CASE')
        self.NEI_CASESCRIPTS = f'{self.NEI_CASE}/scripts/point'
        self.NEI_CASEINPUTS = f'{self.NEI_CASE}/inputs'
        self.CMAQ_DATA = dirpaths.get('CMAQ_DATA')

        # Define linux command aliai
        self.CMD_LN = 'ln -sf %s %s'
        self.CMD_CP = 'cp %s %s'
        self.CMD_MV = 'mv %s %s'
        self.CMD_RM = 'rm %s'

    def run_onetime(self, setup_only=False):
        """
        Run the onetime step for a point sector.
        """
        # Copy the template onetime run script to the scripts directory
        run_onetime_path = f'{self.NEI_CASESCRIPTS}/Annual_{self.sector}_onetime_{self.case_name}.csh'
        cmd = self.CMD_CP % (f'{self.DIR_TEMPLATES}/template_Annual_ptertac_onetime.csh', run_onetime_path)
        os.system(cmd)

        # Write GRIDDESC info
        grid_info = f'setenv GRIDDESC {self.CMAQ_DATA}/{self.appl}/mcip/GRIDDESC'
        utils.write_to_template(run_onetime_path, grid_info, id='%GRID%')

        # Write emissions file info
        emis_files  = f'setenv EMISINV_A {self.NEI_CASEINPUTS}/{self.sector}/{self.emisinv_a}'
        emis_files += f'setenv EMISINV_B {self.NEI_CASEINPUTS}/{self.sector}/{self.emisinv_b}'
        emis_files += f'setenv EMISINV_C {self.NEI_CASEINPUTS}/{self.sector}/{self.emisinv_c}'
        emis_files += f'setenv EMISHOUR_A {self.NEI_CASEINPUTS}/{self.sector}/{self.emishour_a}'
        utils.write_to_template(run_onetime_path, emis_files, id='%EMIS%')

        # Submit the onetime script to the scheduler
        if not setup_only:
            os.system(f'sbatch {run_onetime_path}')
        return

    def run_daily(self, season='summer', setup_only=False):
        """
        Run the onetime step for a point sector.
        """
        # Copy the template onetime run script to the scripts directory
        run_daily_path = f'{self.NEI_CASESCRIPTS}/Annual_{self.sector}_daily_{season}_{self.case_name}.csh'
        cmd = self.CMD_CP % (f'{self.DIR_TEMPLATES}/template_Annual_ptertac_daily_summer.csh', run_daily_path)
        os.system(cmd)

        # Write GRIDDESC info
        grid_info = f'setenv GRIDDESC {self.CMAQ_DATA}/{self.appl}/mcip/GRIDDESC'
        utils.write_to_template(run_daily_path, grid_info, id='%GRID%')

        # Write emissions file info
        emis_files  = f'setenv EMISINV_A {self.NEI_CASEINPUTS}/{self.sector}/{self.emisinv_a}'
        emis_files += f'setenv EMISINV_B {self.NEI_CASEINPUTS}/{self.sector}/{self.emisinv_b}'
        emis_files += f'setenv EMISINV_C {self.NEI_CASEINPUTS}/{self.sector}/{self.emisinv_c}'
        emis_files += f'setenv EMISHOUR_A {self.NEI_CASEINPUTS}/{self.sector}/{self.emishour_a}'
        utils.write_to_template(run_daily_path, emis_files, id='%EMIS%')

        # Submit the daily script to the scheduler
        if not setup_only:
            os.system(f'sbatch {run_daily_path}')
        return
