#!/usr/bin/env python3
"""Offline, source-gated KCL octree reference verification (research-only).

Interprets a Wii-style KCL octree without asserting Wii Sports uses every
Mario Kart Wii convention. Never prints native RAM, raw indices, heap pointers,
file hashes or coordinates. Cannot establish game-owned collision behavior.
"""
from __future__ import annotations

import argparse
from collections import deque
from contextlib import ExitStack
import json
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

MAX_ROOT_WORDS = 131072
MAX_OCTREE_BYTES = 16 * 1024 * 1024
MAX_BRANCH_BLOCKS = 100000
MAX_LEAVES = 300000
MAX_LEAF_ITEMS = 50000
MAX_TOTAL_REFERENCES = 2000000
CAPTURES = (1, 5, 7)


class OctreeUnsupported(ValueError):
    """Header/variant differs from the bounded format tested here."""


class OctreeInvalid(ValueError):
    """Specific octree layout fails structural/reference validation."""


# Fixed allowlist of code-authored exception messages; never serialize native
# values, offsets, source paths, guest bytes, or untrusted exception strings.
# A failure means the *parser hypothesis* is unresolved, not no geometry.
_SAFE_UNSUPPORTED_REASONS = {
    'noncontiguous KCL dimensions': 'ROOT_MASK_SHAPE_UNSUPPORTED',
    'unexpected root block shift': 'ROOT_BLOCK_SHIFT_UNSUPPORTED',
    'root indexing shift convention differs': 'ROOT_INDEX_SHIFT_MISMATCH',
    'root entry table exceeds safe bound': 'ROOT_TABLE_TOO_LARGE',
    'too many root entries': 'ROOT_COUNT_TOO_LARGE',
    'unexpected leaf start convention': 'LEAF_SENTINEL_LAYOUT_UNSUPPORTED',
}


def _mask_width(mask: int) -> int:
    """Return count of contiguous low zero bits in upper-one KCL mask."""
    inv = (~mask) & 0xFFFFFFFF
    if inv & (inv + 1):
        raise OctreeUnsupported('noncontiguous KCL dimensions')
    return inv.bit_length()


def inspect_octree(buf, offset: int, *, max_octree_bytes=MAX_OCTREE_BYTES) -> dict:
    """Validate the full reachable root/branch/leaf reference graph.

    A leaf offset is relative to its enclosing branch base; child branch
    offsets are likewise relative to that base. Leaf arrays use a leading 0,
    one-indexed prism IDs, then a 0 terminator. Tests cannot prove Wii Sports
    uses the same game-specific semantics as MKW's published implementation.
    """
    candidate = kcl.parse_kcl_candidate(buf, offset)
    if candidate is None:
        raise OctreeInvalid('missing source-qualified file-style KCL candidate')
    prism_cap = candidate['prism_count_upper_bound']
    po, no, pro, octo = struct.unpack_from('>IIII', buf, offset)
    xmask, ymask, zmask, shift, shift_x, shift_xy = struct.unpack_from(
        '>IIIIII', buf, offset + 0x20)
    if shift > 30:
        raise OctreeUnsupported('unexpected root block shift')
    bx, by, bz = (max(0, _mask_width(v) - shift) for v in (xmask, ymask, zmask))
    if shift_x != bx or shift_xy != bx + by:
        raise OctreeUnsupported('root indexing shift convention differs')
    bits = bx + by + bz
    if bits > 17:
        raise OctreeUnsupported('root entry table exceeds safe bound')
    root_count = 1 << bits
    if root_count > MAX_ROOT_WORDS:
        raise OctreeUnsupported('too many root entries')
    octree_base = offset + octo
    bank_limit = min(len(buf), octree_base + max_octree_bytes)
    if octree_base + 4*root_count > bank_limit:
        raise OctreeInvalid('root table outside bounded octree')
    # Entries are held as (parent_block_relative_start, relative_word_offset,
    # depth), so different octree branches can point to one shared leaf list.
    pending = deque([(0, 4*j, 0) for j in range(root_count)])
    branch_blocks = set()
    leaf_lists = set()
    unique_prisms = set()
    total_refs = 0
    empty_leaves = 0
    max_depth = 0
    while pending:
        block, entry, depth = pending.popleft()
        max_depth = max(depth, max_depth)
        if depth > 30:
            raise OctreeInvalid('octree depth invalid')
        absolute = octree_base + block + entry
        if absolute % 4 or absolute < octree_base or absolute + 4 > bank_limit:
            raise OctreeInvalid('octree entry beyond bounded section')
        raw = struct.unpack_from('>I', buf, absolute)[0]
        relative = raw & 0x7FFFFFFF
        if raw & 0x80000000:
            pointer = block + relative
            start = octree_base + pointer
            if start % 2 or start < octree_base or start + 4 > bank_limit:
                raise OctreeInvalid('leaf list outside bounded octree')
            if pointer in leaf_lists:
                continue
            leaf_lists.add(pointer)
            if len(leaf_lists) > MAX_LEAVES:
                raise OctreeInvalid('too many leaf lists')
            # The first 0 terminates the preceding list in the standard KCL
            # storage layout. The next values are 1-based prism references.
            if struct.unpack_from('>H', buf, start)[0] != 0:
                raise OctreeUnsupported('unexpected leaf start convention')
            cursor = start + 2
            n = 0
            while True:
                if n > MAX_LEAF_ITEMS or cursor + 2 > bank_limit:
                    raise OctreeInvalid('leaf list not bounded/terminated')
                prism_id = struct.unpack_from('>H', buf, cursor)[0]
                cursor += 2
                if prism_id == 0:
                    break
                if prism_id > prism_cap:
                    raise OctreeInvalid('out of bounds prism index')
                unique_prisms.add(prism_id)
                total_refs += 1
                n += 1
                if total_refs > MAX_TOTAL_REFERENCES:
                    raise OctreeInvalid('too many total leaf references')
            if n == 0:
                empty_leaves += 1
        else:
            # Relative 0 loops on the same block; forbid non-forward pointers.
            new_block = block + relative
            if (relative == 0 or new_block <= block or
                    octree_base + new_block + 32 > bank_limit or
                    new_block % 4):
                raise OctreeInvalid('invalid child branch offset')
            if new_block in branch_blocks:
                continue
            if depth >= 30:
                raise OctreeInvalid('branch exceeds max octree depth')
            branch_blocks.add(new_block)
            if len(branch_blocks) > MAX_BRANCH_BLOCKS:
                raise OctreeInvalid('too many octree internal blocks')
            for index in range(8):
                pending.append((new_block, 4*index, depth+1))
    if not leaf_lists:
        raise OctreeInvalid('no reachable leaf lists')
    if not unique_prisms:
        raise OctreeInvalid('no reachable prism references')
    return {
        'octree_candidate_structurally_valid': True,
        'root_entry_count': root_count,
        'reachable_branch_blocks': len(branch_blocks),
        'reachable_leaf_lists': len(leaf_lists),
        'empty_leaf_lists': empty_leaves,
        'total_leaf_prism_references': total_refs,
        'distinct_prisms_referenced': len(unique_prisms),
        'highest_referenced_prism_index_one_based': max(unique_prisms),
        'all_candidate_prisms_referenced': len(unique_prisms) == prism_cap,
        'candidate_prism_upper_bound': prism_cap,
        'max_octree_depth': max_depth,
        'Wii_Sports_runtime_octree_usage_verified': False,
    }


