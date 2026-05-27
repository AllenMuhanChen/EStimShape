#!/usr/bin/env python3
"""Convert all DICOM series in a folder to .nii.gz, one per series."""

import re
from collections import defaultdict
from pathlib import Path

import pydicom
from dicom2nifti.convert_dicom import dicom_array_to_nifti


def group_by_series(dcm_dir: Path) -> dict[str, list[pydicom.Dataset]]:
    series = defaultdict(list)
    for f in dcm_dir.iterdir():
        if not f.is_file():
            continue
        try:
            ds = pydicom.dcmread(f)
        except Exception:
            continue
        desc = getattr(ds, "SeriesDescription", "UNKNOWN")
        series[desc].append(ds)
    return dict(series)


def sanitize(name: str) -> str:
    """Make a series description safe for a filename."""
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", name).strip("_")


def dcm_to_niigz_all(dcm_dir: Path, out_dir: Path, base_name: str) -> list[Path]:
    dcm_dir, out_dir = Path(dcm_dir), Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    series = group_by_series(dcm_dir)
    print("Available series:")
    for d, datasets in sorted(series.items()):
        print(f"  [{len(datasets):4d} slices]  {d}")

    written = []
    for desc, datasets in series.items():
        suffix = sanitize(desc)
        out_path = out_dir / f"{base_name}_{suffix}.nii.gz"
        print(f"\nConverting: {desc}  -> {out_path.name}  ({len(datasets)} slices)")
        try:
            dicom_array_to_nifti(datasets, str(out_path), reorient_nifti=True)
            written.append(out_path)
        except Exception as e:
            print(f"  ! Skipped ({type(e).__name__}: {e})")
    return written


def main():
    dcm_dir = Path("/home/connorlab/Documents/MRI/Bixby/std_20221129_182317194")
    out_dir = Path("/home/connorlab/Documents/MRI/Bixby")
    base_name = "bixby"

    written = dcm_to_niigz_all(dcm_dir, out_dir, base_name)
    print("\nWrote:")
    for p in written:
        print(f"  {p}")


if __name__ == "__main__":
    main()