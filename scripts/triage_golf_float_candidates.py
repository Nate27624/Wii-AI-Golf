#!/usr/bin/env python3
"""Read-only, PRIVATE triage of candidate changing float triplets in RSPE01 rev1.

This requires the alias audit from the SAME capture study; reports hypotheses,
not ball positions. Never commit local JSON reports or RAM banks to GitHub.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
import math
from pathlib import Path
import struct
import sys

FLOAT_REGION = 0x80B56D40
METADATA_REGION = 0x933E0000


def float_value(data: bytes) -> float:
    return struct.unpack('>f', data)[0]


def plausible(value: float) -> bool:
    return math.isfinite(value) and abs(value) <= 1e6


def triage(banks, audit_report: dict) -> dict:
    root = banks.validate_root()
    if audit_report.get('root_pointer') != f'0x{root:08X}':
        raise ValueError('alias report root does not match loaded RAM snapshots')
    if audit_report.get('captures') != list(banks.names):
        raise ValueError('alias report capture IDs/order do not match RAM snapshots')
    if audit_report.get('coverage_status') not in ('complete', 'bounded_partial'):
        raise ValueError('alias report missing declared coverage status')

    verified_changed = []
    for row in audit_report.get('unique_changed_addresses_outside_root', []):
        addr = int(row['address'], 16)
        if not banks.valid(addr, 4):
            raise ValueError(f'invalid reported change address: {row["address"]}')
        actual = [banks.read(name, addr, 4).hex().upper() for name in banks.names]
        if actual != row['values'] or len(set(actual)) < 2:
            raise ValueError(f'alias report does not match captures at 0x{addr:08X}')
        verified_changed.append(addr)

    candidate_windows = []
    for start in (FLOAT_REGION - 4, FLOAT_REGION, FLOAT_REGION + 4):
        vectors = [struct.unpack('>fff', banks.read(n, start, 12)) for n in banks.names]
        if not all(plausible(f) for xyz in vectors for f in xyz):
            continue
        changed = [len({xyz[j] for xyz in vectors}) > 1 for j in range(3)]
        candidate_windows.append({
            'address': f'0x{start:08X}',
            'vectors_by_capture': {
                n: [round(f, 6) for f in xyz] for n, xyz in zip(banks.names, vectors)},
            'varying_components_xyz': changed,
            'varying_component_count': sum(changed),
            'status': 'float_window_hypothesis_only_not_verified_ball_xyz'
        })

    focus_words = []
    for addr in range(FLOAT_REGION - 16, FLOAT_REGION + 24, 4):
        raw = [banks.read(n, addr, 4).hex().upper() for n in banks.names]
        floats = [float_value(bytes.fromhex(x)) for x in raw]
        focus_words.append({
            'address': f'0x{addr:08X}',
            'raw_words': raw,
            'floats': ([round(f, 6) for f in floats]
                       if all(plausible(f) and (abs(f) >= 1e-5 or f == 0)
                              for f in floats) else None),
            'varies': len(set(raw)) > 1,
        })

    source_regions = []
    for row in audit_report.get('ranked_pointees', []):
        if row.get('changed_words_outside_4k_root', 0) <= 0:
            continue
        ptr = int(row['pointee'], 16)
        source_regions.append({
            'pointee': row['pointee'],
            'source_references': row['references'],
            'changed_count_in_512b': row['changed_words_outside_4k_root'],
            'covers_float_window': ptr <= FLOAT_REGION and ptr + 512 >= FLOAT_REGION + 12,
            'covers_metadata_window': ptr <= METADATA_REGION + 0x60 < ptr + 512,
        })

    return {
        'kind': 'PRIVATE-offline-float-candidate-triage',
        'verified_ball_world_xyz': False,
        'approved_for_training': False,
        'source_audit_coverage': audit_report['coverage_status'],
        'report_changed_addresses_verified_against_banks': len(verified_changed),
        'report_total_changed_addresses': audit_report.get('total_unique_changed_addresses_outside_root'),
        'float_word_context': focus_words,
        'vector_hypotheses': candidate_windows,
        'provenance': source_regions,
        'note': 'B0–B3 capture phase and real contact/ball movement are not independently verified. '
                'Two changing adjacent floats are not proof of a ball-position vector.'
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--study', required=True, type=Path)
    parser.add_argument('--report', type=Path)
    parser.add_argument('--captures', nargs='+', default=['B0','B1','B2','B3'])
    args = parser.parse_args(argv)
    alias_script = Path(__file__).with_name('audit_golf_main_aliases.py')
    if not alias_script.is_file():
        print(f'ABORT: missing pinned dependency {alias_script}', file=sys.stderr)
        return 2
    spec = importlib.util.spec_from_file_location('pinned_alias_reader', alias_script)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    path = args.report or args.study / 'golf-main-alias-audit-v2.json'
    try:
        report = json.loads(path.read_text(encoding='utf-8-sig'))
        with mod.Captures(args.study, args.captures) as banks:
            result = triage(banks, report)
    except (OSError, ValueError, KeyError, TypeError, mod.ReadError) as exc:
        print(f'ABORT: {exc}', file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
