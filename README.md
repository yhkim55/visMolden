# visMolden

Report a CASSCF calculation as a 16:9 PowerPoint deck of active-space
orbitals. Each orbital is written to a cube file with pyscf, rendered with
xyzrender, and placed in an 8-column grid labeled with its occupation.

The view can be oriented so that chosen atoms (e.g. the reacting atoms of a
reaction step) are seen most distinctively: spread out in the image plane and
not hidden behind other atoms.

## Requirements

- Python with `pyscf`, `python-pptx`, `Pillow`, `numpy`
- `xyzrender` importable from the same Python
- Slurm (`sbatch`) if using `run.sh`

## Usage

```bash
# orient on "reacting_atoms" -> "idx" from bond_changes.json
python cas_report.py casscf.molden bond_changes.json

# orient on atoms given directly (0-indexed, same convention as the json)
python cas_report.py casscf.molden --atoms 25,27,37,21

# xyzrender's default (PCA) orientation
python cas_report.py casscf.molden
```

Arguments:

- `molden` — CASSCF Molden file (natural orbitals).
- `bond_changes` (optional) — json with `"reacting_atoms": {"idx": [...]}`
  (0-indexed atoms).
- `--atoms` — 3 or more 0-indexed atoms, e.g. `25,27,37` or `21-23,25`.
  Overrides the json. The first atom is placed on the left of the image.
- `--orbitals` — 0-indexed orbitals, e.g. `89-96`. If omitted, defaults to
  the orbitals with fractional occupancy (`1e-4 < occ < 2 - 1e-4`).
- `-o`, `--output` — output PPTX path (default: `<molden_basename>_cas_report.pptx`).
- `--one-based` — print 1-based orbital indices on the slides.
- `--iso` — isovalue (xyzrender default 0.05).
- `--res` — cube grid points per axis (default 80).
- `--config` — xyzrender config preset (default `paton`).
- `--canvas` — xyzrender canvas size in px.
- `--workdir` — keep cube/PNG files in this directory (by default a temporary
  directory is used and deleted afterwards).
- `--title` — override the slide title.

`run.sh` submits the same command to a compute node:

```bash
~/bin/visMolden/run.sh casscf.molden bond_changes.json
```

## Output

Slides are 13.333 x 7.5 in (16:9). Each slide has:

- title `CAS(ne, mo) <absolute molden path>`
- subtitle `Orbital index: 89-96` listing the orbitals on that slide
- an 8-column grid of orbital images, each labeled `Occ=y.zzz` (Arial 12 pt);
  the number of rows per slide follows from the image aspect ratio

All images share one crop box, so the molecule has the same size and position
in every image.

## Orientation

With reacting atoms given, about 4000 view directions are scored by

- spread: projected pair distances of the chosen atoms relative to their 3D
  distances (1 when all lie in the image plane), minus
- occlusion: other atoms in front of a chosen atom that overlap it on screen
  (H counts half).

The best direction becomes the viewing axis, and the molecule's longest
projected extent is laid horizontally. The rotation is applied to the atom
positions through the xyzrender Python API with auto-orientation off;
xyzrender maps the cube grid onto the rotated atoms, so the lobes follow. The
result is deterministic for a given geometry and atom list.

## Files

- `cas_report.py` — the whole pipeline: cube generation, orientation,
  rendering, and PPTX layout.
- `run.sh` — Slurm submission wrapper for `cas_report.py` (not tracked by
  git; `*.sh` is in `.gitignore`).
