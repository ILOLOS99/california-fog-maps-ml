#!/bin/bash
#SBATCH -N 1
#SBATCH -c 8
#SBATCH -t 24:00:00
#SBATCH -p public
#SBATCH -q public
#SBATCH --array=1-128
#SBATCH --mem=256G
#SBATCH -o fog_%A_%a.out
#SBATCH -e fog_%A_%a.err
#SBATCH --mail-type=END,FAIL
#SBATCH --export=NONE

module load r-4.5.1-gcc-12.1.0

Rscript "09_predict_fog_tiles_30m_SLURM.R" $SLURM_ARRAY_TASK_ID