def _read_one(folders, number, seven, roster):
    with ExitStack() as stack:
        banks = []
        for i, size in enumerate(seven.SIZE, 1):
            path = seven.src._file(folders[number], f'{number}.{i}.raw', size)
            s0 = path.lstat()
            fd = os.open(path, os.O_RDONLY | getattr(os, 'O_BINARY', 0) |
                         getattr(os, 'O_NOFOLLOW', 0))
            stack.callback(os.close, fd)
            s1 = os.fstat(fd)
            if not stat.S_ISREG(s1.st_mode) or (
                    s1.st_dev, s1.st_ino, s1.st_size, s1.st_mtime_ns) != (
                    s0.st_dev, s0.st_ino, s0.st_size, s0.st_mtime_ns):
                raise ValueError('native bank modified during open')
            mm = mmap.mmap(fd, 0, access=mmap.ACCESS_READ)
            stack.callback(mm.close)
            banks.append(mm)
        rd = roster.TwoBankReader(*banks)
        source = seven._get(rd)
        hits, c2 = kcl.scan_bank(banks[1], limit=2)
        _, c1 = kcl.scan_bank(banks[0], limit=1)
        if c1 or c2 != 1 or len(hits) != 1:
            raise OctreeInvalid('unique MEM2 KCL candidate not found')
        return source['hole'], inspect_octree(banks[1], hits[0][0])


def analyze_archive(archive: Path, captures=CAPTURES):
    import audit_p0_seven_numbered_source_pairs_private as seven
    from audit_p0_seven_numbered_source_pairs_private import roster
    if (not captures or any(type(n) is not int or n not in range(1,8) for n in captures)
            or len(set(captures)) != len(captures)):
        raise ValueError('invalid capture numbers')
    folders = seven._check_archive(archive)
    reports = []
    for number in captures:
        try:
            hole, evidence = _read_one(folders, number, seven, roster)
        except OctreeUnsupported as exc:
            # Preserve the failing *numbered* phase, but no native address.
            exc.capture_number = number
            raise
        reports.append({'capture_number':number,'source_hole_index':hole,**evidence})
    seven._check_archive(archive)
    return {
        'kind':'P0_PRIVATE_KCL_OCTREE_REFERENCE_TRIAGE',
        'status':'OCTREE_FORMAT_CANDIDATE_VALIDATED',
        'capture_reports':reports,
        'game_uses_this_octree_for_collision_verified':False,
        'course_terrain_visual_alignment_verified':False,
        'world_coordinate_transform_verified':False,
        'training_approved':False,
        'allowed_to_publish':False,
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archive', required=True, type=Path)
    p.add_argument('--captures', nargs='+', type=int, default=list(CAPTURES))
    a = p.parse_args(argv)
    try:
        print(json.dumps(analyze_archive(a.archive, tuple(a.captures)),
                         indent=2, sort_keys=True))
        return 0
    except OctreeUnsupported as exc:
        print(json.dumps({'kind':'P0_PRIVATE_KCL_OCTREE_REFERENCE_TRIAGE',
                          'status':'OCTREE_LAYOUT_VARIANT_UNRESOLVED',
                          'capture_number':getattr(exc, 'capture_number', None),
                          'reason_code':_SAFE_UNSUPPORTED_REASONS.get(
                              str(exc), 'UNCLASSIFIED_OCTREE_LAYOUT_VARIANT'),
                          'game_uses_this_octree_for_collision_verified':False,
                          'training_approved':False, 'allowed_to_publish':False}))
        return 4
    except (OSError, ValueError, TypeError, KeyError, IndexError,
            OverflowError, AttributeError, struct.error):
        print(json.dumps({'kind':'P0_PRIVATE_KCL_OCTREE_REFERENCE_TRIAGE',
                          'status':'ABSTAIN_SOURCE_OR_OCTREE_REFERENCE_GATE',
                          'game_uses_this_octree_for_collision_verified':False,
                          'training_approved':False, 'allowed_to_publish':False}))
        return 3


if __name__ == '__main__':
    raise SystemExit(main())
