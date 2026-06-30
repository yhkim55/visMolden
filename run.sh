#!/bin/bash

if [ "$#" -eq 0 ]; then
    echo "Usage: $0 molden_path 0-indices [--output OUTPUT]"
    exit 1
fi

sbatch <<EOF
#!/bin/bash
#SBATCH -N 1
#SBATCH --cpus-per-task=4
#SBATCH -t 03:00:00
#SBATCH --job-name=molden_to_pptx
#SBATCH --mem=8G
#SBATCH --account=pi-lgagliardi
#SBATCH --partition=amd
#SBATCH -o orbgif.out
#SBATCH -e orbgif.err
python /home/yhkim5/bin/visMolden/molden_to_pptx.py $@
EOF
