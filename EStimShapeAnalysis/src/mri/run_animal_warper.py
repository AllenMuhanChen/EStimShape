"""
Drive AFNI's @animal_warper to register a subject PAR/REC MRI to the NMT v2.0
sym template, producing an atlas + template warped into the subject's
corrected-world space (matching the mri_viewer display).

Usage
-----
    python -m src.mri.run_animal_warper

No command-line arguments. Everything is read from `mri_viewer_config.json`
in the current working directory:

    default_path       -> subject PAR/REC to warp
    template_mri_path  -> @animal_warper -base (e.g. NMT_v2.0_sym.nii.gz)
    atlas_nifti_path   -> @animal_warper -atlas_followers (e.g. D99 atlas)

By default, if `<par>_corrections.json` exists with a non-identity matrix,
that subject correction is composed into the NIfTI affine before warping so
the warped atlas/template land directly in the viewer's corrected-world
space. Flip the module-level `USE_SUBJECT_CORRECTION` constant to False to
skip this and warp from native scanner space instead (useful if the
pre-correction seems to be biasing the warp).

If `RIGID_POSE_MATCH_TO_TEMPLATE` is True (default), a final step computes a
6-DOF rigid transform (rotation + translation only — no scale, no shear)
from the subject to the template via `3dAllineate -warp shift_rotate`, then
applies it as a header-only affine update to the subject NIfTI and the
atlas-in-subject NIfTI. Voxel data is unchanged so subject morphology and
voxel grid are preserved exactly (important for electrode targeting). The
original template can then be loaded as-is in the viewer.

Outputs are tagged with the space used so different parameterizations don't
collide, and the script refuses to overwrite existing results:

    <par>_warper_<space>/                       — @animal_warper working dir
    <par>_warper_<space>/subject_pose_matched.nii.gz   — pose-matched subject
    <par>_warper_<space>/atlas_pose_matched.nii.gz     — pose-matched atlas
    <par>_warper_<space>/rigid_xfm_RAS.txt             — 4x4 rigid transform
    <par>_warper_<space>.json                          — sidecar JSON

where <space> is "corrected" or "native".

Prerequisite: AFNI installed and on PATH. Quick install on Linux:

    cd /tmp
    curl -fL -o setup.tcsh https://afni.nimh.nih.gov/pub/dist/bin/misc/@update.afni.binaries
    tcsh setup.tcsh -package linux_ubuntu_24_64 -do_extras
    # add ~/abin to PATH, restart shell, verify with: @animal_warper -help

Runtime: typically 30-60 min per subject on a workstation.
"""

import glob
import json
import os
import shutil
import subprocess
import sys
import time

import nibabel as nib
import numpy as np

from src.mri.correction import load_corrections


CONFIG_PATH = os.path.join(os.getcwd(), "mri_viewer_config.json")

# Flip this to False to warp from native scanner space instead of composing
# in the subject correction matrix from <par>_corrections.json. Useful for
# debugging when the pre-correction seems to be biasing the warp.
USE_SUBJECT_CORRECTION = False

# After @animal_warper finishes, compute a 6-DOF rigid (rotation + translation
# only — no scale, no shear) transform from the subject MRI to the template
# via 3dAllineate, and apply it as a header-only affine update to both the
# subject NIfTI and the atlas-in-subject NIfTI. Voxel data is unchanged so
# subject morphology and voxel grid (the targeting space for the electrode)
# are preserved exactly. The pose-matched files are written into the warper
# outdir as subject_pose_matched.nii.gz and atlas_pose_matched.nii.gz, and
# the original template can then be loaded as-is in the viewer.
RIGID_POSE_MATCH_TO_TEMPLATE = True


