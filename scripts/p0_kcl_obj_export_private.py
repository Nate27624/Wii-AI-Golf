#!/usr/bin/env python3
"""Export one source-qualified PRIVATE KCL collision candidate to local ASCII OBJ.

Original RAM remains read-only, SHA-verified, and outside Git. A private mesh
is a *visual candidate*, not proof of active golf collision or training data.
The export is deliberately independent of octree, trees, and material analysis.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import hashlib
import json
import mmap
import math
import os
from pathlib import Path
import stat
import subprocess
import struct
import sys

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import p0_kcl_private_probe as kcl
import p0_kcl_full_validation_private as full

MAX_OBJ_BYTES = 16 * 1024 * 1024
MAX_OBJ_FACES = 30000
MAX_OBJ_VERTICES = 90000
CAPTURE_NUMBER = 5
CONTROL_NUMBERS = (1, 7)


class ExportGate(ValueError):
    """Only static, non-sensitive diagnostic stage codes go to stdout."""

    def __init__(self, stage: str, capture_number: int | None = None):
        super().__init__("private export source/output gate abstained")
        self.stage = stage
        self.capture_number = capture_number



def _git_ignored_private_obj(path: Path) -> bool:
    """Approve project Data/derived OBJ only when explicitly Git-ignored.

    A containing .git root alone is not a reason to prevent the operator
    from organizing their own private files. Require ignored AND untracked.
    """
    data = path.parent.parent
    if (path.parent.name != "derived" or data.name != "Wii-AI-Golf-Data"
            or not path.name.endswith("-PRIVATE.obj")
            or data.is_symlink() or path.parent.is_symlink()):
        return False
    try:
        ignored = subprocess.run(
            ["git", "-C", str(path.parent), "check-ignore", "--no-index", "-q",
             "--", str(path)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            check=False, timeout=5,
        )
        tracked = subprocess.run(
            ["git", "-C", str(path.parent), "ls-files", "--cached", "-z",
             "--", str(path)],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            check=False, timeout=5,
        )
        # --error-unmatch differs for untracked paths across Git for Windows
        # versions. --cached -z is stable: 0 + empty stdout proves the file
        # does not already occur in the repository index. A Git failure
        # cannot be mistaken for "untracked".
        if ignored.returncode != 0:
            raise ExportGate('OUTPUT_GIT_IGNORE_UNVERIFIED')
        if tracked.returncode != 0:
            raise ExportGate('OUTPUT_GIT_INDEX_CHECK_FAILED')
        if tracked.stdout != b"":
            raise ExportGate('OUTPUT_GIT_TRACKED_REJECTED')
        return True
    except (OSError, subprocess.TimeoutExpired):
        raise ExportGate('OUTPUT_GIT_COMMAND_FAILED') from None


def _safe_output_path(output: Path, data_root: Path) -> Path:
    """Allow new private OBJ in Data/derived or per-user LOCALAPPDATA.

    Both are allowlisted, must already exist and must be outside Git.
    Never use untrusted output paths as directory creation targets.
    """
    root = data_root.resolve(strict=True)
    if not root.is_dir() or data_root.is_symlink():
        raise ValueError('private Data root invalid')

    # A workspace may have an enclosing Git checkout above the sibling
    # Wii-AI-Golf-Data directory. In that case, allow a narrowly prescribed
    # alternate destination in per-user LOCALAPPDATA, never arbitrary paths.
    local_env = os.environ.get('LOCALAPPDATA')
    if local_env:
        user_root = Path(local_env)
        if user_root.is_dir() and not user_root.is_symlink():
            user_root = user_root.resolve(strict=True)
            app_folder = user_root / 'WiiGolfAI'
            priv_folder = app_folder / 'private'
            derived_folder = priv_folder / 'derived'
            if (all(d.is_dir() and not d.is_symlink()
                    for d in (app_folder, priv_folder, derived_folder))
                    and output.parent.is_dir()
                    and not output.parent.is_symlink()
                    and output.parent.resolve(strict=True) ==
                    derived_folder.resolve(strict=True)):
                if (output.suffix.lower() != '.obj'
                        or not output.name.endswith('-PRIVATE.obj')):
                    raise ValueError('private OBJ name must end in -PRIVATE.obj')
                if output.is_symlink() or output.exists():
                    raise ValueError('refusing existing, linked, or invalid OBJ target')
                approved_parent = derived_folder.resolve(strict=True)
                if any((d / '.git').exists()
                       for d in (approved_parent, *approved_parent.parents)):
                    raise ValueError('OBJ output must never be inside Git')
                return approved_parent / output.name

    parent = root / 'derived'
    if not parent.is_dir() or parent.is_symlink():
        raise ValueError('private Data derived directory missing or linked')
    parent = parent.resolve(strict=True)
    if parent.parent != root:
        raise ValueError('output must be directly in private Data derived')
    if output.suffix.lower() != '.obj' or not output.name.endswith('-PRIVATE.obj'):
        raise ValueError('private OBJ name must end in -PRIVATE.obj')
    if output.name in ('.', '..') or output.is_symlink() or output.exists():
        raise ValueError('refusing existing, linked, or invalid OBJ target')
    if not output.parent.is_dir() or output.parent.is_symlink():
        raise ValueError('OBJ parent must be existing private Data/derived')
    if output.parent.resolve(strict=True) != parent:
        raise ValueError('OBJ must be placed directly under private Data/derived')
    path = parent / output.name
    if (any((p / '.git').exists() for p in (parent, *parent.parents))
            and not _git_ignored_private_obj(path)):
        raise ValueError('OBJ output must never be inside Git')
    return path


def _source_qualified_mesh(folders, capture: int, seven, roster, *, keep_mesh: bool):
    """One original pair; verify source scene and every prism before writing."""
    with ExitStack() as stack:
        banks = []
        for i, size in enumerate(seven.SIZE, 1):
            path = seven.src._file(folders[capture], f'{capture}.{i}.raw', size)
            before = path.lstat()
            fd = os.open(path, os.O_RDONLY | getattr(os, 'O_BINARY', 0)
                         | getattr(os, 'O_NOFOLLOW', 0))
            stack.callback(os.close, fd)
            after = os.fstat(fd)
            if not stat.S_ISREG(after.st_mode) or (
                    after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns
                ) != (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns):
                raise ValueError('original bank identity changed')
            mm = mmap.mmap(fd, 0, access=mmap.ACCESS_READ)
            stack.callback(mm.close)
            banks.append(mm)
        reader = roster.TwoBankReader(*banks)
        source = seven._get(reader)
        # Independent source-field ownership presence gates; pointer values
        # stay in memory and are never sent to stdout or the OBJ file.
        roots = kcl._source_model_category(reader, source['field'], roster)
        if any(roots.get(label) != 'non_null_in_guest_ram' for label in (
                'placement_pmp', 'course_model_object',
                'course_visual_model_g3d', 'minimap_object')):
            raise ExportGate('FIELD_MODEL_ROOTS', capture)
        _, count1 = kcl.scan_bank(banks[0], limit=1)
        hits, count2 = kcl.scan_bank(banks[1], limit=2)
        if count1 != 0 or count2 != 1 or len(hits) != 1:
            raise ExportGate('UNIQUE_MEM2_KCL_CANDIDATE', capture)
        start, header = hits[0]
        tee = source['triplets']['source_current_start']
        pin = source['pin']
        report = full.analyze_blob(banks[1], start, tee_words=tee, pin_words=pin)
        count = report['prism_slot_upper_bound']
        if (count != header['prism_count_upper_bound']
                or not 2 <= count <= MAX_OBJ_FACES
                or 3*count > MAX_OBJ_VERTICES
                or not report['all_prism_slots_reconstructed']
                or report['prism_index_slots_valid'] != count
                or report['prism_referenced_normals_unit'] != count
                or report['prism_reconstructed_non_degenerate'] != count
                or report['tee_untransformed_proximity'] != 'WITHIN_2PCT_OF_MESH_BBOX_DIAGONAL'
                or report['pin_untransformed_proximity'] != 'WITHIN_2PCT_OF_MESH_BBOX_DIAGONAL'):
            raise ExportGate('FULL_PRISM_OR_TEE_PIN_GATE', capture)
        triangles = None
        attributes = None
        if keep_mesh:
            po, no, prism_offset, _ = struct.unpack_from('>IIII', banks[1], start)
            positions = [kcl._v3(banks[1], start + po + 12*i)
                         for i in range((no-po)//12)]
            normals = [kcl._v3(banks[1], start + no + 12*i)
                       for i in range((prism_offset+0x10-no)//12)]
            # Require all reconstructed faces, not a decimated preview, and
            # never use a geometry 'repair' that changes source coordinates.
            triangles = []
            attributes = []
            for i in range(count):
                tri = kcl._triangle(banks[1], start, positions, normals, prism_offset, i)
                if tri is None:
                    raise ExportGate('TRIANGLE_CONVERSION', capture)
                # Canonical _triangle returns original prism attribute at
                # +0x0E. No histogram join or inferred terrain semantics.
                attr = tri[3]
                if type(attr) is not int or not 0 <= attr <= 0xFFFF:
                    raise ExportGate('PRISM_SURFACE_ATTRIBUTE', capture)
                triangles.append(tri[:3])
                attributes.append(attr)
        return {
            'hole': source['hole'],
            'count': count,
            'private_geometry_fingerprint': report['fingerprint_PRIVATE'],
            'triangles_PRIVATE': triangles,
            'attributes_PRIVATE': attributes,
        }


def _obj_bytes(triangles, *, attributes=None) -> bytes:
    """Produce strictly v/f triangle OBJ compatible with S002's terrain.py."""
    if not 2 <= len(triangles) <= MAX_OBJ_FACES or 3*len(triangles) > MAX_OBJ_VERTICES:
        raise ValueError('OBJ face or vertex bound exceeded')
    if attributes is not None and (
            len(attributes) != len(triangles) or
            any(type(x) is not int or not 0 <= x <= 0xFFFF for x in attributes)):
        raise ValueError('Source KCL attribute cardinality/typing invalid')
    lines = [
        '# PRIVATE KCL collision candidate - not verified visible terrain',
        '# Source coordinate components unchanged; OGWS groups are source IDs only',
    ]
    for face in triangles:
        if len(face) != 3:
            raise ValueError('OBJ requires source triangles')
        for vertex in face:
            if len(vertex) != 3 or any(
                not isinstance(v, (int, float)) or
                not math.isfinite(v) or abs(v) >= 1e7
                for v in vertex
            ):
                raise ValueError('nonfinite or unsafe OBJ vertex')
            lines.append('v ' + ' '.join(format(v, '.9g') for v in vertex))
    for i in range(len(triangles)):
        j = 3*i+1
        if attributes is not None:
            lines.append(f'g KCL_OGWS_{attributes[i]:04X}')
        lines.append(f'f {j} {j+1} {j+2}')
    payload = ('\n'.join(lines) + '\n').encode('ascii')
    if not 1 <= len(payload) <= MAX_OBJ_BYTES:
        raise ValueError('OBJ payload size exceeds private viewer bound')
    return payload


