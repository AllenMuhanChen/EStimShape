"""
Drive AFNI's @animal_warper to register a subject MRI to the NMT v2.0
sym template, producing an atlas + template warped into the subject's
corrected-world space (matching the mri_viewer display).

Usage
-----
    python -m src.mri.run_animal_warper

No command-line arguments. Set the SUBJECT_MRI / TEMPLATE_MRI / ATLAS_MRI /
OUTPUT_DIR / STAGING_ROOT / USE_SUBJECT_CORRECTION constants directly in
this file (see the EDIT THESE PATHS DIRECTLY block below). Any constant
left at None falls back to the corresponding key in `mri_viewer_config.json`
in the current working directory:

    SUBJECT_MRI  <- cfg["default_path"]        (PAR/REC or .nii/.nii.gz)
    TEMPLATE_MRI <- cfg["template_mri_path"]   (e.g. NMT_v2.0_sym.nii.gz)
    ATLAS_MRI    <- cfg["atlas_nifti_path"]    (e.g. D99 atlas)

The script prints every resolved path (and the resolved targets of any
staged symlinks) before running so you can verify what's actually being
fed to @animal_warper.

If USE_SUBJECT_CORRECTION is True and `<subject_stem>_corrections.json`
exists with a non-identity matrix, that subject correction is composed
into the NIfTI affine before warping so the warped atlas/template land
in the viewer's corrected-world space. Setting it to False skips that
step. If your subject MRI is already a .nii.gz with corrections baked in
(via the viewer's "Save Corrected as NIfTI" button), leave it at True —
the script will simply not find a sidecar and treat the input as-is.

Outputs are tagged with the space used so different parameterizations
don't collide, and the script refuses to overwrite existing results:

    <subject_stem>_warper_<space>/      — @animal_warper working directory
    <subject_stem>_warper_<space>.json  — sidecar listing warped output paths

where <space> is "corrected" or "native". Override the outdir entirely by
setting the OUTPUT_DIR constant below.

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

# ============================================================================
# EDIT THESE PATHS DIRECTLY.
#
# Set absolute paths so you know exactly what's being fed to @animal_warper.
# Leave any value as None to fall back to mri_viewer_config.json (legacy
# behavior). The script will print every resolved path before running so you
# can double-check.
# ============================================================================

# Subject MRI. PAR/REC or .nii(.gz). Falls back to cfg["default_path"].
SUBJECT_MRI  = "/home/connorlab/Documents/MRI/Bixby/bixby_WIP_MPrageAX_.70mm_New_corrected.nii.gz"
# Reference template (e.g. NMT_v2.0_sym.nii.gz). Falls back to cfg["template_mri_path"].
TEMPLATE_MRI = "/home/connorlab/Documents/NMT_v2.0_asym/NMT_v2.0_asym/NMT_v2.0_asym.nii.gz"
# Atlas to follow (e.g. D99_atlas_in_NMT_v2.0_sym.nii.gz). Falls back to cfg["atlas_nifti_path"].
ATLAS_MRI    = "/home/connorlab/Documents/NMT_v2.0_asym/NMT_v2.0_asym/D99_atlas_in_NMT_v2.0_asym.nii.gz"

# Brain mask in template space (e.g. NMT_v2.0_asym_brainmask.nii.gz). When set,
# passed to @animal_warper as -skullstrip so it warps the template brainmask
# onto the subject instead of running generic 3dSkullStrip. Strongly preferred
# for monkey MRI. None = let @animal_warper run its default skull-stripping.
BRAIN_MASK   = "/home/connorlab/Documents/NMT_v2.0_asym/NMT_v2.0_asym/NMT_v2.0_asym_brainmask.nii.gz"

# Where to put the @animal_warper outdir. None = <subject_stem>_warper_<space>
# next to the subject MRI.
OUTPUT_DIR   = None

# @animal_warper is a tcsh script that breaks on spaces in any input path.
# When any input path contains a space we stage everything under STAGING_ROOT
# (with symlinks for template/atlas and a fresh-written subject NIfTI), run
# AFNI there, and copy outputs back. None = ~/aw_work/<subject_id>_<space>/.
# Set to a no-space absolute path of your choice if you want to control it.
STAGING_ROOT = None

# Apply <subject_stem>_corrections.json sidecar to the subject affine before
# warping. If the input is a NIfTI that already has corrections baked into
# its affine, you probably want this False (or just no sidecar present).
USE_SUBJECT_CORRECTION = False
# ============================================================================


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


def _is_nifti(path):
    p = path.lower()
    return p.endswith(".nii") or p.endswith(".nii.gz")


def subject_to_nifti(in_path, out_nii, correction=None):
    """Convert subject MRI (PAR/REC or NIfTI) to a single-volume NIfTI.

    If `correction` (4x4) is provided, it is composed with the input's
    native affine so the output lives in corrected-world coordinates
    (matching the viewer's display space). Otherwise the input affine is
    used as-is.

    For 4D inputs (PAR with multiple dynamics), the volumes are averaged —
    @animal_warper expects a single 3-D volume.
    """
    if _is_nifti(in_path):
        img = nib.load(in_path)
    else:
        from nibabel.parrec import load as load_parrec
        img = load_parrec(in_path, strict_sort=True)

    data = img.get_fdata()
    affine = img.affine.copy()
    if correction is not None:
        affine = correction @ affine

    if data.ndim == 4:
        if data.shape[3] > 1:
            print(f"  Input has {data.shape[3]} dynamics — averaging to 3-D for warper.")
        data = data.mean(axis=3)

    nii = nib.Nifti1Image(data.astype(np.float32), affine)
    nib.save(nii, out_nii)
    return out_nii


def run_animal_warper(subj_nii, base_nii, atlas_nii, outdir, subj_id,
                      brain_mask=None):
    cmd = [
        "@animal_warper",
        "-input", subj_nii,
        "-base", base_nii,
        "-atlas_followers", atlas_nii,
        "-outdir", outdir,
        "-input_abbrev", subj_id,
        "-ok_to_exist"
    ]
    if brain_mask:
        cmd += ["-skullstrip", brain_mask]
    print("Running:")
    print("  " + " ".join(cmd))
    t0 = time.time()
    proc = subprocess.run(cmd, check=False)
    dt = time.time() - t0
    print(f"@animal_warper exited with code {proc.returncode} after {dt/60:.1f} min")
    if proc.returncode != 0:
        sys.exit(proc.returncode)


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
        glob.glob(os.path.join(outdir, f"BASEORIG*in*{subj_id}*.nii*"))
        + glob.glob(os.path.join(outdir, f"*NMT*in*{subj_id}*.nii*"))
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

    # Load config if it exists so the constants can fall back to it for any
    # unset values. If it doesn't exist and any required constant is unset,
    # we error out below.
    cfg = {}
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            cfg = json.load(f)

    subj_path  = SUBJECT_MRI  or cfg.get("default_path")
    template   = TEMPLATE_MRI or cfg.get("template_mri_path")
    atlas      = ATLAS_MRI    or cfg.get("atlas_nifti_path")
    brain_mask = BRAIN_MASK   or cfg.get("brain_mask_path")

    print()
    print("=== INPUTS ===")
    def _src(override, cfg_val, label):
        if override is not None:
            return "constant"
        if cfg_val is not None:
            return f"{label} (config)"
        return "MISSING"
    print(f"  subject    : {subj_path}   [{_src(SUBJECT_MRI, cfg.get('default_path'), 'default_path')}]")
    print(f"  template   : {template}   [{_src(TEMPLATE_MRI, cfg.get('template_mri_path'), 'template_mri_path')}]")
    print(f"  atlas      : {atlas}   [{_src(ATLAS_MRI, cfg.get('atlas_nifti_path'), 'atlas_nifti_path')}]")
    print(f"  brain mask : {brain_mask}   [{_src(BRAIN_MASK, cfg.get('brain_mask_path'), 'brain_mask_path')}]")
    print()

    missing = [k for k, v in (("SUBJECT_MRI", subj_path),
                              ("TEMPLATE_MRI", template),
                              ("ATLAS_MRI", atlas)) if not v]
    if missing:
        sys.exit(f"Missing required paths: {', '.join(missing)}")
    for label, p in (("subject", subj_path), ("template", template), ("atlas", atlas)):
        if not os.path.isfile(p):
            sys.exit(f"{label} file does not exist: {p}")
    if brain_mask and not os.path.isfile(brain_mask):
        sys.exit(f"brain mask file does not exist: {brain_mask}")

    is_nifti_input = _is_nifti(subj_path)
    if is_nifti_input:
        # Strip both .nii and .nii.gz so the stem is the same regardless.
        stem = subj_path
        for ext in (".nii.gz", ".nii"):
            if stem.endswith(ext):
                stem = stem[: -len(ext)]
                break
    else:
        stem = os.path.splitext(subj_path)[0]
        if not (os.path.exists(stem + ".REC") or os.path.exists(stem + ".rec")):
            sys.exit(f"REC file not found alongside {subj_path}")

    # Resolve subject correction up front so we can include the resulting
    # space tag in the output directory / sidecar names. That way runs with
    # and without correction can coexist without overwriting each other.
    subj_corr = None
    corr_json = stem + "_corrections.json"
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

    subj_id = os.path.basename(stem)
    if OUTPUT_DIR is not None:
        outdir = OUTPUT_DIR
        summary_path = OUTPUT_DIR.rstrip("/") + ".json"
    else:
        outdir = stem + f"_warper_{space_tag}"
        summary_path = stem + f"_warper_{space_tag}.json"

    print("=== OUTPUTS ===")
    print(f"  outdir       : {outdir}")
    print(f"  summary json : {summary_path}")
    print(f"  space tag    : {space_tag}")
    print()

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
    needs_staging = (" " in outdir or " " in subj_path
                     or " " in template or " " in atlas
                     or (brain_mask is not None and " " in brain_mask))
    if needs_staging:
        if STAGING_ROOT is not None:
            work_root = STAGING_ROOT
        else:
            work_root = os.path.expanduser(f"~/aw_work/{safe_subj_id}_{space_tag}")
        print(f"  Spaces detected in input paths — staging in {work_root} "
              "to avoid tcsh parsing issues.")
        work_outdir = os.path.join(work_root, "out")
        work_inputs = os.path.join(work_root, "inputs")
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
        if brain_mask:
            brain_mask = _stage(brain_mask, "nmt_brainmask")
        print("=== STAGED SYMLINKS (verify these resolve to the correct files!) ===")
        for link in [template, atlas] + ([brain_mask] if brain_mask else []):
            try:
                print(f"  {link}  ->  {os.readlink(link)}")
            except OSError:
                print(f"  {link}  (not a symlink)")
        print()

    # 1. Convert subject MRI to NIfTI, composing in the subject correction
    # resolved above if applicable. For NIfTI input with no correction this
    # is essentially a re-save into the work_inputs dir.
    subj_nii = os.path.join(work_inputs, f"{safe_subj_id}_{space_tag}.nii.gz")
    print(f"[1/3] Converting subject MRI -> {subj_nii}")
    subject_to_nifti(subj_path, subj_nii, correction=subj_corr)

    # 2. @animal_warper.
    print(f"[2/3] Running @animal_warper (template={os.path.basename(template)}, "
          f"atlas={os.path.basename(atlas)}"
          + (f", skullstrip={os.path.basename(brain_mask)}" if brain_mask else "")
          + ")")
    run_animal_warper(subj_nii, template, atlas, work_outdir, safe_subj_id,
                      brain_mask=brain_mask)

    # If we staged in a separate work dir, mirror the contents back to the
    # user-facing outdir next to the input file.
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

    # 3. Sidecar JSON.
    print(f"[3/3] Locating outputs in {outdir}")
    warped_atlas, warped_template = find_outputs(outdir, safe_subj_id, atlas)
    summary = {
        "subject_file": subj_path,
        "subj_id": safe_subj_id,
        "outdir": outdir,
        "work_outdir": work_outdir if work_outdir != outdir else None,
        "source_template": template,
        "source_atlas": atlas,
        "subject_space": space_tag,
        "warped_template_in_subject": warped_template,
        "warped_atlas_in_subject": warped_atlas,
    }
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"Wrote summary -> {summary_path}")

    print()
    print("Done. To use in mri_viewer, update mri_viewer_config.json:")
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
