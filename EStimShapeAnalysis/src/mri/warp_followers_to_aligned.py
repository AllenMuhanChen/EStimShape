"""
Carry an arbitrary NMT-template-space volume through the SAME two-step
transform the pipeline already applied to the D99 atlas, without re-running
@animal_warper.

Use this to bring extra template-space datasets — e.g.
NMT_v2.0_asym_segmentation.nii.gz, tissue/probability maps, other ROI
atlases defined on the NMT — into the final rigid-aligned space the
mri_viewer displays, co-registered with subject_rigid_aligned.nii.gz and
atlas_rigid_aligned.nii.gz.

WHY TWO STEPS
-------------
The viewer's atlas (`atlas_rigid_aligned.nii.gz`) was produced by:

  1. @animal_warper: NMT template space --(affine + NONLINEAR warp)-->
     subject native space. This made the `*_in_<subj>.nii.gz` outputs.
  2. run_rigid_align: a pure 6-DOF header rewrite (no resampling) re-posing
     those subject-space volumes to line up with the original template.
     The transform is saved as xfm_RAS.txt.

Any NMT-space input must go through BOTH. An affine-only copy would be wrong
because it skips the nonlinear deformation @animal_warper computed.

HOW (the two transform files)
------------------------------
@animal_warper saves the template<->subject transform as two files in its
output dir. We need the TEMPLATE->SUBJECT (inverse) direction:

  affine : <subj>_composite_linear_to_template_inv.1D
  warp   : <subj>_corrected_shft_WARPINV.nii.gz

3dNwarpApply applies them (warp first, then affine) to put a template-space
source onto the subject grid — exactly how d99_atlas_in_<subj> was made.
Then xfm_RAS.txt does the identical header-only rigid rewrite.

Output: `<name>_rigid_aligned.nii.gz`, drop-in alongside the existing aligned
files.

Usage
-----
    1. Set the path constants below.
    2. python -m src.mri.warp_followers_to_aligned

VERIFY (do this once)
---------------------
Set FOLLOWERS to the ORIGINAL template-space D99 atlas
(D99_atlas_in_NMT_v2.0_asym.nii.gz) with "NN" and run. The resulting
*_rigid_aligned.nii.gz should match the existing atlas_rigid_aligned.nii.gz.
If it does, the transform files + order are right and everything else
(segmentation, etc.) is correct too. If it doesn't, swap the order of the two
-nwarp files (see NWARP_ORDER below).

Prerequisite: AFNI on PATH (3dNwarpApply).
"""

import json
import os
import subprocess
import sys

import nibabel as nib
import numpy as np

from src.mri.run_rigid_align import _rewrite_affine


# ============================================================================
# EDIT THESE PATHS DIRECTLY.
# ============================================================================

# The two @animal_warper transform files, TEMPLATE->SUBJECT (inverse) direction.
# Both already exist in your warper output dir. The affine ends in
# "_inv.1D"; the nonlinear warp ends in "WARPINV.nii.gz".
AFFINE_TEMPLATE_TO_NATIVE = "/home/connorlab/Documents/MRI/45X_MRI/45X_110315_4_1_corrected_warper_native/45X_110315_4_1_corrected_composite_linear_to_template_inv.1D"
WARP_TEMPLATE_TO_NATIVE   = "/home/connorlab/Documents/MRI/45X_MRI/45X_110315_4_1_corrected_warper_native/45X_110315_4_1_corrected_shft_WARPINV.nii.gz"

# 3dNwarpApply applies the -nwarp list right-to-left (rightmost first). To map
# template->subject we want the nonlinear WARPINV applied first, then the
# inverse affine: "<affine> <warp>". If the VERIFY check below comes out
# misaligned, flip this to ("warp", "affine").
NWARP_ORDER = ("affine", "warp")  # or ("warp", "affine")

# Subject native-space anatomy = the master grid. Same SUBJECT_NII
# run_rigid_align used, so followers land on the identical grid as the atlas.
SUBJECT_NII = "/home/connorlab/Documents/MRI/45X_MRI/45X_110315_4_1_corrected_warper_native/45X_110315_4_1_corrected.nii.gz"

# The 6-DOF rigid transform run_rigid_align saved (in its OUTPUT_DIR).
XFM_RAS_TXT = "/home/connorlab/Documents/MRI/45X_MRI/45X_110315_4_1_corrected_warper_native/rigid_aligned/xfm_RAS.txt"

# Template-space volumes to carry over, each with an interpolation mode:
#   "NN"     -> nearest-neighbor: label / segmentation / atlas volumes.
#   "wsinc5" -> high-quality continuous: anatomicals, probability maps.
#   (any 3dNwarpApply -ainterp value: NN, linear, cubic, quintic, wsinc5)
FOLLOWERS = [
    # ("/home/connorlab/Documents/NMT_v2.0_asym/NMT_v2.0_asym/NMT_v2.0_asym_segmentation.nii.gz", "NN"),
    ("/home/connorlab/Documents/NMT_v2.0_asym/NMT_v2.0_asym/NMT_v2.0_asym_SS.nii.gz", "wsinc5"),
]

