#!/bin/csh -f

#SBATCH -J inln22d		# Job name
#SBATCH -o /dev/null		# Name of stdout output file (%j expands to jobId)
#SBATCH --nodes=1		# Total number of nodes requested 
#SBATCH --ntasks=1		# Total number of tasks to be configured for. 
#SBATCH --tasks-per-node=1	# sets number of tasks to run on each node. 
#SBATCH --cpus-per-task=1	# sets number of cpus needed by each task (if task is "make -j3" number should be 3).
#SBATCH --get-user-env		# tells sbatch to retrieve the users login environment. 
#SBATCH -t 6:00:00		# Run time (hh:mm:ss) 
#SBATCH --mem=20000M		# memory required per node
#SBATCH --partition=default_cpu	# Which queue it should run on.

setenv YYYYMMDD 20160812

setenv NEI_DIR /share/mzhang/jas983/emissions_data/nei_platform2016/v1
setenv SMOKE_PTERTAC /share/mzhang/jas983/emissions_data/nei_platform2016/v1/2016fh_16j/smoke_out/2016fh_16j/12OTC2/cmaq_cb6/ptertac
setenv INLN $SMOKE_PTERTAC/inln_mole_ptertac_${YYYYMMDD}_12OTC2_cmaq_cb6_2016fh_16j.ncf
setenv STACK_GROUPS $SMOKE_PTERTAC/stack_groups_ptertac_12OTC2_2016fh_16j.ncf
setenv OUTFILE $SMOKE_PTERTAC/2d_mole_ptertac_${YYYYMMDD}_12OTC2_cmaq_cb6_2016fh_16j.ncf
setenv LOGFILE $NEI_DIR/2016fh_16j/intermed/ptertac/logs/inlineto2d_ptertac_2016fh_16j_12OTC2.log
setenv GRIDDESC /share/mzhang/jas983/cmaq_data/CMAQ_v5.3.3/cmaqpy/cmaqpy/data/GRIDDESC2
# setenv G_GRIDPATH /share/mzhang/jas983/cmaq_data/CMAQ_v5.3.3/cmaqpy/cmaqpy/data/GRIDDESC2
setenv IOAPI_GRIDNAME_1 12OTC2
setenv PROMPTFLAG N

rm $LOGFILE
$SMK_HOME/subsys/smoke/Linux2_x86_64gfort/inlineto2d