def _require_afni():
    """Locate @animal_warper. If not on PATH (common under conda envs which
    rebuild PATH on activation), look in standard AFNI install locations and
    prepend the directory to os.environ['PATH'] so subprocess calls inherit it.
    """
    if shutil.which("@animal_warper") is not None:
        return
    candidates = [
        os.path.expanduser("~/abin"),
        "/usr/local/abin",
        "/opt/abin",
        "/usr/local/afni",
    ]
    for d in candidates:
        if os.path.isfile(os.path.join(d, "@animal_warper")):
            os.environ["PATH"] = d + os.pathsep + os.environ.get("PATH", "")
            print(f"  Found AFNI in {d}, prepended to PATH for subprocesses.")
            return
    sys.exit(
        "ERROR: '@animal_warper' not found on PATH or in standard locations "
        f"({', '.join(candidates)}). Install AFNI first "
        "(see header docstring of this file)."
    )


def par_to_nifti(par_path, out_nii, correction=None):
    """Convert PAR/REC to a single-volume NIfTI.

    If `correction` (4x4) is provided, it is composed with the PAR's native
    affine so the NIfTI lives in corrected-world coordinates (matching the
    viewer's display space). Otherwise the native scanner affine is used.

    If the PAR has multiple dynamics (4D), average across them — @animal_warper
    expects a single 3-D volume.
    """
    from nibabel.parrec import load as load_parrec

    img = load_parrec(par_path, strict_sort=True)
    data = img.get_fdata()
    affine = img.affine.copy()
    if correction is not None:
        affine = correction @ affine

    if data.ndim == 4:
        if data.shape[3] > 1:
            print(f"  PAR has {data.shape[3]} dynamics — averaging to 3-D for warper.")
        data = data.mean(axis=3)

    nii = nib.Nifti1Image(data.astype(np.float32), affine)
    nib.save(nii, out_nii)
    return out_nii


def run_animal_warper(subj_nii, base_nii, atlas_nii, outdir, subj_id):
    cmd = [
        "@animal_warper",
        "-input", subj_nii,
        "-base", base_nii,
        "-atlas_followers", atlas_nii,
        "-outdir", outdir,
        "-input_abbrev", subj_id,
    ]
    print("Running:")
    print("  " + " ".join(cmd))
    t0 = time.time()
    proc = subprocess.run(cmd, check=False)
    dt = time.time() - t0
    print(f"@animal_warper exited with code {proc.returncode} after {dt/60:.1f} min")
    if proc.returncode != 0:
        sys.exit(proc.returncode)