def _write_new_private_obj(output: Path, payload: bytes) -> None:
    """Exclusive-create protects existing private exports; remove partial only."""
    fd = os.open(output, os.O_CREAT | os.O_EXCL | os.O_WRONLY
                 | getattr(os, 'O_BINARY', 0), 0o600)
    try:
        with os.fdopen(fd, 'wb') as out:
            out.write(payload)
            out.flush()
            os.fsync(out.fileno())
    except BaseException:
        output.unlink(missing_ok=True)
        raise


def export(archive: Path, output: Path, *, capture=CAPTURE_NUMBER,
           controls=CONTROL_NUMBERS, surface_groups=False) -> dict:
    import audit_p0_seven_numbered_source_pairs_private as seven
    from audit_p0_seven_numbered_source_pairs_private import roster
    if type(surface_groups) is not bool:
        raise ValueError('Surface groups option must be boolean')
    if (type(capture) is not int or capture not in range(1,8)
            or len(controls) != 2 or
            any(type(n) is not int or n not in range(1,8) for n in controls)
            or len({capture, *controls}) != 3):
        raise ValueError('source capture/control numbers must be distinct')
    from audit_selected_ball_start_link_private import DATA_ROOT
    try:
        target = _safe_output_path(output, DATA_ROOT)
    except ExportGate:
        raise
    except (OSError, ValueError, TypeError) as exc:
        stage = {
            'private Data root invalid': 'OUTPUT_DATA_ROOT',
            'private Data derived directory missing or linked': 'OUTPUT_DERIVED_DIRECTORY',
            'output must be directly in private Data derived': 'OUTPUT_DERIVED_DIRECTORY_PARENT',
            'private OBJ name must end in -PRIVATE.obj': 'OUTPUT_PRIVATE_OBJ_FILENAME',
            'refusing existing, linked, or invalid OBJ target': 'OUTPUT_FILE_ALREADY_EXISTS',
            'OBJ parent must be existing private Data/derived': 'OUTPUT_REQUESTED_PARENT',
            'OBJ must be placed directly under private Data/derived': 'OUTPUT_PARENT_MISMATCH',
            'OBJ output must never be inside Git': 'OUTPUT_INSIDE_GIT',
        }.get(str(exc), 'OUTPUT_DESTINATION_UNKNOWN')
        raise ExportGate(stage) from None
    try:
        folders = seven._check_archive(archive)
    except (OSError, ValueError, TypeError, KeyError, IndexError, OverflowError):
        raise ExportGate('ARCHIVE_SHA_PRECHECK') from None
    findings = {}
    # Independently read both controls as well as requested selected capture.
    for number in (*controls, capture):
        try:
            findings[number] = _source_qualified_mesh(
                folders, number, seven, roster, keep_mesh=(number == capture))
        except ExportGate:
            raise
        except (OSError, ValueError, IndexError, KeyError, TypeError,
                AttributeError, OverflowError, struct.error):
            raise ExportGate('CAPTURE_SOURCE_OR_MEMORY_READER', number) from None
    baseline = findings[capture]
    if any(
        findings[n]['hole'] != baseline['hole'] or
        findings[n]['count'] != baseline['count'] or
        findings[n]['private_geometry_fingerprint'] !=
        baseline['private_geometry_fingerprint']
        for n in controls
    ):
        raise ExportGate('CROSS_CAPTURE_GEOMETRY_CONSISTENCY')
    try:
        payload = _obj_bytes(
            baseline['triangles_PRIVATE'],
            attributes=(baseline['attributes_PRIVATE'] if surface_groups else None))
    except (ValueError, TypeError, OverflowError, AttributeError):
        raise ExportGate('OBJ_ASCII_ENCODING') from None
    # Recheck every original bank after mappings have closed, BEFORE write.
    try:
        seven._check_archive(archive)
    except (OSError, ValueError, TypeError, KeyError, IndexError, OverflowError):
        raise ExportGate('ARCHIVE_SHA_POSTCHECK') from None
    if target.exists():
        raise ExportGate('OUTPUT_ALREADY_EXISTS')
    try:
        _write_new_private_obj(target, payload)
    except (OSError, ValueError, TypeError):
        raise ExportGate('OUTPUT_FILE_CREATE') from None
    return {
        'kind': 'P0_PRIVATE_KCL_OBJ_EXPORT',
        'status': 'PRIVATE_OBJ_CREATED',
        'capture_number': capture,
        'control_captures': list(controls),
        'source_hole_index': baseline['hole'],
        'triangle_faces': baseline['count'],
        'vertex_records': 3*baseline['count'],
        'cross_capture_geometry_identical': True,
        'source_component_coordinates_untransformed': True,
        'viewer_compatible_ascii_triangle_obj': True,
        'original_prism_ogws_groups_included': surface_groups,
        'filename': target.name,
        'obj_sha256': hashlib.sha256(payload).hexdigest(),
        'octree_reachability_verified': False,
        'game_collision_ownership_verified': False,
        'surface_materials_or_trees_included': False,
        'training_approved': False,
        'allowed_to_publish': False,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--capture', type=int, default=CAPTURE_NUMBER)
    parser.add_argument('--controls', nargs=2, type=int, default=CONTROL_NUMBERS)
    parser.add_argument('--surface-groups', action='store_true',
                        help='Include original KCL prism OGWS attribute group per triangle')
    args = parser.parse_args(argv)
    try:
        print(json.dumps(export(args.archive, args.output,
                               capture=args.capture, controls=tuple(args.controls),
                               surface_groups=args.surface_groups),
                         indent=2, sort_keys=True))
        return 0
    except ExportGate as exc:
        print(json.dumps({
            'kind': 'P0_PRIVATE_KCL_OBJ_EXPORT',
            'status': 'ABSTAIN_SOURCE_GEOMETRY_OR_OUTPUT_GATE',
            'stage': exc.stage,
            'capture_number': exc.capture_number,
            'private_obj_created': False,
            'training_approved': False,
            'allowed_to_publish': False,
        }))
        return 3
    except (OSError, ValueError, IndexError, KeyError, TypeError,
            AttributeError, OverflowError, struct.error):
        print(json.dumps({
            'kind': 'P0_PRIVATE_KCL_OBJ_EXPORT',
            'status': 'ABSTAIN_SOURCE_GEOMETRY_OR_OUTPUT_GATE',
            'stage': 'UNCLASSIFIED_SAFE_ABSTAIN',
            'capture_number': None,
            'private_obj_created': False,
            'training_approved': False,
            'allowed_to_publish': False,
        }))
        return 3


if __name__ == '__main__':
    raise SystemExit(main())
