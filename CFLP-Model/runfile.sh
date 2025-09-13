#!/bin/bash

# SLURM script for running Durham Public Schools CFLP optimization
# Expected runtime: 6-15 hours depending on problem size

# Job name
#SBATCH --job-name=cflp_linear_optimization

# Partition 
#SBATCH --partition=scavenger

# Number of CPUs
#SBATCH --cpus-per-task=8

# Memory requirement 
#SBATCH --mem=32GB

# Maximum runtime 
#SBATCH --time=30-00:00:00

# Error and output files
#SBATCH -e slurm.err
#SBATCH -o slurm.out

# Python environment setup 
. "/hpc/group/dataplus/lnw20/miniconda3/etc/profile.d/conda.sh"
conda activate dataplus-env

# Run CFLP model with command line arguments
# Default parameters if none provided:
#   - Planning units: hs_full_geo.geojson
#   - Schools: dps_hs_locations.geojson  
#   - SGR level: none
python CFLP.py ${1:-hs_full_geo.geojson} ${2:-dps_hs_locations.geojson} ${3:-none} ${@:4}

# Usage examples:
# sbatch runfile.sh                                                    
# sbatch runfile.sh hs_full_geo.geojson dps_hs_locations.geojson half # Half SGR
# sbatch runfile.sh hs_full_geo.geojson dps_hs_locations.geojson full --include-dsa # Full SGR with DSA