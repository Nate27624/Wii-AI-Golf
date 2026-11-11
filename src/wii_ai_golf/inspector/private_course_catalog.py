"""Bounded local-only lookup of operator-owned Wii Golf FC course exports.

The Wii archive naming convention glf_course_fcN is not proof that N is the
selected training-shot scene. This catalog NEVER looks inside copyrighted
models, never downloads/extracts assets, never scans the disc, and never
changes KCL, RAM, or physics coordinates.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

MAX_SOURCE_COURSE = 99
DEFAULT_PRIVATE_ROOT = Path("D:/Projects/WiiGolfVisualPrivate")


@dataclass(frozen=True)
class PrivateCourseCandidate:
    course_number: int
    status: str
    exported_dae: Path | None
    source_brres_present: bool
    source_unpacked_present: bool
    source_carc_present: bool = False
    native_course_identity_verified: bool = False


def _is_local_regular(path: Path) -> bool:
    # Source is always verified again by the strict Collada asset loader.
    # Avoid accepting a symlink to outside the explicit private export root.
    return path.is_file() and not path.is_symlink()


def inspect_private_course(number: int, private_root: Path = DEFAULT_PRIVATE_ROOT
                           ) -> PrivateCourseCandidate:
    """Check only known locally exported file patterns, never recurse."""
    if type(number) is not int or not 1 <= number <= MAX_SOURCE_COURSE:
        raise ValueError("Course number must be an integer from 1 to 99")
    if not isinstance(private_root, Path):
        raise ValueError("Private visual root must be a Path")
    root = private_root
    name = f"glf_course_fc{number}"
    if (not root.is_absolute() or root.is_symlink()
            or not root.is_dir()):
        return PrivateCourseCandidate(
            number, "PRIVATE_COURSE_ROOT_NOT_PRESENT", None, False, False)
    # BrawlCrate original export convention, plus a nonrecursive direct
    # DAE alternative. Explicit operator files only.
    choices = (
        root / "visual_exports" / name / f"{name}.dae",
        root / "visual_exports" / f"{name}.dae",
    )
    brres = root / "unpacked" / name / "G3D" / f"{name}.brres"
    unpacked = root / "unpacked" / name
    # Explicit sibling original archive location identified by the operator.
    # Only checks for one known filename, never searches game/disc bytes.
    carc = root.parent / "RPGolScene" / f"{name}.carc"
    found = next((path for path in choices if _is_local_regular(path)), None)
    brres_present = _is_local_regular(brres)
    unpacked_present = unpacked.is_dir() and not unpacked.is_symlink()
    carc_present = _is_local_regular(carc)
    if found is not None:
        status = "LOCAL_SOURCE_DAE_CANDIDATE_FOUND"
    elif brres_present:
        status = "SOURCE_BRRES_PRESENT_EXPORT_DAE_WITH_BRAWLCRATE"
    elif unpacked_present:
        status = "SOURCE_UNPACKED_SEARCH_G3D_AND_EXPORT_DAE"
    elif carc_present:
        status = "SOURCE_CARC_PRESENT_EXTRACT_AND_EXPORT"
    else:
        status = "COURSE_NOT_YET_EXTRACTED_OR_EXPORTED"
    return PrivateCourseCandidate(
        number, status, found, brres_present, unpacked_present,
        carc_present)


def private_course_report(candidate: PrivateCourseCandidate) -> dict:
    """Safe report: no original private absolute path, geometry or texture."""
    return {
        "status": candidate.status,
        "candidate_asset": f"glf_course_fc{candidate.course_number}",
        "dae_export_ready": candidate.exported_dae is not None,
        "unpacked_original_brres_present": candidate.source_brres_present,
        "unpacked_course_directory_present": candidate.source_unpacked_present,
        "original_course_carc_archive_present": candidate.source_carc_present,
        "original_training_hole_identity_verified":
            candidate.native_course_identity_verified,
        "collision_world_alignment_verified": False,
        "course_identity_is_operator_visual_hypothesis": True,
        "training_approved": False,
    }
