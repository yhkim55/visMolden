import os
import sys
import pathlib
import shutil
import argparse
import logging
import tempfile
import subprocess
from concurrent.futures import ProcessPoolExecutor
from glob import glob
import numpy as np
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


def molden_to_xyz(molden_fn):
    mol, _, _, _, _, _ = molden.load(molden_fn)
    atoms = mol._atom
    symbols = [a[0] for a in atoms]
    coords = np.array([a[1] for a in atoms])
    return symbols, coords


def rotation_from_triangle(a: np.ndarray, b: np.ndarray, c: np.ndarray, up: np.ndarray | None = None) -> np.ndarray:
    """Rotation matrix R (apply as `coords @ R.T`) that aligns the plane
    through points a, b, c so its normal points along +z (toward the viewer),
    matching xyzrender's default view convention (x=right, y=up, z=toward viewer).

    a, b, c: (3,) arrays, the three atom coordinates defining the plane.
    up: optional (3,) direction. If given, the in-plane twist about z is
        chosen so that `up`'s projection onto the new viewing plane points
        along +y (screen-up). If omitted, the minimal (shortest-arc)
        rotation is used and the in-plane twist is left unconstrained.
    """
    a, b, c = np.asarray(a, float), np.asarray(b, float), np.asarray(c, float)
    normal = np.cross(b - a, c - a)
    norm = np.linalg.norm(normal)
    if norm < 1e-10:
        raise ValueError("a, b, c are collinear; plane normal is undefined")
    normal /= norm

    target = np.array([0.0, 0.0, 1.0])
    cos_t = float(np.dot(normal, target))

    if cos_t < -1 + 1e-8:
        R = np.diag([1.0, -1.0, -1.0])  # 180 deg flip about x
    else:
        v = np.cross(normal, target)
        s = np.linalg.norm(v)
        if s < 1e-10:
            R = np.eye(3)
        else:
            vx = np.array([
                [0, -v[2], v[1]],
                [v[2], 0, -v[0]],
                [-v[1], v[0], 0],
            ])
            R = np.eye(3) + vx + vx @ vx * ((1 - cos_t) / (s**2))

    if up is not None:
        up = np.asarray(up, float)
        up_rot = R @ up
        up_proj = up_rot - np.dot(up_rot, target) * target
        n = np.linalg.norm(up_proj)
        if n > 1e-10:
            up_proj /= n
            angle = np.pi / 2 - np.arctan2(up_proj[1], up_proj[0])
            cz, sz = np.cos(angle), np.sin(angle)
            Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
            R = Rz @ R

    return R


def apply_rotation(coords: np.ndarray, R: np.ndarray) -> np.ndarray:
    """Apply R to an (N,3) coordinate array."""
    return coords @ R.T
    

def write_xyz(coords, symbols):
    tmpfile = tempfile.NamedTemporaryFile(mode='w+t')
    tmpfile.write(f'{len(symbols)}\n\n')
    for symb, row in zip(symbols, coords):
        tmpfile.write(f'{symb:<2} {row[0]:13.6f} {row[1]:13.6f} {row[2]:13.6f}\n')
    return tmpfile.name


def generate_oriented_xyz(molden_fn, orient_atoms):
    symbols, coords = molden_to_xyz(molden_fn)
    a, b, c = coords[orient_atoms[0]], coords[orient_atoms[1]], coords[orient_atoms[2]]
    R = rotation_from_triangle(a, b, c)
    coords_1 = apply_rotation(coords, R)
    tmpfile_path = write_xyz(coords_1, symbols)
    return tmpfile_path


def generate_orbital_images(molden_fn, orb_indices, out_dir, orient_atoms=None):
    out_dir = os.path.abspath(out_dir)
    os.makedirs(out_dir, exist_ok=True)

    occ = get_occup(molden_fn)

    cwd = os.getcwd()
    os.chdir(out_dir)

    do_orient = False

    try:
        logging.info(f"Generating cube files for {molden_fn}")
        nproc = int(os.environ.get("SLURM_CPUS_PER_TASK", os.cpu_count() or 1))
        with ProcessPoolExecutor(max_workers=nproc) as executor:
            list(executor.map(molden_to_cube, [molden_fn] * len(orb_indices), orb_indices))

        cubefiles = sorted(glob('*.cube'))
        
        if orient_atoms is not None:
            tmp_xyz = generate_oriented_xyz(molden_fn, orient_atoms)
            do_orient = True


        for cube_fn in cubefiles:
            png_fn = cube_fn.replace('cube', 'png')
            if do_orient:
                subprocess.run(f'xyzrender {cube_fn} --mo --ref {tmp_xyz} --hy --idx -o {png_fn}', shell=True)
            else:
                subprocess.run(f'xyzrender {cube_fn} --mo --no-orient --hy --idx -o {png_fn}', shell=True)
        

    finally:
        os.chdir(cwd)
        pathlib.Path.unlink(tmp_xyz)


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


def parse_orient_atoms(s):
    s = s.split(',')
    if len(s) != 3:
        raise RuntimeError('Input for orient_atoms: three integers with comma separated')
    try: 
        s = list(map(int, s))
        return s
    except:
        raise RuntimeError('Input for orient_atoms: three integers with comma separated')


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
    parser.add_argument("--output", default=None,
                        help='output pptx file, defaults as MOLDEN_orbitals.pptx')
    parser.add_argument("--erase_dir", default=True, action='store_false',
                        help='Add this option to preserve cube & pngs in --dir')
    parser.add_argument("--orient_atoms", default=None,
                        help='Three atom indices(0-idx) for manual orientation, separated by comma (ex. 0,3,7)')
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

    if args.output is None:
        args.output = args.molden.replace('.molden', '_orbitals.pptx')

    if args.orient_atoms is not None:
        args.orient_atoms = parse_orient_atoms(args.orient_atoms)

    png_map, occ = generate_orbital_images(
        os.path.abspath(args.molden), orb_indices, args.dir, args.orient_atoms
    )

    collate_png_ppt(
        png_map,
        occ,
        orb_indices,
        args.output,
    )

    logging.info(f"Created PowerPoint: {args.output}")

    if args.erase_dir:
        shutil.rmtree(args.dir)


if __name__ == "__main__":
    main()
