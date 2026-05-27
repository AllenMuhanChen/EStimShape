"""
Post-process @animal_warper outputs with a rigid (6-DOF: rotation + translation
only) alignment to the original template.

@animal_warper's internal alignment optimizes a full 12-DOF affine + nonlinear
warp. The rigid component buried in that affine is biased by the scale/shear
terms — so the three subject-space outputs (subject, atlas-in-subject,
template-in-subject) end up mutually aligned to each other but collectively
rotated/offset from the original template's pose. This script does a clean
6-DOF rigid fit via 3dAllineate and header-rewrites the affines so all three
land in template-aligned pose. Voxel data is byte-identical (no resampling),
which matters because the atlas is a label volume and the subject voxels are
the electrode-targeting space.

Usage:
    1. Set the path constants below.
    2. python -m src.mri.run_rigid_align

The script refuses to overwrite an existing non-empty OUTPUT_DIR.
"""

import json
import os
import shutil
import subprocess
import sys
import time

import nibabel as nib
import numpy as np


# ============================================================================
# EDIT THESE PATHS DIRECTLY.
#
# Set absolute paths to the relevant @animal_warper outputs and to the
# original template you want to align to. Leave OUTPUT_DIR somewhere safe
# (it must not already exist with contents).
# ============================================================================

# Skull-stripped subject from @animal_warper outdir. 3dAllineate works better
# on skull-stripped brains. This is the file the rigid fit uses for cost
# evaluation — it is NOT the file that gets exported.
SUBJECT_NS_NII          = "/home/connorlab/Documents/MRI/Bixby/bixby_WIP_MPrageAX_.70mm_New_warper_native/bixby_WIP_MPrageAX_.70mm_New_ns.nii.gz"   # e.g. ".../<outdir>/45X_..._corrected_ns.nii.gz"

# The three @animal_warper subject-space outputs whose affines we'll rewrite:
SUBJECT_NII             = "/home/connorlab/Documents/MRI/Bixby/bixby_WIP_MPrageAX_.70mm_New_warper_native/bixby_WIP_MPrageAX_.70mm_New.nii.gz"   # ".../<outdir>/45X_..._corrected.nii.gz"
ATLAS_IN_SUBJECT_NII    = "/home/connorlab/Documents/MRI/Bixby/bixby_WIP_MPrageAX_.70mm_New_warper_native/D99_atlas_in_NMT_v2.0_asym_in_bixby_WIP_MPrageAX_.70mm_New.nii.gz"   # ".../<outdir>/d99_atlas_in_45X_..._corrected.nii.gz"
TEMPLATE_IN_SUBJECT_NII = "/home/connorlab/Documents/MRI/Bixby/bixby_WIP_MPrageAX_.70mm_New_warper_native/NMT2_in_bixby_WIP_MPrageAX_.70mm_New.nii.gz"   # ".../<outdir>/BASEORIG_in_45X_..._corrected.nii.gz"

# The original NMT template — the rigid alignment target.
ORIGINAL_TEMPLATE       = "/home/connorlab/Documents/NMT_v2.0_asym/NMT_v2.0_asym/NMT_v2.0_asym.nii.gz"   # e.g. ".../NMT_v2.0_sym.nii.gz"

# Output directory for the rigid-aligned NIfTIs + transform files. Must not
# already exist with contents (script refuses to overwrite).
OUTPUT_DIR              = "/home/connorlab/Documents/MRI/Bixby/bixby_WIP_MPrageAX_.70mm_New_warper_native/rigid_aligned"   # e.g. ".../<outdir>/rigid_aligned"
# ============================================================================


def _require_afni():
    if shutil.which("3dAllineate") is not None:
        return
    for d in (os.path.expanduser("~/abin"), "/usr/local/abin",
              "/opt/abin", "/usr/local/afni"):
        if os.path.isfile(os.path.join(d, "3dAllineate")):
            os.environ["PATH"] = d + os.pathsep + os.environ.get("PATH", "")
            print(f"  Found AFNI in {d}, prepended to PATH for subprocesses.")
            return
    sys.exit("ERROR: 3dAllineate not found on PATH or in standard AFNI locations.")


def _load_afni_aff12(path):
    """Parse 3dAllineate's -1Dmatrix_save output (one line of 12 numbers in
    row-major order) into a 4x4 matrix in AFNI's RAI convention.
    """
    with open(path) as f:
        for line in f:
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            nums = [float(x) for x in s.split()]
            if len(nums) == 12:
                M = np.eye(4)
                M[:3, :] = np.array(nums).reshape(3, 4)
                return M
    raise ValueError(f"No 12-number row found in {path}")


def _rai_to_ras(M):
    """AFNI's RAI -> NIfTI's RAS: flip the z axis."""
    F = np.diag([1.0, 1.0, -1.0, 1.0])
    return F @ M @ F


def _rewrite_affine(in_path, out_path, M_ras_inv):
    """Apply a header-only affine update: new_affine = M_ras_inv @ old_affine.
    Voxel data and dtype are preserved byte-identical.
    """
    img = nib.load(in_path)
    new_affine = M_ras_inv @ img.affine
    data = np.asanyarray(img.dataobj)
    new_img = nib.Nifti1Image(data, new_affine, header=img.header)
    qcode = img.header.get_qform(coded=True)[1] or 1
    scode = img.header.get_sform(coded=True)[1] or 1
    new_img.set_qform(new_affine, code=qcode)
    new_img.set_sform(new_affine, code=scode)
    nib.save(new_img, out_path)


