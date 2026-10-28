#!/usr/bin/env python3
"""PRIVATE/read-only RSPE01 rev1 alias-aware RPGolMain pointer-difference audit.

Finds changed absolute RAM words reached by stable 1- or 2-hop pointers. This
does NOT identify dynamic ball position, object sizes, or shot phases.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import struct
import sys

BANKS = (('MEM1', 0x80000000, 0x01800000), ('MEM2', 0x90000000, 0x04000000))
SCENE_MGR_SLOT = 0x804BF4D8
ROOT_BYTES = 4096
ROOT_POINTER_BYTES = 512
CHILD_BYTES = 512
SECOND_POINTER_BYTES = 128


class ReadError(Exception):
    pass


class Captures:
    def __init__(self, study: Path, names: list[str]):
        self.names = names
        self.study = study
        self.handles = {}
    def __enter__(self):
        try:
            for name in self.names:
                if not name.isalnum():
                    raise ReadError('invalid capture name')
                for bank, _, length in BANKS:
                    file = self.study / f'{name}-{bank}.bin'
                    if file.stat().st_size != length:
                        raise ReadError(f'{name} {bank}: incorrect bank size')
                    self.handles[(name, bank)] = file.open('rb')
            return self
        except Exception:
            self.__exit__(None, None, None)
            raise
    def __exit__(self, *_):
        for handle in self.handles.values():
            handle.close()
        self.handles.clear()
    @staticmethod
    def valid(addr: int, size: int) -> bool:
        return bool(addr % 4 == 0 and size > 0 and any(
            base <= addr and addr + size <= base + length
            for _, base, length in BANKS))
    def read(self, name: str, addr: int, size: int) -> bytes:
        for bank, base, length in BANKS:
            if base <= addr and addr + size <= base + length:
                handle = self.handles[(name, bank)]
                handle.seek(addr - base)
                result = handle.read(size)
                if len(result) != size:
                    raise ReadError(f'{name}: short read at 0x{addr:08X}')
                return result
        raise ReadError(f'{name}: unmapped address 0x{addr:08X}')
    def word(self, name: str, addr: int) -> int:
        if addr % 4:
            raise ReadError(f'unaligned word at 0x{addr:08X}')
        return struct.unpack('>I', self.read(name, addr, 4))[0]
    def validate_root(self) -> int:
        mains = []
        for name in self.names:
            if self.read(name, 0x80000000, 4) != b'RSPE' or self.read(name, 0x80000007, 1) != b'\x01':
                raise ReadError(f'{name}: not RSPE01 US revision 1')
            manager = self.word(name, SCENE_MGR_SLOT)
            if not self.valid(manager, 0x1C):
                raise ReadError(f'{name}: invalid scene manager')
            scene = self.word(name, manager + 0x0C)
            if not self.valid(scene, 0xA0):
                raise ReadError(f'{name}: invalid scene object')
            if self.word(name, manager + 0x18) != 5 or self.word(name, scene + 0x1C) != 5:
                raise ReadError(f'{name}: not Golf scene 5')
            if self.word(name, scene + 0x20) != manager:
                raise ReadError(f'{name}: manager/scene cross-check fails')
            main = self.word(name, scene + 0x9C)
            if not self.valid(main, ROOT_BYTES):
                raise ReadError(f'{name}: invalid golf main pointer')
            mains.append(main)
        if len(set(mains)) != 1:
            raise ReadError('different RPGolMain addresses across captures: cannot compare absolute words')
        return mains[0]


def changed_words(captures: Captures, addr: int, length: int) -> dict[int, list[str]]:
    samples = [captures.read(name, addr, length) for name in captures.names]
    changes = {}
    for offset in range(0, length, 4):
        vals = [s[offset:offset+4] for s in samples]
        if len(set(vals)) > 1:
            changes[addr + offset] = [x.hex().upper() for x in vals]
    return changes


def stable_pointers(captures: Captures, start: int, length: int) -> list[tuple[int, int]]:
    found = []
    for off in range(0, length, 4):
        vals = [captures.word(name, start + off) for name in captures.names]
        ptr = vals[0]
        if len(set(vals)) == 1 and captures.valid(ptr, CHILD_BYTES):
            found.append((off, ptr))
    return found


def analyze(captures: Captures, depth: int = 2, max_nodes: int = 256) -> dict:
    root = captures.validate_root()
    root_changes = changed_words(captures, root, ROOT_BYTES)
    # Each pointer is keyed by the referenced ADDRESS, not the source-field offset.
    references = defaultdict(list)
    first = stable_pointers(captures, root, ROOT_POINTER_BYTES)
    for off, ptr in first:
        references[ptr].append(f'main+0x{off:03X}')
    first_ptrs = list(references)
    if depth == 2:
        for parent in first_ptrs:
            for off, ptr in stable_pointers(captures, parent, SECOND_POINTER_BYTES):
                references[ptr].append(f'0x{parent:08X}+0x{off:03X}')
                if len(references) > max_nodes:
                    raise ReadError(f'pointer graph exceeded {max_nodes} unique nodes: do not report a partial audit')
    if len(references) > max_nodes:
        raise ReadError(f'too many pointer nodes: {len(references)}')
    unique_new = {}
    rows = []
    for ptr, sources in references.items():
        changes = changed_words(captures, ptr, CHILD_BYTES)
        outside_root = {addr: vals for addr, vals in changes.items()
                        if not root <= addr < root + ROOT_BYTES}
        unique_new.update(outside_root)
        rows.append({
            'pointee': f'0x{ptr:08X}',
            'references': sorted(set(sources))[:6],
            'additional_reference_count': max(0, len(set(sources)) - 6),
            'overlaps_4k_root': (ptr < root + ROOT_BYTES and ptr + CHILD_BYTES > root),
            'changed_words_in_window': len(changes),
            'changed_words_outside_4k_root': len(outside_root),
            'new_change_addresses': [f'0x{x:08X}' for x in sorted(outside_root)[:8]],
        })
    rows.sort(key=lambda r: (-r['changed_words_outside_4k_root'],
                             -r['changed_words_in_window'], r['pointee']))
    return {
        'kind': 'PRIVATE-RPGolMain-alias-aware-audit',
        'verified_ball_world_xyz': False, 'approved_for_training': False,
        'root_pointer': f'0x{root:08X}',
        'captures': captures.names, 'max_pointer_depth': depth,
        'root_4k_changed_words': [
            {'address': f'0x{a:08X}', 'root_offset': f'0x{a-root:03X}', 'values': v}
            for a, v in sorted(root_changes.items())],
        'stable_pointer_fields_512b': len(first),
        'unique_first_hop_pointees': len(first_ptrs),
        'unique_pointees_all_hops': len(references),
        'unique_changed_addresses_outside_root': [
            {'address': f'0x{a:08X}', 'values': v}
            for a, v in sorted(unique_new.items())[:40]],
        'total_unique_changed_addresses_outside_root': len(unique_new),
        'ranked_pointees': rows[:30],
        'note': 'Overlapping window aliases are not independent changes. '
                'A changed word outside this window is not necessarily ball physics.'
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--study', required=True, type=Path)
    parser.add_argument('--captures', nargs='+', default=['B0','B1','B2','B3'])
    parser.add_argument('--depth', type=int, default=2, choices=[1,2])
    args = parser.parse_args(argv)
    try:
        with Captures(args.study, args.captures) as captures:
            result = analyze(captures, args.depth)
    except (ReadError, OSError, struct.error) as exc:
        print(f'ABORT: {exc}', file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
