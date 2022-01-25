#!/bin/csh

#SBATCH -J cctm                  # Job name
#SBATCH -o /home/jas983/models/cmaq/CMAQ_v5.3.3/CCTM/scripts/out.cctm.%j              # Name of stdout output file(%j expands to jobId)
#SBATCH -e /home/jas983/models/cmaq/CMAQ_v5.3.3/CCTM/scripts/errors.cctm.%j              # Name of stderr output file(%j expands to jobId)
#SBATCH --ntasks=16             # Total number of tasks to be configured for.
#SBATCH --tasks-per-node=16     # sets number of tasks to run on each node.
#SBATCH --cpus-per-task=1       # sets number of cpus needed by each task (if task is "make -j3" number should be 3).
#SBATCH --get-user-env          # tells sbatch to retrieve the users login environment. 
#SBATCH -t 24:00:00            # Run time (hh:mm:ss)
#SBATCH --mem=20000M            # memory required per node
#SBATCH --partition=default_cpu # Which queue it should run on.

/home/jas983/models/cmaq/CMAQ_v5.3.3/CCTM/scripts/run_cctm_Bench_2016_12SE1.csh >&! /home/jas983/models/cmaq/CMAQ_v5.3.3/CCTM/scripts/cctm_Bench_2016_12SE1.log
