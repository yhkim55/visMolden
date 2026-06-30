import numpy as np
from scipy.spatial.transform import Rotation as R

def get_rotation_from_molden(molden_fn):
    coords = []
    with open(molden_fn) as f:
        in_coords = False
        for line in f:
            if line.startswith('[Atoms]'):
                in_coords = True
                continue
            if in_coords:
                if len(line.strip().split()) < 6:
                    break
                parts = line.split()
                coords.append([float(parts[-3]), float(parts[-2]), float(parts[-1])])
    
    coords = np.array(coords)
    atom1 = coords[0]
    atom2 = coords[1]
    centered_coords = coords - atom1
    bond_vec = atom2 - atom1
    bond_vec /= np.linalg.norm(bond_vec)

    # Rotate bond vector to +Y axis (0,1,0)
    rot1 = R.align_vectors([[0, 1, 0]], [bond_vec])[0]
    aligned_coords = rot1.apply(centered_coords)

    # PCA to find major axis
    cov = np.cov(aligned_coords.T)
    eigvals, eigvecs = np.linalg.eigh(cov)
    major_axis = eigvecs[:, np.argmax(eigvals)]

    # Project major axis onto XZ-plane (we don't want to break bond alignment)
    major_axis_proj = major_axis.copy()
    major_axis_proj[1] = 0  # remove Y component
    if np.linalg.norm(major_axis_proj) > 1e-6:
        major_axis_proj /= np.linalg.norm(major_axis_proj)
        # Rotate major axis projection to X axis
        rot_axis = np.cross(major_axis_proj, [1, 0, 0])
        rot_angle = np.arccos(np.dot(major_axis_proj, [1, 0, 0]))
        if np.linalg.norm(rot_axis) > 1e-6:
            rot_axis /= np.linalg.norm(rot_axis)
            rot2 = R.from_rotvec(rot_angle * rot_axis)
            total_rot = rot2 * rot1
        else:
            total_rot = rot1
    else:
        total_rot = rot1  # already aligned

    # Convert to Euler angles (VMD uses degrees)
    euler_deg = total_rot.as_euler('xyz', degrees=True)
    RX, RY, RZ = euler_deg
    return RX, RY, RZ
