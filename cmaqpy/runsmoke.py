"""
A Class for processing EGU emissions using SMOKE.
"""
import datetime
import os
import sys
import time
from .data.fetch_data import fetch_yaml


class SMOKEModel():
    """
    This Class provides a framework for running the ptegu/ptertac sectors in SMOKE.
    """
    def __init__(self, case_name='', sector='ptertac', run_months=[8], setup_yaml='dirpaths.yml', compiler='gcc', compiler_vrsn='9.3.1', verbose=False):
        self.case_name = case_name
        self.sector = sector
        self.run_months = run_months
        self.compiler = compiler
        self.compiler_vrsn = compiler_vrsn
        self.verbose = verbose
        if self.verbose:
            print(f'Processing {self.sector} for months {self.run_months}')

        # Set model directory names
        dirs = fetch_yaml(setup_yaml)
        dirpaths = dirs.get('directory_paths')
        self.NEI_CASE = dirpaths.get('NEI_CASE')
        self.NEI_CASESCRIPTS = f'{self.NEI_CASE}/scripts/point'

        # Define linux command aliai
        self.CMD_LN = 'ln -sf %s %s'
        self.CMD_CP = 'cp %s %s'
        self.CMD_MV = 'mv %s %s'
        self.CMD_RM = 'rm %s'

    def run_onetime(self):
        """
        Run the onetime step for a point sector.
        """
        # Copy the template onetime run script to the scripts directory
        run_onetime_path = f'{self.NEI_CASESCRIPTS}/Annual_{self.sector}_onetime_{self.case_name}.csh'
        cmd = self.CMD_CP % (f'{self.DIR_TEMPLATES}/template_run_mcip.csh', run_mcip_path)
        os.system(cmd)

    def run_daily(self, season='summer'):
        """
        Run the onetime step for a point sector.
        """
        # Copy the template onetime run script to the scripts directory
        run_onetime_path = f'{self.NEI_CASESCRIPTS}/Annual_{self.sector}_daily_{season}_{self.case_name}.csh'
        cmd = self.CMD_CP % (f'{self.DIR_TEMPLATES}/template_run_mcip.csh', run_mcip_path)
        os.system(cmd)
