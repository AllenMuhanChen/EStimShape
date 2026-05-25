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

  1. @animal_warper: NMT template space --(12-DOF affine + NONLINEAR warp)-->
     subject native space. This is the `*_in_<subj>.nii.gz` outputs.
  2. run_rigid_align: a pure 6-DOF header rewrite (no resampling) re-posing
     those subject-space volumes to line up with the original template.
     The transform is saved as xfm_RAS.txt.

Any NMT-space input must go through BOTH. An affine-only copy would be wrong
because it skips the nonlinear deformation @animal_warper computed. This
script:

  * locates @animal_warper's saved template->native nonlinear warp
    (`*_base2osh_WARP.nii.gz`, the exact warp that made the atlas-in-subject),
  * 3dNwarpApply's it onto the subject grid (NN for label volumes, wsinc5 for
    continuous), reproducing the `*_in_<subj>` step, then
  * reuses xfm_RAS.txt to apply the identical header-only rigid rewrite.

Output: `<name>_rigid_aligned.nii.gz`, drop-in alongside the existing aligned
files.

Usage
-----
    1. Set the path constants below: the @animal_warper template->native warp
       (or its outdir), the subject master grid, run_rigid_align's xfm_RAS.txt,
       and your follower files + interpolation.
    2. python -m src.mri.warp_followers_to_aligned

VERIFY (recommended)
--------------------
Because the no-re-run path depends on globbing @animal_warper's internal warp
filenames (which vary by AFNI version), sanity-check once: add the ORIGINAL
D99 atlas (the template-space `D99_atlas_in_NMT_v2.0_asym.nii.gz`) as a
follower with "NN". The result should match the existing
`atlas_rigid_aligned.nii.gz` voxel-for-voxel. If it does, the discovered warp
+ master grid are correct and you can trust the other followers.