def main():
    _require_afni()

    inputs = {
        "SUBJECT_NS_NII":          SUBJECT_NS_NII,
        "SUBJECT_NII":             SUBJECT_NII,
        "ATLAS_IN_SUBJECT_NII":    ATLAS_IN_SUBJECT_NII,
        "TEMPLATE_IN_SUBJECT_NII": TEMPLATE_IN_SUBJECT_NII,
        "ORIGINAL_TEMPLATE":       ORIGINAL_TEMPLATE,
        "OUTPUT_DIR":              OUTPUT_DIR,
    }
    missing = [k for k, v in inputs.items() if v is None]
    if missing:
        sys.exit("Set these constants at the top of run_rigid_align.py: "
                 + ", ".join(missing))

    print("=== INPUTS ===")
    for k, v in inputs.items():
        print(f"  {k:24s} : {v}")
    print()

    for k, v in inputs.items():
        if k == "OUTPUT_DIR":
            continue
        if not os.path.isfile(v):
            sys.exit(f"{k} file does not exist: {v}")

    if os.path.isdir(OUTPUT_DIR) and os.listdir(OUTPUT_DIR):
        sys.exit(f"ERROR: OUTPUT_DIR exists and is non-empty:\n  {OUTPUT_DIR}\n"
                 "Move or delete it before re-running.")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 1. Compute the 6-DOF rigid transform via 3dAllineate. We use the
    # skull-stripped subject for cost evaluation but apply the result to the
    # full-anatomy NIfTIs.
    xfm_aff12  = os.path.join(OUTPUT_DIR, "xfm_AFNI.aff12.1D")
    throwaway  = os.path.join(OUTPUT_DIR, "_throwaway_resampled.nii.gz")
    cmd = [
        "3dAllineate",
        "-source", SUBJECT_NS_NII,
        "-base", ORIGINAL_TEMPLATE,
        "-warp", "shift_rotate",     # 6-DOF: 3 translation + 3 rotation
        "-cost", "lpa",
        "-source_automask+4",
        "-cmass",
        "-twobest", "5",
        "-1Dmatrix_save", xfm_aff12,
        "-final", "NN",              # NN for the throwaway; we discard it
        "-prefix", throwaway,
        "-overwrite",
    ]
    print("[1/2] Running 3dAllineate (rigid fit, ~1 min):")
    print("  " + " ".join(cmd))
    t0 = time.time()
    proc = subprocess.run(cmd, check=False)
    dt = time.time() - t0
    print(f"3dAllineate exited with code {proc.returncode} after {dt/60:.1f} min")
    if proc.returncode != 0:
        sys.exit(proc.returncode)

    # 2. Parse the AFNI matrix, convert to RAS, invert, and apply header-only
    # to each subject-space output. AFNI's matrix maps base_RAI -> source_RAI,
    # so to move the source into the base's pose we apply inv(M) to each
    # source affine.
    M_rai = _load_afni_aff12(xfm_aff12)
    M_ras = _rai_to_ras(M_rai)
    M_ras_inv = np.linalg.inv(M_ras)

    np.savetxt(
        os.path.join(OUTPUT_DIR, "xfm_RAS.txt"), M_ras,
        header=("6-DOF rigid transform (RAS, NIfTI convention).\n"
                "source_RAS = M_ras @ base_RAS.\n"
                "Aligned-subject affine = inv(M_ras) @ old_affine."),
    )

    targets = [
        (SUBJECT_NS_NII,          "subject_ns_rigid_aligned.nii.gz"),
        (SUBJECT_NII,             "subject_rigid_aligned.nii.gz"),
        (ATLAS_IN_SUBJECT_NII,    "atlas_rigid_aligned.nii.gz"),
        (TEMPLATE_IN_SUBJECT_NII, "template_in_subject_rigid_aligned.nii.gz"),
    ]
    print(f"[2/2] Header-rewriting affines (no voxel resampling):")
    outputs = {}
    for src, name in targets:
        out = os.path.join(OUTPUT_DIR, name)
        _rewrite_affine(src, out, M_ras_inv)
        outputs[name] = out
        print(f"  {os.path.basename(src)}  ->  {out}")

    summary = {
        "inputs": {k: v for k, v in inputs.items() if k != "OUTPUT_DIR"},
        "outputs": outputs,
        "xfm_AFNI_aff12_1D": xfm_aff12,
        "xfm_RAS_txt": os.path.join(OUTPUT_DIR, "xfm_RAS.txt"),
    }
    with open(os.path.join(OUTPUT_DIR, "rigid_align.json"), "w") as f:
        json.dump(summary, f, indent=2)

    if os.path.exists(throwaway):
        os.remove(throwaway)

    print()
    print("Done. To use in mri_viewer, update mri_viewer_config.json:")
    print(f'  "default_path":       "{outputs["subject_rigid_aligned.nii.gz"]}",')
    print(f'  "atlas_nifti_path":   "{outputs["atlas_rigid_aligned.nii.gz"]}",')
    print(f'  "template_mri_path":  "{outputs["template_in_subject_rigid_aligned.nii.gz"]}",')


if __name__ == "__main__":
    main()
