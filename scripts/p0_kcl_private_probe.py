#!/usr/bin/env python3
"""Source-gated offline Wii Sports Golf terrain KCL candidate probe.

Reads ONE original numbered MEM1/MEM2 snapshot from existing seven-pair private
archive. No Dolphin, memory writes, source files or raw-memory publication.
A file-layout KCL match is a candidate, not proof of live collision ownership.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import json
import math
import mmap
import os
from pathlib import Path
import re
import stat
import struct
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
HEADER_START = re.compile(b'\x00\x00(?:\x00[\x38-\xff]|[\x01-\x0f][\x00-\xff])')
MAX_BLOB = 32 * 1024 * 1024
MAX_PRISMS = 400_000


def _v3(buf, off):
    return struct.unpack_from('>fff', buf, off)


def _sub(a, b):
    return tuple(x-y for x, y in zip(a, b))


def _add(a, b):
    return tuple(x+y for x, y in zip(a, b))


def _mul(a, t):
    return tuple(x*t for x in a)


def _cross(a, b):
    return (a[1]*b[2]-a[2]*b[1],
            a[2]*b[0]-a[0]*b[2],
            a[0]*b[1]-a[1]*b[0])


def _dot(a, b):
    return sum(x*y for x, y in zip(a, b))


def _normal(a):
    n = math.sqrt(_dot(a, a))
    return math.isfinite(n) and 0.88 <= n <= 1.12


def _triangle(buf, start, pos, normals, prism_offset, j):
    # Wii KCL 1-indexed prism offset points 0x10 before first record.
    q = start + prism_offset + 0x10 + j*0x10
    height, pi, fi, n1, n2, n3, attribute = struct.unpack_from('>fHHHHHH', buf, q)
    if not math.isfinite(height) or not 0.005 < height < 100000:
        return None
    if pi >= len(pos) or max(fi, n1, n2, n3) >= len(normals):
        return None
    p, face = pos[pi], normals[fi]
    edge1, edge2, edge3 = normals[n1], normals[n2], normals[n3]
    cross_a, cross_b = _cross(edge1, face), _cross(edge2, face)
    da, db = _dot(cross_a, edge3), _dot(cross_b, edge3)
    if not math.isfinite(da*db) or abs(da) < 1e-4 or abs(db) < 1e-4:
        return None
    a = p
    b = _add(p, _mul(cross_b, height/db))
    c = _add(p, _mul(cross_a, height/da))
    if any(not math.isfinite(x) or abs(x)>1e7 for v in (a, b, c) for x in v):
        return None
    cross = _cross(_sub(b, a), _sub(c, a))
    area2 = math.sqrt(_dot(cross, cross))
    if not 0.0001 < area2 < 1e10:
        return None
    return (a, b, c, attribute)


def parse_kcl_candidate(buf, start):
    """Strictly ordered *file-layout* KCL only; not runtime pointer decoding.

    Sections need not be ordered in all KCL versions, so a zero-hit result
    does NOT prove no collision geometry is present.
    """
    try:
        if start < 0 or start%4 or start+0x3c > len(buf):
            return None
        po, no, pro, octo = struct.unpack_from('>IIII', buf, start)
        if not (0x38 <= po <= 0x1000 and po%4==0
                and po+12*3 <= no and no%4==0
                and no+12*4 <= pro+0x10 and pro%4==0
                and pro+0x10+0x10*2 <= octo and octo%4==0
                and octo <= MAX_BLOB and start+octo+4 <= len(buf)):
            return None
        prism_count = (octo-pro-0x10)//0x10
        if not 2 <= prism_count <= MAX_PRISMS:
            return None
        pos_count = (no-po)//12
        norm_count = (pro+0x10-no)//12
        if not 3 <= pos_count <= 65535 or not 4 <= norm_count <= 65535:
            return None
        thickness = struct.unpack_from('>f', buf, start+0x10)[0]
        minimum = _v3(buf, start+0x14)
        shifts = struct.unpack_from('>III', buf, start+0x2c)
        if not (math.isfinite(thickness) and 0.001 < thickness < 100000
                and all(math.isfinite(x) and abs(x)<1e7 for x in minimum)
                and all(s<=31 for s in shifts)):
            return None
        # Upper-bound section sizes include alignment padding, not asserted counts.
        positions = [_v3(buf, start+po+12*i) for i in range(pos_count)]
        normals = [_v3(buf, start+no+12*i) for i in range(norm_count)]
        if any(not math.isfinite(x) or abs(x)>1e7
               for vec in positions[:32] for x in vec):
            return None
        if not all(_normal(v) for v in normals[:min(12, len(normals))]):
            return None
        triangles = []
        selected = (0, 1, 2, prism_count//4, prism_count//2,
                    3*prism_count//4, prism_count-1)
        for j in sorted(set(selected)):
            t = _triangle(buf, start, positions, normals, pro, j)
            if t is None:
                return None
            triangles.append(t)
        return {'position_count_upper_bound': pos_count,
                'normal_count_upper_bound': norm_count,
                'prism_count_upper_bound': prism_count,
                'validated_prism_samples': len(triangles)}
    except (ValueError, OverflowError, struct.error, IndexError, ZeroDivisionError):
        return None


def scan_bank(buf, *, limit=12):
    """Scan aligned plausible KCL headers; return categorical evidence only."""
    hits = []
    for match in HEADER_START.finditer(buf):
        offset = match.start()
        if offset%4:
            continue
        result = parse_kcl_candidate(buf, offset)
        if result is not None:
            hits.append((offset, result))
    hits.sort(key=lambda h: (-h[1]['prism_count_upper_bound'], h[0]))
    return hits[:limit], len(hits)


def _source_model_category(rd, field, roster):
    u = rd.u32
    def valid(p, span=12):
        return roster._bank(p, span) is not None
    result = {}
    for label, off in (('placement_pmp', 0x18),
                       ('course_model_object', 0x70),
                       ('minimap_object', 0x74)):
        p = u(field+off)
        result[label] = ('non_null_in_guest_ram'
                         if p and valid(p) else 'absent_or_invalid')
        if label == 'course_model_object' and p and valid(p):
            model = u(p+0x04)
            result['course_visual_model_g3d'] = (
                'non_null_in_guest_ram' if model and valid(model)
                else 'absent_or_invalid')
    return result


def analyze(archive: Path, capture: int):
    import audit_p0_seven_numbered_source_pairs_private as seven
    from audit_p0_seven_numbered_source_pairs_private import roster
    if type(capture) is not int or capture not in range(1, 8):
        raise ValueError('invalid numbered phase')
    folders = seven._check_archive(archive)  # existing SHA/manifest gates
    with ExitStack() as stack:
        banks = []
        for i, size in enumerate(seven.SIZE, 1):
            filename = f'{capture}.{i}.raw'
            path = seven.src._file(folders[capture], filename, size)
            before = path.lstat()
            fd = os.open(path, os.O_RDONLY | getattr(os, 'O_BINARY', 0)
                         | getattr(os, 'O_NOFOLLOW', 0))
            stack.callback(os.close, fd)
            s = os.fstat(fd)
            if not stat.S_ISREG(s.st_mode) or (
                    s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns
                ) != (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns):
                raise ValueError('private bank identity changed')
            mm = mmap.mmap(fd, 0, access=mmap.ACCESS_READ)
            stack.callback(mm.close)
            banks.append(mm)
        rd = roster.TwoBankReader(*banks)
        source = seven._get(rd)  # Rev1, scene, owner, hole, ball, tee/pin
        model = _source_model_category(rd, source['field'], roster)
        summaries = []
        total = 0
        for name, bank in zip(('MEM1', 'MEM2'), banks):
            hits, count = scan_bank(bank)
            total += count
            summaries.append({
                'bank': name, 'file_style_kcl_header_candidates': count,
                'top_candidates': [
                    {'rank': j+1,
                     'prism_count_upper_bound': v['prism_count_upper_bound'],
                     'sampled_prisms_validated': v['validated_prism_samples']}
                    for j, (_, v) in enumerate(hits)]})
    seven._check_archive(archive)  # rehash original after bank maps close
    return {
        'kind': 'P0-PRIVATE-COURSE-KCL-HEADER-PROBE',
        'status': 'CANDIDATES_ONLY' if total else 'NO_FILE_STYLE_KCL_HEADER_DETECTED',
        'source_gates': 'REV1_GOLF_SCENE5_HITTING_GREEN_SELECTED_BALL_TEE_PIN',
        'capture_number': capture, 'source_hole_index': source['hole'],
        'field_roots': model, 'banks': summaries,
        'file_style_headers_total': total,
        'runtime_relocated_or_compressed_geometry_not_excluded': True,
        'triangle_to_tee_pin_alignment_verified': False,
        'terrain_3d_model_verified': False,
        'training_approved': False, 'allowed_to_publish': False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--capture', type=int, choices=range(1, 8), default=5)
    args = parser.parse_args(argv)
    try:
        print(json.dumps(analyze(args.archive, args.capture),
                         indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError, KeyError, IndexError, TypeError,
            OverflowError, AttributeError):
        print(json.dumps({
            'kind': 'P0-PRIVATE-COURSE-KCL-HEADER-PROBE',
            'status': 'ABSTAIN_SOURCE_OR_ARCHIVE_GATE',
            'training_approved': False, 'allowed_to_publish': False}))
        return 3


if __name__ == '__main__':
    raise SystemExit(main())
