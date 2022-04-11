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
    def __init__(self, appl, grid_name, nei_case_name='2016fh_16j', chem_mech='cmaq_cb6', region_desc='12km OTC Domain', sector='ptertac', run_months=[8], ertac_case='CONUS2016', emisinv_b='2016fh_proj_from_egunoncems_2016version1_ERTAC_Platform_POINT_calcyear2014_27oct2019.csv', emisinv_c='egunoncems_2016version1_ERTAC_Platform_POINT_27oct2019.csv', setup_yaml='dirpaths.yml', compiler='gcc', compiler_vrsn='9.3.1', smk_exe_str='Linux2_x86_64gfort_default', ioapi_exe_str='Linux2_x86_64gfort', verbose=False):
        self.appl = appl
        self.grid_name = grid_name
        self.nei_case_name = nei_case_name
        self.chem_mech = chem_mech
        self.region_desc = region_desc
        self.sector = sector
        self.run_months = run_months
        self.ertac_case = ertac_case
        self.emisinv_a = f'{self.ertac_case}_fs_ff10_future.csv' 
        self.emisinv_b = emisinv_b
        self.emisinv_c = emisinv_c
        self.emishour_a = f'{self.ertac_case}_fs_ff10_hourly_future.csv'
        self.compiler = compiler
        self.compiler_vrsn = compiler_vrsn
        self.smk_exe_str = smk_exe_str
        self.ioapi_exe_str = ioapi_exe_str
        self.verbose = verbose
        if self.verbose:
            print(f'Application: {self.appl}; Processing {self.sector} for months {self.run_months}')

        # Set model directory names
        dirs = fetch_yaml(setup_yaml)
        dirpaths = dirs.get('directory_paths')
        self.NEI_HOME = dirpaths.get('NEI_HOME')
        self.NEI_CASESCRIPTS = f'{self.NEI_HOME}/{self.nei_case_name}/scripts'
        self.NEI_CASEINPUTS = f'{self.NEI_HOME}/{self.nei_case_name}/inputs'
        self.MCIP_OUT = dirpaths.get('LOC_MCIP')
        self.SMOKE_HOME = dirpaths.get('SMOKE_HOME')
        self.SMOKE_OUT = f'{self.NEI_HOME}/{self.nei_case_name}/smoke_out/{self.nei_case_name}/{self.grid_name}/{self.chem_mech}'
        self.SMOKE_EXE = f'{self.SMOKE_HOME}/subsys/smoke/{self.smk_exe_str}'
        self.IOAPI_EXE = f'{self.SMOKE_HOME}/subsys/ioapi/{self.ioapi_exe_str}'
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

        ## Write directory_definitions.csh
        # Copy the template directory_definitions.csh script to the scripts directory
        dir_def_path = f'{self.NEI_CASESCRIPTS}/directory_definitions.csh'
        cmd = self.CMD_CP % (f'{self.DIR_TEMPLATES}/template_directory_definitions.csh', dir_def_path)
        os.system(cmd)

        # Write directory info
        dir_info =  f'# Root directory where you unzipped all .zips\n'
        dir_info += f'setenv INSTALL_DIR "{self.NEI_HOME}"\n'
        dir_info += f'\n'
        dir_info += f'# Full path of MCIP (meteorology) files\n'
        dir_info += f'setenv MET_ROOT "{self.MCIP_OUT}"\n'
        dir_info += f'\n'
        dir_info += f'## Location of SMOKE executables\n'
        dir_info += f'setenv SMOKE_LOCATION "{self.SMOKE_EXE}"\n'
        dir_info += f'\n'
        dir_info += f'## Location of I/O API utilities, such as juldate and m3xtract\n'
        dir_info += f'setenv IOAPI_LOCATION "{self.IOAPI_EXE}"\n'
        utils.write_to_template(dir_def_path, dir_info, id='%DIR%') 

        # Write case info
        case_info =  f'# Case name\n'
        case_info += f'setenv CASE "{self.nei_case_name}"\n'
        case_info += f'\n'
        case_info += f'## Grid name\n'
        case_info += f'setenv REGION "{self.region_desc}"\n'
        case_info += f'setenv REGION_ABBREV "{self.grid_name}" # affects filename labeling\n'
        case_info += f'setenv REGION_IOAPI_GRIDNAME "{self.grid_name}" # should match GRIDDESC\n'
        case_info += f'\n'
        case_info += f'## Speciation mechanism name\n'
        case_info += f'setenv EMF_SPC "{self.chem_mech}"\n'
        utils.write_to_template(dir_def_path, case_info, id='%CASE%')   

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

    def run_inlineto2d(self, date, run_hours=1, mem_per_node=20):
        """
        Run the inlineto2d utilty to visualize the change in point-source outputs.
        """
        # Format the date
        date = utils.format_date(date)

        ## Write the run script
        # Copy the template run_inlineto2d script to the scripts directory
        run_inln_path = f'{self.SMOKE_OUT}/{self.sector}/run_inlineto2d.csh'
        cmd = self.CMD_CP % (f'{self.DIR_TEMPLATES}/template_run_inlineto2d.csh', run_inln_path)
        os.system(cmd)

        # Write slurm info
        slurm_info  = f'#SBATCH -J inln22d		# Job name\n'
        slurm_info += f'#SBATCH -o /dev/null		# Name of stdout output file\n'
        slurm_info += f'#SBATCH --nodes=1		# Total number of nodes requested\n'
        slurm_info += f'#SBATCH --ntasks=1		# Total number of tasks to be configured for\n' 
        slurm_info += f'#SBATCH --tasks-per-node=1	# sets number of tasks to run on each node\n'
        slurm_info += f'#SBATCH --cpus-per-task=1	# sets number of cpus needed by each task\n'
        slurm_info += f'#SBATCH --get-user-env		# tells sbatch to retrieve the users login environment\n'
        slurm_info += f'#SBATCH -t {run_hours}:00:00		# Run time (hh:mm:ss)\n'
        slurm_info += f'#SBATCH --mem={mem_per_node}000M		# memory required per node\n'
        slurm_info += f'#SBATCH --partition=default_cpu	# Which queue it should run on\n'
        utils.write_to_template(run_inln_path, slurm_info, id='%SLURM%')

        # Write setup/run info
        run_info =  f'setenv SMOKE_OUT_PTSECTOR {self.SMOKE_OUT}/{self.sector}\n'
        run_info += f'setenv INLN $SMOKE_OUT_PTSECTOR/inln_mole_{self.sector}_{date.strftime("%Y%m%d")}_{self.grid_name}_{self.chem_mech}_{self.nei_case_name}.ncf\n'
        run_info += f'setenv STACK_GROUPS $SMOKE_OUT_PTSECTOR/stack_groups_{self.sector}_{self.grid_name}_{self.nei_case_name}.ncf\n'
        run_info += f'setenv OUTFILE $SMOKE_OUT_PTSECTOR/2d_mole_{self.sector}_{date.strftime("%Y%m%d")}_{self.grid_name}_{self.chem_mech}_{self.nei_case_name}.ncf\n'
        run_info += f'setenv LOGFILE {self.NEI_HOME}/{self.nei_case_name}/intermed/{self.sector}/logs/inlineto2d_{self.sector}_{self.nei_case_name}_{self.grid_name}.log\n'
        run_info += f'setenv GRIDDESC {self.GRIDDESC}\n'
        run_info += f'# setenv G_GRIDPATH {self.GRIDDESC}\n'
        run_info += f'setenv IOAPI_GRIDNAME_1 {self.grid_name}\n'
        run_info += f'setenv PROMPTFLAG N\n'
        run_info += f'\n'
        run_info += f'rm $LOGFILE\n'
        run_info += f'{self.SMOKE_EXE}/inlineto2d\n'
        utils.write_to_template(run_inln_path, run_info, id='%RUNTIME%')

        # Submit inlineto2d to the scheduler
        os.system(f'sbatch {run_inln_path}')
        return
