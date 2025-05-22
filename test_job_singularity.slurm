#!/bin/bash -l 
  
#SBATCH --job-name=example 
#SBATCH --time=0-00:05:00 
#SBATCH --array=1-4
#SBATCH --cpus-per-task=4
#SBATCH --mem-per-cpu=500MB 
#SBATCH --output=probe_%j.out
#SBATCH --partition=cpu-1heure

SINGULARITY_IMG=image_ubuntu24.04.sif

# Define and create a unique scratch directory
SCRATCH_DIRECTORY=$SLURM_TMPDIR/example 
mkdir -p $SCRATCH_DIRECTORY 
cd $SCRATCH_DIRECTORY

# Copy the program and singularity image to the scratch directory 
cp $SLURM_SUBMIT_DIR/test.py $SCRATCH_DIRECTORY
cp $SLURM_SUBMIT_DIR/$SINGULARITY_IMG $SCRATCH_DIRECTORY

# Run the program and give a unique name per task for the output file 
srun singularity exec --bind $SCRATCH_DIRECTORY:/scratch --pwd /scratch $SCRATCH_DIRECTORY/$SINGULARITY_IMG ./test.py

# After the job is done we copy our output back to $SLURM_SUBMIT_DIR 
#cp output_$SLURM_ARRAY_TASK_ID.txt $SLURM_SUBMIT_DIR

# We step out of the scratch directory and remove it 
cd $SLURM_SUBMIT_DIR
rm -rf $SCRATCH_DIRECTORY


# Happy end 
exit 0
