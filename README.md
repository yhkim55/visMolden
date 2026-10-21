# visMolden

Report molecular orbitals as a PowerPoint deck of orbitals. Each orbital is written 
to a cube file with pyscf, rendered with xyzrender, and placed in a slide labeled with its occupation.

Designed as a reporting tool for CASSCF (and/or post-CASSCF) calculations,
but can be used in general purpose.

The view can be oriented so that chosen atoms (e.g. the reacting atoms of a
reaction step) are seen most distinctively: spread out in the image plane and
not hidden behind other atoms.

## Requirements

- Python with `pyscf`, `python-pptx`, `Pillow`, `numpy`
- `xyzrender` importable from the same Python

## Usage

```bash
# orient on "reacting_atoms" -> "idx" from bond_changes.json
python vismolden.py casscf.molden bond_changes.json

# orient on atoms given directly (0-indexed, same convention as the json)
python vismolden.py casscf.molden --atoms 25,27,37,21

# xyzrender's default (PCA) orientation
python vismolden.py casscf.molden
```

Arguments:

- `molden` — Molden file (e.g. CASSCF natural orbitals).
- `bond_changes` (optional) — json with `"reacting_atoms": {"idx": [...]}`
  (0-indexed atoms).
- `--atoms` — 3 or more 0-indexed atoms, e.g. `25,27,37` or `21-23,25`.
  Overrides the json. The first atom is placed on the left of the image.
- `--orbitals` — 0-indexed orbitals, e.g. `89-96`. If omitted, defaults to
  the orbitals with fractional occupancy (`1e-4 < occ < 2 - 1e-4`).
- `-o`, `--output` — output PPTX path (default: `<molden_basename>_orbitals.pptx`).
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

Each slide has:

- title `CAS(ne, mo) <absolute molden path>`
- subtitle `Orbital index: 89-96` listing the orbitals on that slide
- an 8-column grid of orbital images, each labeled `Occ=y.zzz`;
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

