"""
Drive AFNI's @animal_warper to register a subject PAR/REC MRI to the NMT v2.0
sym template, producing an atlas + template warped into the subject's native
scanner space.

Usage
-----
    python -m src.mri.run_animal_warper SUBJECT.PAR [options]

When run with no options, paths are read from mri_viewer_config.json in the
current working directory:
    template_mri_path   -> @animal_warper -base
    atlas_nifti_path    -> @animal_warper -atlas (followset)

Outputs are written to <subject>_warper/ next to the PAR file. Two files in
that directory are what the viewer should subsequently load:
    <subj>_in_<subj>_NMT.nii.gz                — template warped to subject
    <subj>_in_<subj>_D99_atlas_in_NMT...nii.gz — atlas labels warped to subject

A summary JSON <subject>_warper.json is also written alongside the PAR file
listing the resulting paths so they can be auto-picked up by the viewer.

Prerequisite: AFNI must be installed and on PATH. Quick install on Linux:

    cd /tmp
    curl -fL -o setup.tcsh https://afni.nimh.nih.gov/pub/dist/bin/misc/@update.afni.binaries
    tcsh setup.tcsh -package linux_ubuntu_24_64 -do_extras
    # then add ~/abin to PATH, log out/in, and verify with: @animal_warper -help

Runtime is typically 30-60 min per subject on a workstation.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time

import nibabel as nib
import numpy as np

from src.mri.correction import load_corrections


def _require_afni():
    if shutil.which("@animal_warper") is None:
        sys.exit(
            "ERROR: '@animal_warper' not found on PATH. Install AFNI first "
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


def run_animal_warper(subj_nii, base_nii, atlas_nii, outdir, subj_id,
                      extra_args=None):
    """Invoke @animal_warper. Returns the completed-process object."""
    cmd = [
        "@animal_warper",
        "-input", subj_nii,
        "-base", base_nii,
        "-atlas_followers", atlas_nii,
        "-outdir", outdir,
        "-input_abbrev", subj_id,
    ]
    if extra_args:
        cmd.extend(extra_args)

    print("Running:")
    print("  " + " ".join(cmd))
    t0 = time.time()
    proc = subprocess.run(cmd, check=False)
    dt = time.time() - t0
    print(f"@animal_warper exited with code {proc.returncode} after {dt/60:.1f} min")
    if proc.returncode != 0:
        sys.exit(proc.returncode)
    return proc


def find_outputs(outdir, subj_id, atlas_nii):
    """Locate the atlas-in-subject and template-in-subject NIfTIs produced by
    @animal_warper. Naming convention: <subj_id>_<atlas_basename>_in_subj.nii.gz
    or similar — actual layout can vary between AFNI versions, so we glob.
    """
    import glob

    atlas_base = os.path.basename(atlas_nii)
    for ext in (".nii.gz", ".nii"):
        if atlas_base.endswith(ext):
            atlas_base = atlas_base[: -len(ext)]
            break

    # Search common @animal_warper output patterns.
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

    return pick(atlas_candidates, "atlas-in-subject"), pick(template_candidates, "template-in-subject")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("par_file", help="Subject PAR file (REC must be alongside).")
    ap.add_argument("--template", help="Override template NIfTI (-base).")
    ap.add_argument("--atlas", help="Override atlas NIfTI (-atlas_followers).")
    ap.add_argument("--config",
                    default=os.path.join(os.getcwd(), "mri_viewer_config.json"),
                    help="mri_viewer_config.json to read template/atlas paths from.")
    ap.add_argument("--outdir", help="Output directory (default: <par>_warper/).")
    ap.add_argument("--subj-id", help="Short subject id used in output names (default: PAR basename).")
    ap.add_argument("--keep-nifti", action="store_true",
                    help="Keep the intermediate subject NIfTI conversion.")
    ap.add_argument("--no-subject-correction", action="store_true",
                    help="Skip applying <par>_corrections.json to the NIfTI affine. "
                         "Use this only if you intend to set atlas_correction to "
                         "your subject correction matrix manually in the viewer.")
    ap.add_argument("--extra", nargs=argparse.REMAINDER,
                    help="Pass remaining args verbatim to @animal_warper (must be last).")
    args = ap.parse_args()

    par_path = os.path.abspath(args.par_file)
    if not os.path.isfile(par_path):
        sys.exit(f"PAR file not found: {par_path}")

    rec_path = os.path.splitext(par_path)[0]
    if not (os.path.exists(rec_path + ".REC") or os.path.exists(rec_path + ".rec")):
        sys.exit(f"REC file not found alongside {par_path}")

    # Resolve template + atlas from CLI overrides or config.
    cfg = {}
    if os.path.exists(args.config):
        with open(args.config) as f:
            cfg = json.load(f)
    template = args.template or cfg.get("template_mri_path")
    atlas = args.atlas or cfg.get("atlas_nifti_path")
    if not template or not os.path.isfile(template):
        sys.exit("Template NIfTI not specified or missing. Pass --template or set "
                 "template_mri_path in mri_viewer_config.json.")
    if not atlas or not os.path.isfile(atlas):
        sys.exit("Atlas NIfTI not specified or missing. Pass --atlas or set "
                 "atlas_nifti_path in mri_viewer_config.json.")

    par_stem = os.path.splitext(par_path)[0]
    subj_id = args.subj_id or os.path.basename(par_stem)
    outdir = args.outdir or (par_stem + "_warper")
    os.makedirs(outdir, exist_ok=True)

    _require_afni()

    # 1. PAR/REC -> NIfTI, optionally pre-applying the subject correction so
    # the NIfTI lives in the viewer's corrected-world display space.
    subj_corr = None
    if not args.no_subject_correction:
        corr_json = par_stem + "_corrections.json"
        if os.path.exists(corr_json):
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
    subj_nii = os.path.join(outdir, f"{subj_id}_{space_tag}.nii.gz")
    print(f"[1/3] Converting PAR/REC -> {subj_nii}")
    par_to_nifti(par_path, subj_nii, correction=subj_corr)

    # 2. @animal_warper.
    print(f"[2/3] Running @animal_warper (template={os.path.basename(template)}, "
          f"atlas={os.path.basename(atlas)})")
    run_animal_warper(subj_nii, template, atlas, outdir, subj_id,
                      extra_args=args.extra)

    # 3. Locate outputs and write a sidecar JSON.
    print(f"[3/3] Locating outputs in {outdir}")
    warped_atlas, warped_template = find_outputs(outdir, subj_id, atlas)
    summary_path = par_stem + "_warper.json"
    summary = {
        "par_file": par_path,
        "subj_id": subj_id,
        "outdir": outdir,
        "source_template": template,
        "source_atlas": atlas,
        "subject_space": "corrected" if subj_corr is not None else "native",
        "warped_template_in_subject": warped_template,
        "warped_atlas_in_subject": warped_atlas,
    }
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"Wrote summary -> {summary_path}")

    if not args.keep_nifti:
        try:
            os.remove(subj_nii)
        except OSError:
            pass

    print()
    print("Done. To load the warped atlas in mri_viewer, update "
          "mri_viewer_config.json:")
    if warped_atlas:
        print(f'  "atlas_nifti_path":   "{warped_atlas}",')
    if warped_template:
        print(f'  "template_mri_path":  "{warped_template}",')
    if subj_corr is not None:
        print("The atlas_correction in the viewer should be reset to identity — "
              "the warp aligned to your AC/PC-corrected MRI space, so display "
              "lines up automatically.")
    else:
        print("The NIfTI was warped in the subject's native scanner space. If "
              "you use a subject correction matrix in the viewer, set the atlas "
              "correction to that same matrix; otherwise leave it at identity.")


if __name__ == "__main__":
    main()
