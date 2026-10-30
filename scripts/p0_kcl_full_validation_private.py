#!/usr/bin/env python3
"""Read-only, whole-prism KCL candidate falsification on original private Wii RAM.

Requires the preceding terrain KCL header probe on a stacked branch. Keeps all
private addresses, native words, mesh vertices, and digests out of stdout.
A structurally consistent KCL asset is NOT proof of game-owned terrain.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import hashlib
import json
import math
import mmap
import os
from pathlib import Path
import stat
import struct
import sys

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import p0_kcl_private_probe as kcl

MAX_SLOTS = 50000
CAPTURES = (1, 5, 7)


def _f32(words):
    if len(words) != 3 or any(type(w) is not int or not 0 <= w <= 0xFFFFFFFF for w in words):
        return None
    a = tuple(struct.unpack('>f', w.to_bytes(4, 'big'))[0] for w in words)
    return a if all(math.isfinite(v) and abs(v) < 1e7 for v in a) else None


def _point_triangle_distance_sq(p, a, b, c):
    """Ericson region test; distances measured only in candidate raw components."""
    ab, ac, ap = kcl._sub(b, a), kcl._sub(c, a), kcl._sub(p, a)
    d1, d2 = kcl._dot(ab, ap), kcl._dot(ac, ap)
    if d1 <= 0 and d2 <= 0:
        return kcl._dot(ap, ap)
    bp = kcl._sub(p, b)
    d3, d4 = kcl._dot(ab, bp), kcl._dot(ac, bp)
    if d3 >= 0 and d4 <= d3:
        return kcl._dot(bp, bp)
    vc = d1*d4 - d3*d2
    if vc <= 0 and d1 >= 0 and d3 <= 0:
        t = d1/(d1-d3)
        q = kcl._add(a, kcl._mul(ab, t))
        v = kcl._sub(p, q)
        return kcl._dot(v, v)
    cp = kcl._sub(p, c)
    d5, d6 = kcl._dot(ab, cp), kcl._dot(ac, cp)
    if d6 >= 0 and d5 <= d6:
        return kcl._dot(cp, cp)
    vb = d5*d2 - d1*d6
    if vb <= 0 and d2 >= 0 and d6 <= 0:
        t = d2/(d2-d6)
        q = kcl._add(a, kcl._mul(ac, t))
        v = kcl._sub(p, q)
        return kcl._dot(v, v)
    va = d3*d6 - d5*d4
    if va <= 0 and (d4-d3) >= 0 and (d5-d6) >= 0:
        cb = kcl._sub(c, b)
        t = (d4-d3)/((d4-d3)+(d5-d6))
        q = kcl._add(b, kcl._mul(cb, t))
        v = kcl._sub(p, q)
        return kcl._dot(v, v)
    denom = va + vb + vc
    if not math.isfinite(denom) or abs(denom) < 1e-20:
        raise ValueError('degenerate triangle')
    v, w = vb/denom, vc/denom
    q = kcl._add(a, kcl._add(kcl._mul(ab, v), kcl._mul(ac, w)))
    h = kcl._sub(p, q)
    return kcl._dot(h, h)


def _anchor_class(anchor, triangles, low, high):
    if anchor is None or not triangles:
        return 'UNAVAILABLE'
    diag = math.sqrt(sum((high[i]-low[i])**2 for i in range(3)))
    if not 0 < diag < 1e9:
        return 'INVALID_BOUNDING_BOX'
    # This assumes the same untransformed coordinate frame. It is diagnostic,
    # NOT evidence of a real coordinate transform or collision ownership.
    closest = min(_point_triangle_distance_sq(anchor, *tri[:3]) for tri in triangles)
    if not math.isfinite(closest):
        return 'INVALID_PROXIMITY'
    ratio = math.sqrt(max(closest, 0.0))/diag
    if ratio <= .02:
        return 'WITHIN_2PCT_OF_MESH_BBOX_DIAGONAL'
    if ratio <= .10:
        return 'WITHIN_10PCT_OF_MESH_BBOX_DIAGONAL'
    if ratio <= .25:
        return 'WITHIN_25PCT_OF_MESH_BBOX_DIAGONAL'
    return 'FAR_OR_COORDINATE_TRANSFORM_REQUIRED'


def analyze_blob(buf, offset, *, tee_words=None, pin_words=None):
    candidate = kcl.parse_kcl_candidate(buf, offset)
    if candidate is None:
        raise ValueError('candidate lost sampled-prism qualification')
    po, no, pro, octo = struct.unpack_from('>IIII', buf, offset)
    count = candidate['prism_count_upper_bound']
    if not 2 <= count <= MAX_SLOTS:
        raise ValueError('whole-prism analysis cap exceeded')
    positions = [kcl._v3(buf, offset+po+12*i)
                 for i in range((no-po)//12)]
    normals = [kcl._v3(buf, offset+no+12*i)
               for i in range((pro+0x10-no)//12)]
    index_ok = 0
    normal_ok = 0
    good = []
    valid_bitmap = []
    for i in range(count):
        q = offset+pro+0x10+0x10*i
        _, pi, fi, n1, n2, n3, _ = struct.unpack_from('>fHHHHHH', buf, q)
        indexes_ok = pi < len(positions) and max(fi, n1, n2, n3) < len(normals)
        if indexes_ok:
            index_ok += 1
        normals_ok = indexes_ok and all(kcl._normal(normals[j]) for j in (fi,n1,n2,n3))
        if normals_ok:
            normal_ok += 1
        tri = kcl._triangle(buf, offset, positions, normals, pro, i) if normals_ok else None
        valid_bitmap.append(tri is not None)
        if tri is not None:
            good.append(tri)
    prefix = next((i for i, ok in enumerate(valid_bitmap) if not ok), count)
    tail = next((i for i, ok in enumerate(reversed(valid_bitmap)) if ok), count)
    malformed_interior = sum(not x for x in valid_bitmap[:count-tail])
    low, high = None, None
    if good:
        vertices = [v for tri in good for v in tri[:3]]
        low = tuple(min(v[i] for v in vertices) for i in range(3))
        high = tuple(max(v[i] for v in vertices) for i in range(3))
    # Fingerprint never leaves this process; compare bytes through prism end.
    fingerprint = hashlib.blake2s(buf[offset:offset+octo], digest_size=16).digest()
    return {'prism_slot_upper_bound': count,
            'prism_index_slots_valid': index_ok,
            'prism_referenced_normals_unit': normal_ok,
            'prism_reconstructed_non_degenerate': len(good),
            'first_invalid_prism_slot_zero_based': prefix if prefix != count else None,
            'trailing_invalid_prism_slots': tail,
            'interior_invalid_prism_slots': malformed_interior,
            'all_prism_slots_reconstructed': len(good) == count,
            'tee_untransformed_proximity': _anchor_class(_f32(tee_words) if tee_words else None, good, low, high),
            'pin_untransformed_proximity': _anchor_class(_f32(pin_words) if pin_words else None, good, low, high),
            'octree_structure_validated': False,
            'fingerprint_PRIVATE': fingerprint}


def _read_capture(archive, folders, n, seven, roster):
    with ExitStack() as stack:
        banks = []
        for i, size in enumerate(seven.SIZE, 1):
            path = seven.src._file(folders[n], f'{n}.{i}.raw', size)
            before = path.lstat()
            fd = os.open(path, os.O_RDONLY | getattr(os, 'O_BINARY', 0) |
                         getattr(os, 'O_NOFOLLOW', 0))
            stack.callback(os.close, fd)
            s = os.fstat(fd)
            if not stat.S_ISREG(s.st_mode) or (
                    s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns) != (
                    before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns):
                raise ValueError('private bank replaced')
            m = mmap.mmap(fd, 0, access=mmap.ACCESS_READ)
            stack.callback(m.close)
            banks.append(m)
        rd = roster.TwoBankReader(*banks)
        source = seven._get(rd)
        # Deliberately require a *unique* candidate in MEM2 and no MEM1 match.
        _, count1 = kcl.scan_bank(banks[0], limit=1)
        hits, count2 = kcl.scan_bank(banks[1], limit=2)
        if count1 or count2 != 1 or len(hits) != 1:
            raise ValueError('unique MEM2 candidate not established')
        off, _ = hits[0]
        tee = source['triplets']['source_current_start']
        pin = source['pin']
        result = analyze_blob(banks[1], off, tee_words=tee, pin_words=pin)
        return source['hole'], result


def analyze_archive(archive: Path, captures=CAPTURES):
    import audit_p0_seven_numbered_source_pairs_private as seven
    from audit_p0_seven_numbered_source_pairs_private import roster
    if not captures or any(type(i) is not int or i not in range(1,8) for i in captures) or len(set(captures)) != len(captures):
        raise ValueError('capture selection invalid')
    folders = seven._check_archive(archive)
    scans = []
    for number in captures:
        hole, private = _read_capture(archive, folders, number, seven, roster)
        scans.append((number, hole, private))
    seven._check_archive(archive)
    baseline = scans[0][2]['fingerprint_PRIVATE']
    return {
        'kind': 'P0_PRIVATE_KCL_WHOLE_PRISM_FALSIFICATION',
        'status': 'CANDIDATE_GEOMETRY_ONLY',
        'capture_reports': [{
            'capture_number': n, 'source_hole_index': hole,
            **{k:v for k,v in private.items() if k != 'fingerprint_PRIVATE'}
        } for n, hole, private in scans],
        'prism_bytes_identical_across_selected_captures': all(s[2]['fingerprint_PRIVATE'] == baseline for s in scans[1:]),
        'same_source_hole_across_captures': len(set(s[1] for s in scans)) == 1,
        'file_header_is_active_course_collision_proven': False,
        'tee_pin_world_transform_verified': False,
        'terrain_3d_model_verified': False,
        'guest_physics_step_verified': False,
        'training_approved': False,
        'allowed_to_publish': False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', required=True, type=Path)
    parser.add_argument('--captures', nargs='+', type=int, default=list(CAPTURES))
    args = parser.parse_args(argv)
    try:
        print(json.dumps(analyze_archive(args.archive, tuple(args.captures)), indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError, TypeError, IndexError, KeyError, OverflowError, AttributeError, struct.error):
        print(json.dumps({'kind':'P0_PRIVATE_KCL_WHOLE_PRISM_FALSIFICATION',
                          'status':'ABSTAIN_SOURCE_ARCHIVE_OR_GEOMETRY_GATE',
                          'training_approved':False,'allowed_to_publish':False}))
        return 3


if __name__ == '__main__':
    raise SystemExit(main())