def _load_afni_aff12(path):
    """Parse 3dAllineate's -1Dmatrix_save output (one line of 12 numbers in
    row-major order) into a 4x4 matrix. AFNI's coordinate convention is RAI
    (DICOM); caller must convert to RAS for use with NIfTI affines.
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
    """Convert a 4x4 AFNI-RAI affine to NIfTI-RAS by flipping the z axis."""
    F = np.diag([1.0, 1.0, -1.0, 1.0])
    return F @ M @ F


def rigid_pose_match(subj_nii, template_nii, atlas_in_subj_nii,
                     work_dir, out_dir):
    """Run 3dAllineate to compute a 6-DOF rigid transform subject -> template,
    then header-rewrite the subject NIfTI and atlas-in-subject NIfTI so they
    live in template-aligned pose with zero voxel resampling.

    3dAllineate's `-1Dmatrix_save` writes M such that source_RAI = M @ base_RAI.
    To move the subject into the base's pose without resampling, we
    pre-multiply the subject's affine by the inverse: new_affine_RAS =
    inv(M_RAS) @ old_affine_RAS. The same transform applied to the atlas
    keeps it aligned with the subject.

    Returns (pose_subj_path, pose_atlas_path_or_None, M_ras).
    """
    xfm_dir = os.path.join(work_dir, "rigid_pose")
    os.makedirs(xfm_dir, exist_ok=True)
    xfm_path = os.path.join(xfm_dir, "xfm.aff12.1D")
    throwaway = os.path.join(xfm_dir, "rigid_resampled.nii.gz")

    cmd = [
        "3dAllineate",
        "-source", subj_nii,
        "-base", template_nii,
        "-warp", "shift_rotate",
        "-cost", "lpa",
        "-1Dmatrix_save", xfm_path,
        "-final", "NN",
        "-prefix", throwaway,
        "-overwrite",
    ]
    print("Running:")
    print("  " + " ".join(cmd))
    t0 = time.time()
    proc = subprocess.run(cmd, check=False)
    dt = time.time() - t0
    print(f"3dAllineate (rigid) exited with code {proc.returncode} after {dt/60:.1f} min")
    if proc.returncode != 0:
        sys.exit(proc.returncode)

    M_rai = _load_afni_aff12(xfm_path)
    M_ras = _rai_to_ras(M_rai)
    M_ras_inv = np.linalg.inv(M_ras)

    np.savetxt(
        os.path.join(out_dir, "rigid_xfm_RAS.txt"), M_ras,
        header=("6-DOF rigid transform (RAS, NIfTI convention).\n"
                "source_RAS = M_ras @ base_RAS.\n"
                "Subject pose-matched affine = inv(M_ras) @ old_affine."),
    )

    def _rewrite_affine(in_path, out_path):
        img = nib.load(in_path)
        new_affine = M_ras_inv @ img.affine
        data = np.asanyarray(img.dataobj)
        new_img = nib.Nifti1Image(data, new_affine, header=img.header)
        qcode = img.header.get_qform(coded=True)[1] or 1
        scode = img.header.get_sform(coded=True)[1] or 1
        new_img.set_qform(new_affine, code=qcode)
        new_img.set_sform(new_affine, code=scode)
        nib.save(new_img, out_path)

    pose_subj = os.path.join(out_dir, "subject_pose_matched.nii.gz")
    _rewrite_affine(subj_nii, pose_subj)

    pose_atlas = None
    if atlas_in_subj_nii and os.path.exists(atlas_in_subj_nii):
        pose_atlas = os.path.join(out_dir, "atlas_pose_matched.nii.gz")
        _rewrite_affine(atlas_in_subj_nii, pose_atlas)

    return pose_subj, pose_atlas, M_ras


def find_outputs(outdir, subj_id, atlas_nii):
    """Locate the atlas-in-subject and template-in-subject NIfTIs produced by
    @animal_warper. Layout varies between AFNI versions, so we glob.
    """
    atlas_base = os.path.basename(atlas_nii)
    for ext in (".nii.gz", ".nii"):
        if atlas_base.endswith(ext):
            atlas_base = atlas_base[: -len(ext)]
            break

    atlas_candidates = (
        glob.glob(os.path.join(outdir, f"*{atlas_base}*in*{subj_id}*.nii*"))
        + glob.glob(os.path.join(outdir, f"*{subj_id}*{atlas_base}*.nii*"))
        + glob.glob(os.path.join(outdir, "follow_ROI_*", f"*{atlas_base}*.nii*"))
    )
    template_candidates = (
        glob.glob(os.path.join(outdir, f"*NMT*in*{subj_id}*.nii*"))
        + glob.glob(os.path.join(outdir, f"*{subj_id}*NMT*.nii*"))
        + glob.glob(os.path.join(outdir, f"{subj_id}*aw_*.nii*"))
    )

    def pick(cands, label):
        cands = [c for c in cands if "warp" not in os.path.basename(c).lower()]
        if not cands:
            print(f"  WARN: could not auto-detect {label} output in {outdir}")
            return None
        cands.sort(key=lambda p: len(p))
        return cands[0]

    return (pick(atlas_candidates, "atlas-in-subject"),
            pick(template_candidates, "template-in-subject"))


def main():
    import os, shutil
    print("PATH:", os.environ.get("PATH"))
    print("which @animal_warper:", shutil.which("@animal_warper"))

    if not os.path.exists(CONFIG_PATH):
        sys.exit(f"Config not found: {CONFIG_PATH}\n"
                 f"Run from the directory containing mri_viewer_config.json.")
    with open(CONFIG_PATH) as f:
        cfg = json.load(f)

    par_path = cfg.get("default_path")
    template = cfg.get("template_mri_path")
    atlas = cfg.get("atlas_nifti_path")

    missing = [k for k, v in (("default_path", par_path),
                              ("template_mri_path", template),
                              ("atlas_nifti_path", atlas)) if not v]
    if missing:
        sys.exit(f"Missing keys in {CONFIG_PATH}: {', '.join(missing)}")
    for label, p in (("PAR", par_path), ("template", template), ("atlas", atlas)):
        if not os.path.isfile(p):
            sys.exit(f"{label} file does not exist: {p}")

    rec_stem = os.path.splitext(par_path)[0]
    if not (os.path.exists(rec_stem + ".REC") or os.path.exists(rec_stem + ".rec")):
        sys.exit(f"REC file not found alongside {par_path}")

    # Resolve subject correction up front so we can include the resulting
    # space tag in the output directory / sidecar names. That way runs with
    # and without correction can coexist without overwriting each other.
    subj_corr = None
    corr_json = rec_stem + "_corrections.json"
    if not USE_SUBJECT_CORRECTION:
        print("  USE_SUBJECT_CORRECTION=False — skipping subject correction, using native affine.")
    elif os.path.exists(corr_json):
        subj_corr, _ = load_corrections(corr_json)
        if np.allclose(subj_corr, np.eye(4)):
            subj_corr = None
            print("  Subject correction is identity — using native affine.")
        else:
            print(f"  Applying subject correction from {os.path.basename(corr_json)} "
                  "so the NIfTI lives in corrected-world space.")
    else:
        print(f"  No {os.path.basename(corr_json)} found — using native affine.")

    space_tag = "corrected" if subj_corr is not None else "native"

    subj_id = os.path.basename(rec_stem)
    outdir = rec_stem + f"_warper_{space_tag}"
    summary_path = rec_stem + f"_warper_{space_tag}.json"

    # Never overwrite a previous run — refuse if either the output directory
    # (non-empty) or the sidecar JSON already exists. User must move/delete
    # them explicitly to re-run with the same parameters.
    existing = []
    if os.path.isdir(outdir) and os.listdir(outdir):
        existing.append(outdir)
    if os.path.exists(summary_path):
        existing.append(summary_path)
    if existing:
        sys.exit(
            "ERROR: refusing to overwrite existing outputs:\n  "
            + "\n  ".join(existing)
            + "\nMove or delete them, or re-run with different parameters."
        )
    # @animal_warper is a tcsh script and breaks on spaces in any path it
    # processes ("set: Variable name must contain alphanumeric characters.").
    # If the natural outdir contains a space, work under ~/aw_work/<subj_id>/
    # instead and copy outputs back at the end.
    safe_subj_id = subj_id.replace(" ", "_")
    needs_staging = (" " in outdir or " " in par_path
                     or " " in template or " " in atlas)
    if needs_staging:
        work_root = os.path.expanduser(f"~/aw_work/{safe_subj_id}_{space_tag}")
        work_outdir = os.path.join(work_root, "out")
        work_inputs = os.path.join(work_root, "inputs")
        print(f"  Spaces detected in input/output paths — staging in {work_root} "
              "to avoid tcsh parsing issues.")
    else:
        work_outdir = outdir
        work_inputs = outdir  # subject NIfTI gets written here
    # Clear any stale outputs from a previous failed run — AFNI bails on
    # existing-file conflicts ("output dataset name conflicts with existing
    # file"). We deliberately keep work_inputs across runs to allow reuse,
    # but always start work_outdir fresh.
    if os.path.isdir(work_outdir) and needs_staging:
        shutil.rmtree(work_outdir)
    os.makedirs(work_outdir, exist_ok=True)
    os.makedirs(work_inputs, exist_ok=True)
    os.makedirs(outdir, exist_ok=True)

    _require_afni()

    # Symlink template + atlas into the inputs subdir under clean names so
    # @animal_warper never sees a path with a space. The inputs subdir is
    # separate from work_outdir so our symlinks can't collide with AFNI's
    # output dataset names.
    def _stage(src, name):
        ext = ".nii.gz" if src.endswith(".gz") else ".nii"
        dst = os.path.join(work_inputs, name + ext)
        if os.path.lexists(dst):
            os.remove(dst)
        os.symlink(os.path.abspath(src), dst)
        return dst

    if needs_staging:
        template = _stage(template, "nmt_template")
        atlas = _stage(atlas, "d99_atlas")

    n_steps = 4 if RIGID_POSE_MATCH_TO_TEMPLATE else 3

    # 1. Convert PAR/REC to NIfTI, composing in the subject correction
    # resolved above if applicable.
    subj_nii = os.path.join(work_inputs, f"{safe_subj_id}_{space_tag}.nii.gz")
    print(f"[1/{n_steps}] Converting PAR/REC -> {subj_nii}")
    par_to_nifti(par_path, subj_nii, correction=subj_corr)

    # 2. @animal_warper.
    print(f"[2/{n_steps}] Running @animal_warper (template={os.path.basename(template)}, "
          f"atlas={os.path.basename(atlas)})")
    run_animal_warper(subj_nii, template, atlas, work_outdir, safe_subj_id)

    # If we staged in a separate work dir, mirror the contents back to the
    # user-facing outdir next to the PAR file.
    if work_outdir != outdir:
        print(f"  Copying outputs from {work_outdir} -> {outdir}")
        for name in os.listdir(work_outdir):
            src = os.path.join(work_outdir, name)
            dst = os.path.join(outdir, name)
            if os.path.islink(src):
                continue  # skip our input symlinks
            if os.path.isdir(src):
                if os.path.isdir(dst):
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)

    # 3. Locate the warped outputs.
    print(f"[3/{n_steps}] Locating outputs in {outdir}")
    warped_atlas, warped_template = find_outputs(outdir, safe_subj_id, atlas)

    # 4. Optional rigid pose-match to template (6-DOF, header-only).
    pose_subj = None
    pose_atlas = None
    if RIGID_POSE_MATCH_TO_TEMPLATE:
        print(f"[4/{n_steps}] Rigid pose-match (6-DOF) subject -> template")
        pose_subj, pose_atlas, _ = rigid_pose_match(
            subj_nii=subj_nii,
            template_nii=template,
            atlas_in_subj_nii=warped_atlas,
            work_dir=work_outdir,
            out_dir=outdir,
        )
        print(f"  Pose-matched subject: {pose_subj}")
        if pose_atlas:
            print(f"  Pose-matched atlas:   {pose_atlas}")

    summary = {
        "par_file": par_path,
        "subj_id": safe_subj_id,
        "outdir": outdir,
        "work_outdir": work_outdir if work_outdir != outdir else None,
        "source_template": template,
        "source_atlas": atlas,
        "subject_space": space_tag,
        "warped_template_in_subject": warped_template,
        "warped_atlas_in_subject": warped_atlas,
        "rigid_pose_matched": RIGID_POSE_MATCH_TO_TEMPLATE,
        "pose_matched_subject": pose_subj,
        "pose_matched_atlas": pose_atlas,
    }
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"Wrote summary -> {summary_path}")

    print()
    print("Done. To use in mri_viewer, update mri_viewer_config.json:")
    if RIGID_POSE_MATCH_TO_TEMPLATE and pose_subj:
        print(f'  "default_path":       "{pose_subj}",')
        if pose_atlas:
            print(f'  "atlas_nifti_path":   "{pose_atlas}",')
        print(f'  "template_mri_path":  "{cfg.get("template_mri_path")}",')
        print("Reset atlas_correction to identity. Subject and atlas have "
              "been rigidly pose-matched to the template (rotation + "
              "translation only, no scale/shear, voxel data unchanged) so "
              "the template can be loaded as-is and everything overlays.")
    else:
        if warped_atlas:
            print(f'  "atlas_nifti_path":   "{warped_atlas}",')
        if warped_template:
            print(f'  "template_mri_path":  "{warped_template}",')
        if subj_corr is not None:
            print("Reset atlas_correction to identity in the viewer — the warp "
                  "aligned to your AC/PC-corrected MRI space, so display lines "
                  "up automatically.")
        else:
            print("The NIfTI was warped in native scanner space. If you use a "
                  "subject correction matrix in the viewer, set atlas_correction "
                  "to that same matrix; otherwise leave it at identity.")


if __name__ == "__main__":
    main()
