import os
import sys
import argparse
import logging
import subprocess
from concurrent.futures import ProcessPoolExecutor
from glob import glob
from pyscf.tools import molden, cubegen
from collate_png_ppt import collate_png_ppt
from find_active_space import find_active_space


def get_occup(molden_fn):
    mol, mo_energy, mo_coeff, mo_occ, rrep_labels, spins = molden.load(molden_fn)
    return mo_occ


def molden_to_cube(molden_fn, orb_idx):
    mol, mo_energy, mo_coeff, mo_occ, rrep_labels, spins = molden.load(molden_fn)
    cube_fn = f"orb{orb_idx:03d}.cube"
    print(molden_fn, orb_idx)
    cubegen.orbital(mol, cube_fn, mo_coeff[:, orb_idx])


def generate_orbital_images(molden_fn, orb_indices, out_dir):
    out_dir = os.path.abspath(out_dir)
    os.makedirs(out_dir, exist_ok=True)

    occ = get_occup(molden_fn)

    cwd = os.getcwd()
    os.chdir(out_dir)

    try:
        logging.info(f"Generating cube files for {molden_fn}")
        nproc = int(os.environ.get("SLURM_CPUS_PER_TASK", os.cpu_count() or 1))
        with ProcessPoolExecutor(max_workers=nproc) as executor:
            list(executor.map(molden_to_cube, [molden_fn] * len(orb_indices), orb_indices))

        cubefiles = sorted(glob('*.cube'))
        for cube_fn in cubefiles:
            png_fn = cube_fn.replace('cube', 'png')
            subprocess.run(f'xyzrender {cube_fn} --mo --no-orient --hy --idx -o {png_fn}', shell=True)
        

    finally:
        os.chdir(cwd)

    png_map = {idx: os.path.join(out_dir, f"orb{idx:03d}.png") for idx in orb_indices}

    for idx, fn in png_map.items():
        if not os.path.exists(fn):
            raise FileNotFoundError(f"PNG not found for orbital {idx}: {fn}")

    return png_map, occ


def parse_indices(spec):
    """
    Parse a 0-indexed orbital index spec like "15-30,35,38" into a sorted
    list of unique ints.
    """
    indices = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            lo, hi = part.split("-")
            indices.update(range(int(lo), int(hi) + 1))
        else:
            indices.add(int(part))
    return sorted(indices)


def main():
    parser = argparse.ArgumentParser(
        description="Generate a PowerPoint visualizing orbitals from a Molden file."
    )
    parser.add_argument("molden")
    parser.add_argument(
        "indices",
        nargs="?",
        default=None,
        help='0-indexed orbital indices, e.g. "15-30,35,38". '
             'If omitted, uses orbitals with fractional occupancy (active space).',
    )
    parser.add_argument("--dir")
    parser.add_argument("--output", default="orbitals.pptx")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        stream=sys.stdout,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    if args.dir is None:
        args.dir = args.molden.replace('.molden', '_img')

    if args.indices is None:
        orb_indices, _ = find_active_space(args.molden)
    else:
        orb_indices = parse_indices(args.indices)

    png_map, occ = generate_orbital_images(
        os.path.abspath(args.molden), orb_indices, args.dir
    )

    collate_png_ppt(
        png_map,
        occ,
        orb_indices,
        args.output,
    )

    logging.info(f"Created PowerPoint: {args.output}")


if __name__ == "__main__":
    main()
