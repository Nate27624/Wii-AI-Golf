#!/usr/bin/env python3
"""Read-only RSPE01 rev1 candidate golf tee/pin geometry from private RAM dumps.

Source-derived layout is hypothetical until game controls corroborate it.
Do not publish JSON: dynamic pointers and coordinates are private research data.
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path
import struct
import sys

MEM1_BASE, MEM1_LEN = 0x80000000, 0x01800000
MEM2_BASE, MEM2_LEN = 0x90000000, 0x04000000
FIELD_MANAGER_SINGLETON = 0x804BF868
CURRENT_PIN = 0x44
CURRENT_START = 0x50
CUP_OBJECT = 0x54  # cup subclass layout at +0x30 is UNVERIFIED
NUM_TARGET_OBJECTS = 0x30
TARGET_OBJECTS_ARRAY = 0x34
TRANSLATION = 0x30

class DiagnosticError(Exception):
    pass

class DumpBanks:
    def __init__(self, mem1: Path, mem2: Path):
        self.files = [(MEM1_BASE, MEM1_LEN, Path(mem1)), (MEM2_BASE, MEM2_LEN, Path(mem2))]
        self.handles = []
    def __enter__(self):
        for base, length, path in self.files:
            if path.stat().st_size != length:
                raise DiagnosticError(f"{path.name}: expected {length} bytes")
        try:
            self.handles = [p.open('rb') for _, _, p in self.files]
        except Exception:
            for h in self.handles: h.close()
            raise
        return self
    def __exit__(self, *_):
        for h in self.handles: h.close()
    def read(self, address: int, size: int) -> bytes:
        if size <= 0: raise DiagnosticError('invalid read size')
        for (base, length, _), handle in zip(self.files, self.handles):
            if base <= address and address + size <= base + length:
                handle.seek(address - base)
                data = handle.read(size)
                if len(data) != size: raise DiagnosticError('short RAM read')
                return data
        raise DiagnosticError(f"invalid memory address 0x{address:08X} (size={size})")
    def word(self, address: int) -> int:
        if address & 3: raise DiagnosticError(f"unaligned address 0x{address:08X}")
        return struct.unpack('>I', self.read(address, 4))[0]
    def vec3(self, address: int) -> list[float]:
        return list(struct.unpack('>fff', self.read(address, 12)))

def object_pointer(banks: DumpBanks, addr: int, what: str) -> int:
    ptr = banks.word(addr)
    if ptr == 0 or ptr & 3:
        raise DiagnosticError(f"{what}: null or unaligned pointer 0x{ptr:08X}")
    banks.read(ptr, 0x4C)
    return ptr

def inspect(banks: DumpBanks) -> dict:
    game = banks.read(MEM1_BASE, 4)
    revision = banks.read(MEM1_BASE + 7, 1)[0]
    if game != b'RSPE' or revision != 1:
        raise DiagnosticError(f"RSPE US rev1 only: game {game!r}, revision {revision}")
    manager = object_pointer(banks, FIELD_MANAGER_SINGLETON, 'RPGolFieldManager singleton')
    output = {"status": "source_layout_candidate", "singleton": f"0x{FIELD_MANAGER_SINGLETON:08X}",
              "field_manager": f"0x{manager:08X}", "observations": {},
              "verified_ball_world_xyz": False, "verified_target_xyz": False,
              "approved_for_training": False}
    for name, field in (("pin", CURRENT_PIN), ("start", CURRENT_START)):
        entry = {"manager_field": f"0x{manager + field:08X}"}
        try:
            ptr = object_pointer(banks, manager + field, name)
            entry['object_pointer'] = f"0x{ptr:08X}"
            trans = banks.vec3(ptr + TRANSLATION)
            if not all(math.isfinite(v) and abs(v) <= 1e7 for v in trans):
                raise DiagnosticError('non-finite or unreasonably large translation')
            entry['candidate_translation_xyz'] = [round(v, 7) for v in trans]
            entry['status'] = 'finite_source_layout_candidate'
        except DiagnosticError as exc:
            entry['status'] = 'rejected'
            entry['reason'] = str(exc)
        output['observations'][name] = entry
    # Optional related objects; no assumptions about Target array element size.
    # A cup object's subclass/base offset has NOT been verified.
    extra = {}
    try:
        ptr = object_pointer(banks, manager + CUP_OBJECT, 'cup')
        translation = banks.vec3(ptr + TRANSLATION)
        if not all(math.isfinite(v) and abs(v) <= 1e7 for v in translation):
            raise DiagnosticError('non-finite or too-large cup translation hypothesis')
        extra['cup'] = {'status': 'unverified_base_layout_hypothesis',
                        'object_pointer': f"0x{ptr:08X}",
                        'candidate_translation_xyz': [round(v, 7) for v in translation]}
    except DiagnosticError as exc:
        extra['cup'] = {'status': 'no_usable_cup_candidate', 'reason': str(exc)}
    try:
        count = banks.word(manager + NUM_TARGET_OBJECTS)
        array = banks.word(manager + TARGET_OBJECTS_ARRAY)
        # This is collection metadata only, not a validated per-target array layout.
        if count > 1024:
            raise DiagnosticError(f'implausible target count {count}')
        if count:
            if array == 0 or array & 3:
                raise DiagnosticError('non-empty target array null/unaligned')
            banks.read(array, 4)
        extra['target_collection'] = {
            'status': 'unverified_collection_metadata',
            'count_candidate': count,
            'array_pointer_candidate': f"0x{array:08X}"}
    except DiagnosticError as exc:
        extra['target_collection'] = {'status': 'no_usable_target_collection', 'reason': str(exc)}
    output['optional_context'] = extra

    if all(x['status'] == 'finite_source_layout_candidate' for x in output['observations'].values()):
        output['status'] = 'two_candidate_translations_found_not_verified'
    else:
        output['status'] = 'incomplete_or_invalid_chain'
    return output

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--study', required=True, type=Path,
                        help='private directory with B0..B3-MEM1.bin and -MEM2.bin')
    parser.add_argument('--captures', nargs='+', default=['B0', 'B1', 'B2', 'B3'])
    args = parser.parse_args(argv)
    rows = []
    for capture in args.captures:
        if not capture.isalnum():
            print('invalid capture name', file=sys.stderr)
            return 2
        try:
            with DumpBanks(args.study / f'{capture}-MEM1.bin',
                           args.study / f'{capture}-MEM2.bin') as banks:
                result = inspect(banks)
                result['capture'] = capture
        except (OSError, DiagnosticError, struct.error) as exc:
            result = {'capture': capture, 'status': 'error', 'reason': str(exc)}
        rows.append(result)
    for role in ('pin', 'start'):
        series = [r.get('observations', {}).get(role, {}).get('candidate_translation_xyz') for r in rows]
        valid = [tuple(x) for x in series if x is not None]
        comparison = 'all_same' if len(valid) == len(rows) and len(set(valid)) == 1 else (
            'different' if len(valid) == len(rows) else 'incomplete')
        for row in rows:
            row.setdefault('cross_capture', {})[f'{role}_translation'] = comparison
    print(json.dumps({'kind': 'PRIVATE-offline-golf-geometry-candidate', 'source': 'RSPE01 rev1',
                      'verified': False, 'results': rows}, indent=2))
    return 0 if all(r['status'] == 'two_candidate_translations_found_not_verified' for r in rows) else 1

if __name__ == '__main__':
    raise SystemExit(main())