Prerequisite: AFNI on PATH (3dNwarpApply, 3dNwarpCat).
"""

import glob
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

# @animal_warper's saved template->native nonlinear warp — the exact warp that
# produced the `*_in_<subj>` atlas. It's usually buried in the warper outdir as
# `*_base2osh_WARP.nii.gz`. Set the file directly if you know it. Otherwise
# leave this None and set WARPER_OUTDIR below; the script will find (or
# reconstruct) it from that directory.
WARP_TEMPLATE_TO_NATIVE = None

# @animal_warper output directory. Only used to auto-locate the warp above when
# WARP_TEMPLATE_TO_NATIVE is None. Set to None if you set the warp explicitly.
WARPER_OUTDIR = "/home/connorlab/Documents/MRI/45X_MRI/45X_110315_4_1_corrected_warper_native"

# Subject native-space anatomy = the master grid. This is the SAME SUBJECT_NII
# run_rigid_align used, so followers land on the identical grid as the atlas.
SUBJECT_NII = "/home/connorlab/Documents/MRI/45X_MRI/45X_110315_4_1_corrected_warper_native/45X_110315_4_1_corrected.nii.gz"

# The 6-DOF rigid transform run_rigid_align saved (in its OUTPUT_DIR).
XFM_RAS_TXT = "/home/connorlab/Documents/MRI/45X_MRI/45X_110315_4_1_corrected_warper_native/rigid_aligned/xfm_RAS.txt"

# Template-space volumes to carry over, each with an interpolation mode:
#   "NN"     -> nearest-neighbor: label / segmentation / atlas volumes.
#   "wsinc5" -> high-quality continuous: anatomicals, probability maps.
#   (any 3dNwarpApply -ainterp value: NN, linear, cubic, quintic, wsinc5)
FOLLOWERS = [
    ("/home/connorlab/Documents/NMT_v2.0_asym/NMT_v2.0_asym/NMT_v2.0_asym_segmentation.nii.gz", "NN"),
    # ("/path/to/another_template_space_map.nii.gz", "wsinc5"),
]

# Where to write the *_rigid_aligned.nii.gz outputs. None = the same dir as
# XFM_RAS_TXT (alongside the existing aligned files).
OUTPUT_DIR = None
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


def _find_template_to_native_warp(outdir):
    """Locate @animal_warper's catenated template->native nonlinear warp.

    This is the same warp that produced the `*_in_<subj>` atlas. AFNI writes it
    under an intermediate subdir, so search recursively. Returns the path, or
    None if not found.
    """
    cands = glob.glob(os.path.join(outdir, "**", "*base2osh_WARP.nii*"),
                      recursive=True)
    cands = sorted(set(cands), key=len)
    return cands[0] if cands else None


def _build_template_to_native_warp(outdir, work_prefix):
    """Fallback: reconstruct the template->native warp from the affine +
    nonlinear pieces, mirroring @animal_warper's own 3dNwarpCat:

        3dNwarpCat -iwarp -warp2 <..._al2std_mat.aff12.1D>
                          -warp1 <..._WARP.nii.gz>
                          -prefix <out>

    Returns the path to the newly written warp, or None if pieces are missing.
    """
    aff = sorted(glob.glob(os.path.join(outdir, "**", "*al2std_mat.aff12.1D"),
                           recursive=True), key=len)
    warp = sorted(glob.glob(os.path.join(outdir, "**", "*_WARP.nii*"),
                            recursive=True), key=len)
    # Exclude already-catenated base2osh/osh2base from the incremental warp pick.
    warp = [w for w in warp if "base2osh" not in os.path.basename(w)
            and "osh2base" not in os.path.basename(w)]
    if not aff or not warp:
        return None
    out = work_prefix + "_base2osh_WARP.nii.gz"
    cmd = ["3dNwarpCat", "-overwrite", "-iwarp",
           "-warp2", aff[0], "-warp1", warp[0], "-prefix", out]
    print("  Reconstructing template->native warp:")
    print("    " + " ".join(cmd))
    if subprocess.run(cmd, check=False).returncode != 0:
        sys.exit("3dNwarpCat failed reconstructing the warp.")
    return out


def main():
    _require("3dNwarpApply")
    _require("3dNwarpCat")

    if not os.path.isfile(SUBJECT_NII):
        sys.exit(f"SUBJECT_NII not found: {SUBJECT_NII}")
    if not os.path.isfile(XFM_RAS_TXT):
        sys.exit(f"XFM_RAS_TXT not found: {XFM_RAS_TXT}")
    M_ras = np.loadtxt(XFM_RAS_TXT)
    if M_ras.shape != (4, 4):
        sys.exit(f"{XFM_RAS_TXT} is not a 4x4 matrix.")
    M_ras_inv = np.linalg.inv(M_ras)

    out_dir = OUTPUT_DIR or os.path.dirname(XFM_RAS_TXT)
    os.makedirs(out_dir, exist_ok=True)

    # Resolve the template->native warp: explicit path wins; else find or
    # reconstruct it from WARPER_OUTDIR.
    warp = WARP_TEMPLATE_TO_NATIVE
    if warp is not None:
        if not os.path.isfile(warp):
            sys.exit(f"WARP_TEMPLATE_TO_NATIVE not found: {warp}")
    else:
        if not WARPER_OUTDIR or not os.path.isdir(WARPER_OUTDIR):
            sys.exit("Set WARP_TEMPLATE_TO_NATIVE to the *_base2osh_WARP.nii.gz "
                     "file, or set WARPER_OUTDIR to the @animal_warper output "
                     "directory so it can be found.")
        warp = _find_template_to_native_warp(WARPER_OUTDIR)
        if warp is None:
            print("  No *_base2osh_WARP found — reconstructing from affine + warp.")
            warp = _build_template_to_native_warp(
                WARPER_OUTDIR, os.path.join(out_dir, "_recat"))
        if warp is None:
            sys.exit(
                "ERROR: could not find or reconstruct the template->native warp in\n"
                f"  {WARPER_OUTDIR}\n"
                "Expected '*_base2osh_WARP.nii.gz' (or an affine '*al2std_mat.aff12.1D'\n"
                "plus incremental '*_WARP.nii.gz' to reconstruct from). List that dir\n"
                "and set WARP_TEMPLATE_TO_NATIVE directly.")

    print("=== RESOLVED ===")
    print(f"  template->native: {warp}")
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

        # Step 1: NMT template space -> subject native grid (same warp + master
        # that produced the atlas-in-subject).
        cmd = ["3dNwarpApply", "-overwrite",
               "-ainterp", interp,
               "-nwarp", warp,
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
        "template_to_native_warp": warp,
        "subject_master": SUBJECT_NII,
        "xfm_RAS_txt": XFM_RAS_TXT,
        "followers": results,
    }
    with open(os.path.join(out_dir, "warp_followers.json"), "w") as f:
        json.dump(summary, f, indent=2)

    print("Done. Load any *_rigid_aligned.nii.gz in mri_viewer alongside")
    print("subject_rigid_aligned.nii.gz / atlas_rigid_aligned.nii.gz.")
    print("VERIFY: warp the original D99 atlas through this script with 'NN'")
    print("and confirm it matches atlas_rigid_aligned.nii.gz.")


if __name__ == "__main__":
    main()