# Where to write the *_rigid_aligned.nii.gz outputs. None = the same dir as
# XFM_RAS_TXT (alongside the existing aligned files).
OUTPUT_DIR = "/home/connorlab/Documents/MRI/45X_MRI/45X_110315_4_1_corrected_warper_native/rigid_aligned"
# ============================================================================


def _require(prog):
    import shutil
    if shutil.which(prog) is not None:
        return
    for d in (os.path.expanduser("~/abin"), "/usr/local/abin",
              "/opt/abin", "/usr/local/afni"):
        if os.path.isfile(os.path.join(d, prog)):
            os.environ["PATH"] = d + os.pathsep + os.environ.get("PATH", "")
            print(f"  Found AFNI in {d}, prepended to PATH.")
            return
    sys.exit(f"ERROR: {prog} not found on PATH or standard AFNI locations.")


def main():
    _require("3dNwarpApply")

    for label, p in (("AFFINE_TEMPLATE_TO_NATIVE", AFFINE_TEMPLATE_TO_NATIVE),
                     ("WARP_TEMPLATE_TO_NATIVE", WARP_TEMPLATE_TO_NATIVE),
                     ("SUBJECT_NII", SUBJECT_NII),
                     ("XFM_RAS_TXT", XFM_RAS_TXT)):
        if not os.path.isfile(p):
            sys.exit(f"{label} not found: {p}")

    M_ras = np.loadtxt(XFM_RAS_TXT)
    if M_ras.shape != (4, 4):
        sys.exit(f"{XFM_RAS_TXT} is not a 4x4 matrix.")
    M_ras_inv = np.linalg.inv(M_ras)

    out_dir = OUTPUT_DIR or os.path.dirname(XFM_RAS_TXT)
    os.makedirs(out_dir, exist_ok=True)

    pieces = {"affine": AFFINE_TEMPLATE_TO_NATIVE, "warp": WARP_TEMPLATE_TO_NATIVE}
    if set(NWARP_ORDER) != {"affine", "warp"}:
        sys.exit('NWARP_ORDER must be ("affine", "warp") or ("warp", "affine").')
    nwarp = " ".join(pieces[k] for k in NWARP_ORDER)

    print("=== RESOLVED ===")
    print(f"  -nwarp          : {nwarp}")
    print(f"  subject master  : {SUBJECT_NII}")
    print(f"  rigid xfm (RAS) : {XFM_RAS_TXT}")
    print(f"  output dir      : {out_dir}")
    print()

    results = {}
    for src, interp in FOLLOWERS:
        if not os.path.isfile(src):
            sys.exit(f"follower not found: {src}")
        stem = os.path.basename(src)
        for ext in (".nii.gz", ".nii"):
            if stem.endswith(ext):
                stem = stem[: -len(ext)]
                break

        in_subject = os.path.join(out_dir, f"{stem}_in_subject.nii.gz")
        aligned = os.path.join(out_dir, f"{stem}_rigid_aligned.nii.gz")

        # Step 1: NMT template space -> subject native grid (same transforms +
        # master that produced the atlas-in-subject).
        cmd = ["3dNwarpApply", "-overwrite",
               "-ainterp", interp,
               "-nwarp", nwarp,
               "-source", src,
               "-master", SUBJECT_NII,
               "-prefix", in_subject]
        print(f"[warp] {os.path.basename(src)}  (ainterp={interp})")
        print("  " + " ".join(cmd))
        if subprocess.run(cmd, check=False).returncode != 0:
            sys.exit("3dNwarpApply failed.")

        # Step 2: identical 6-DOF header rewrite as run_rigid_align (no resample).
        _rewrite_affine(in_subject, aligned, M_ras_inv)
        print(f"  -> {aligned}\n")
        results[src] = {"interp": interp,
                        "in_subject": in_subject,
                        "rigid_aligned": aligned}

    summary = {
        "affine_template_to_native": AFFINE_TEMPLATE_TO_NATIVE,
        "warp_template_to_native": WARP_TEMPLATE_TO_NATIVE,
        "nwarp_order": list(NWARP_ORDER),
        "subject_master": SUBJECT_NII,
        "xfm_RAS_txt": XFM_RAS_TXT,
        "followers": results,
    }
    with open(os.path.join(out_dir, "warp_followers.json"), "w") as f:
        json.dump(summary, f, indent=2)

    print("Done. Load any *_rigid_aligned.nii.gz in mri_viewer alongside")
    print("subject_rigid_aligned.nii.gz / atlas_rigid_aligned.nii.gz.")
    print("VERIFY once: warp the original template-space D99 atlas with 'NN'")
    print("and confirm it matches atlas_rigid_aligned.nii.gz. If misaligned,")
    print("flip NWARP_ORDER at the top of this file and re-run.")


if __name__ == "__main__":
    main()
