# visMolden

Visualize molecular orbitals from a Molden file as a PowerPoint deck: each
orbital is rendered to a cube file, converted to a PNG, and collated into a
slide grid with occupation numbers labeled.

## Requirements

- Python with `pyscf`, `python-pptx`
- `xyzrender` available on `PATH` (used to render cube files to PNG)
- Slurm (`sbatch`) if using `run.sh`

## Usage

### Submit as a Slurm job

```bash
./run.sh /path/to/file.molden 15-30,35,38
```

### Run directly

```bash
python molden_to_pptx.py /path/to/file.molden 15-30,35,38
```

Arguments:

- `molden` — path to the Molden file.
- `indices` (optional) — 0-indexed orbitals to visualize, e.g. `15-30,35,38`
  (ranges and comma-separated values). If omitted, defaults to the orbitals
  with fractional occupancy (the active space).
- `--dir` — working directory for cube/PNG files (default:
  `<molden_basename>_img`).
- `--output` — output PPTX path (default: `<molden_basename>_orbitals.pptx`).
- `--erase_dir` — pass this flag to keep the cube/PNG working directory
  instead of deleting it after the PPTX is built (deleted by default).

## Output

A PowerPoint file with a 3x5 grid of orbital images per slide, each labeled
with its index and occupation number.

## Files

- `molden_to_pptx.py` — main entry point: generates cube files, renders PNGs,
  and builds the PPTX.
- `collate_png_ppt.py` — lays out rendered PNGs into PPTX slides.
- `find_active_space.py` — finds orbitals with fractional occupancy in a
  Molden file.
- `rotate_image.py` — computes a molecule orientation (rotation) from atomic
  coordinates in a Molden file.
- `run.sh` — Slurm submission wrapper for `molden_to_pptx.py`.
