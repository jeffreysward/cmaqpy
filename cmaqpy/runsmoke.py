"""
A Class for processing EGU emissions using SMOKE.
"""
import datetime
import os
import sys
import time
from . import utils
from .data.fetch_data import fetch_yaml


class SMOKEModel:
    """
    This Class provides a framework for running the ptegu/ptertac sectors in SMOKE.
    """
    def __init__(self, appl, grid_name, nei_case_name='2016fh_16j', sector='ptertac', run_months=[8], ertac_case='CONUS2016', emisinv_b='2016fh_proj_from_egunoncems_2016version1_ERTAC_Platform_POINT_calcyear2014_27oct2019.csv', emisinv_c='egunoncems_2016version1_ERTAC_Platform_POINT_27oct2019.csv', setup_yaml='dirpaths.yml', compiler='gcc', compiler_vrsn='9.3.1', verbose=False):
        self.appl = appl
        self.grid_name = grid_name
        self.nei_case_name = nei_case_name
        self.sector = sector
        self.run_months = run_months
        self.ertac_case = ertac_case
        self.emisinv_a = f'{self.ertac_case}_fs_ff10_future.csv' 
        self.emisinv_b = emisinv_b
        self.emisinv_c = emisinv_c
        self.emishour_a = f'{self.ertac_case}_fs_ff10_hourly_future.csv'
        self.compiler = compiler
        self.compiler_vrsn = compiler_vrsn
        self.verbose = verbose
        if self.verbose:
            print(f'Application: {self.appl}; Processing {self.sector} for months {self.run_months}')

        # Set model directory names
        dirs = fetch_yaml(setup_yaml)
        dirpaths = dirs.get('directory_paths')
        self.NEI_HOME = dirpaths.get('NEI_HOME')
        self.NEI_CASESCRIPTS = f'{self.NEI_HOME}/{self.nei_case_name}/scripts'
        self.NEI_CASEINPUTS = f'{self.NEI_HOME}/{self.nei_case_name}/inputs'
        self.ERTAC_HOME = dirpaths.get('ERTAC_HOME')
        self.CMAQ_DATA = dirpaths.get('CMAQ_DATA')
        self.DIR_TEMPLATES = dirpaths.get('DIR_TEMPLATES')
        filepaths = dirs.get('file_paths')
        self.GRIDDESC = filepaths.get('GRIDDESC')

        # Define linux command aliai
        self.CMD_LN = 'ln -sf %s %s'
        self.CMD_CP = 'cp %s %s'
        self.CMD_MV = 'mv %s %s'
        self.CMD_RM = 'rm %s'

    def run_sector(self, type='onetime', season='summer', n_procs=1, gb_mem=100, run_hours=12, setup_only=False):
        """
        Run the onetime step for a point sector.
        """
        # Copy the template onetime run script to the scripts directory
        if type == 'onetime':
            run_script_path = f'{self.NEI_CASESCRIPTS}/point/Annual_{self.sector}_onetime_{self.grid_name}_{self.nei_case_name}.csh'
            cmd = self.CMD_CP % (f'{self.DIR_TEMPLATES}/template_Annual_{self.sector}_onetime.csh', run_script_path)
        elif type == 'daily':
            run_script_path = f'{self.NEI_CASESCRIPTS}/point/Annual_{self.sector}_daily_{season}_{self.grid_name}_{self.nei_case_name}.csh'
            cmd = self.CMD_CP % (f'{self.DIR_TEMPLATES}/template_Annual_{self.sector}_daily_summer.csh', run_script_path)
        else:
            print(f'Type "{type}" not recognized. Please use "onetime" or "daily"')
            raise ValueError
        os.system(cmd)

        # Write slurm info
        slurm_info  = f'#SBATCH --ntasks={n_procs}		# Total number of tasks\n' 
        slurm_info += f'#SBATCH --tasks-per-node={n_procs}	# sets number of tasks to run on each node\n' 
        slurm_info += f'#SBATCH --cpus-per-task=1	# sets number of cpus needed by each task (if task is "make -j3" number should be 3)\n'
        slurm_info += f'#SBATCH --get-user-env		# tells sbatch to retrieve the users login environment\n'
        slurm_info += f'#SBATCH -t {run_hours}:00:00		# Run time (hh:mm:ss)\n'
        slurm_info += f'#SBATCH --mem={gb_mem}000M		# memory required per node\n'
        slurm_info += f'#SBATCH --partition=default_cpu	# Which queue it should run on\n'
        utils.write_to_template(run_script_path, slurm_info, id='%SLURM%')

        # Write directory definition info
        dir_info = f'source {self.NEI_CASESCRIPTS}/directory_definitions.csh'
        utils.write_to_template(run_script_path, dir_info, id='%DIR_DEF%')

        # Write GRIDDESC info
        grid_info = f'setenv GRIDDESC "{self.GRIDDESC}"'
        utils.write_to_template(run_script_path, grid_info, id='%GRID%')

        # Write emissions file info
        emis_files  = f'setenv EMISINV_A "{self.ERTAC_HOME}/{self.ertac_case}/for_SMOKE/{self.emisinv_a}"\n'
        emis_files += f'setenv EMISINV_B "{self.NEI_HOME}/{self.nei_case_name}/inputs/{self.sector}/{self.emisinv_b}"\n'
        emis_files += f'setenv EMISINV_C "{self.NEI_HOME}/{self.nei_case_name}/inputs/{self.sector}/{self.emisinv_c}"\n'
        emis_files += f'setenv EMISHOUR_A "{self.ERTAC_HOME}/{self.ertac_case}/for_SMOKE/{self.emishour_a}"\n'
        utils.write_to_template(run_script_path, emis_files, id='%EMIS%')

        # Submit the onetime script to the scheduler
        if not setup_only:
            os.system(f'sbatch {run_script_path}')
        return
