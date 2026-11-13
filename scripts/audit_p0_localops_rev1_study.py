#!/usr/bin/env python3
"""Read-only, bounded Rev1 source archive preflight and nonlinear PPC audit.

For manually approved LocalOps `run_research`, with --stage=preflight or
--stage=nonlinear. Scans ONLY known one/two-level sibling Data locations,
verifies all 14 preserved bank SHA-256 values and identity BEFORE source reads,
rechecks afterward, and emits only source PCs and sanitized status. Does not
launch or connect to Dolphin, write files, disclose private paths/bytes, or
claim executed shot/physics semantics. No dependency on environmental secrets.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import struct
import sys

MEM1_BASE = 0x80000000
MEM1_SIZE = 0x01800000
MEM2_SIZE = 0x04000000
PHASES = tuple(range(1, 8))
SOURCE_WINDOWS = ((0x802A3CF4, 0x802A3DE4),
                  (0x802B2E34, 0x802B2EF8),
                  (0x802A79F8, 0x802C7924))
MAX_SIBLINGS = 80
MAX_ARCHIVES = 30


class Abstain(Exception):
    """Do not interpolate private exception messages into public output."""
    def __init__(self, code: str):
        super().__init__('qualification incomplete')
        self.code = code


def _regular(path: pathlib.Path, size: int | None = None) -> bool:
    try:
        return (path.is_file() and not path.is_symlink() and
                (size is None or path.stat().st_size == size))
    except OSError:
        return False


def _manifest_descriptor(manifest: object) -> tuple[tuple[int, int, str, str], ...]:
    """Validate manifest structure before opening private native banks."""
    if (type(manifest) is not dict or
            manifest.get('kind') != 'p0-private-numbered-capture-inventory' or
            manifest.get('training_approved') is not False or
            manifest.get('human_phase_file_mapping_verified') is not False or
            type(manifest.get('capture_count')) is not int or
            manifest['capture_count'] != 7 or
            manifest.get('capture_numbers') != list(PHASES) or
            type(manifest.get('captures')) is not list or
            len(manifest['captures']) != 7):
        raise Abstain('MANIFEST_IDENTITY')
    result = []
    found = set()
    for item in manifest['captures']:
        if type(item) is not dict:
            raise Abstain('MANIFEST_ROWS')
        phase = item.get('capture_number')
        banks = item.get('banks')
        if (type(phase) is not int or phase not in PHASES or phase in found or
                type(banks) is not list or len(banks) != 2):
            raise Abstain('MANIFEST_ROWS')
        found.add(phase)
        for i, (bank, size) in enumerate((('MEM1', MEM1_SIZE),
                                          ('MEM2', MEM2_SIZE)), start=1):
            row = banks[i - 1]
            filename = f'{phase}.{i}.raw'
            if (type(row) is not dict or row.get('file') != filename or
                    row.get('bank') != bank or row.get('bytes') != size or
                    row.get('copy_verified') is not True or
                    type(row.get('sha256')) is not str or
                    re.fullmatch(r'[0-9a-fA-F]{64}', row['sha256']) is None):
                raise Abstain('MANIFEST_ROWS')
            result.append((phase, size, filename, row['sha256'].lower()))
    if found != set(PHASES):
        raise Abstain('MANIFEST_ROWS')
    return tuple(sorted(result))


def _find_candidates(checkout: pathlib.Path) -> tuple[tuple[pathlib.Path, str], ...]:
    """No broad disk walk. Only immediate checkout siblings and their children."""
    parent = checkout.parent
    if not parent.is_dir() or parent.is_symlink():
        raise Abstain('CHECKOUT_ROOT')
    try:
        items = sorted((x for x in parent.iterdir() if x.is_dir() and
                        not x.is_symlink() and not x.name.startswith('.')),
                       key=lambda p: p.name.lower())
    except OSError:
        raise Abstain('CHECKOUT_ROOT') from None
    if len(items) > MAX_SIBLINGS:
        raise Abstain('TOO_MANY_SIBLINGS')
    roots = [(parent / 'Wii-AI-Golf-Data', 'direct-sibling')]
    roots.extend((p / 'Wii-AI-Golf-Data', 'nested-sibling') for p in items)
    archives = []
    for data, label in roots:
        if not data.is_dir() or data.is_symlink():
            continue
        captures = data / 'captures'
        if not captures.is_dir() or captures.is_symlink():
            continue
        try:
            subs = sorted((p for p in captures.iterdir() if p.is_dir() and
                           not p.is_symlink()), key=lambda x: x.name)
        except OSError:
            raise Abstain('CAPTURE_LISTING') from None
        if len(subs) > MAX_ARCHIVES:
            raise Abstain('TOO_MANY_ARCHIVES')
        for sub in subs:
            mf = sub / 'manifest-PRIVATE.json'
            if not _regular(mf) or mf.stat().st_size > 65536:
                continue
            try:
                content = json.loads(mf.read_text(encoding='utf-8-sig'))
            except (UnicodeError, ValueError, OSError):
                continue
            if isinstance(content, dict) and content.get('kind') == (
                    'p0-private-numbered-capture-inventory'):
                archives.append((sub, label))
    # No ambiguous or silently selected evidence cohorts.
    if len(archives) != 1:
        raise Abstain('NO_CANONICAL_ARCHIVE' if not archives else 'AMBIGUOUS_ARCHIVE')
    return tuple(archives)


def _sha(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def _validate_banks(archive: pathlib.Path) -> tuple[tuple[int, int, pathlib.Path, str], ...]:
    mf = archive / 'manifest-PRIVATE.json'
    if not _regular(mf) or mf.stat().st_size > 65536:
        raise Abstain('MANIFEST_FILE')
    try:
        entries = _manifest_descriptor(json.loads(mf.read_text(encoding='utf-8-sig')))
    except (ValueError, UnicodeError, OSError):
        raise Abstain('MANIFEST_FILE') from None
    banks = []
    for phase, size, name, expected in entries:
        path = archive / name
        if not _regular(path, size):
            raise Abstain('BANK_MISSING_OR_SIZE')
        if _sha(path) != expected:
            raise Abstain('ORIGINAL_SHA_MISMATCH')
        banks.append((phase, size, path, expected))
    # MEM1 captures should reflect the Rev1 game header, not merely length.
    for phase, _size, path, _expected in banks:
        if path.name != f'{phase}.1.raw':
            continue
        with path.open('rb') as stream:
            head = stream.read(8)
        if len(head) != 8 or head[:6] != b'RSPE01' or head[7] != 1:
            raise Abstain('REV1_HEADER')
    return tuple(banks)


def _read_windows(mem1: pathlib.Path, windows=SOURCE_WINDOWS) -> dict[tuple[int, int], bytes]:
    result = {}
    with mem1.open('rb') as fh:
        for begin, end in windows:
            if not (MEM1_BASE <= begin < end <= MEM1_BASE + MEM1_SIZE and
                    begin % 4 == 0 and end % 4 == 0):
                raise Abstain('SOURCE_BOUNDS')
            fh.seek(begin - MEM1_BASE)
            data = fh.read(end - begin)
            if len(data) != end - begin or not any(data):
                raise Abstain('SOURCE_WINDOW_MISSING')
            result[begin, end] = data
    return result


def _word(windows: dict[tuple[int, int], bytes], pc: int) -> int:
    for (lo, hi), data in windows.items():
        if lo <= pc < hi - 3:
            return struct.unpack_from('>I', data, pc-lo)[0]
    raise Abstain('SOURCE_PC_UNMAPPED')


def _branch(pc: int, value: int) -> int | None:
    if (value >> 26) != 18 or (value & 1) == 0:
        return None
    disp = value & 0x03fffffc
    if disp & 0x02000000:
        disp -= 0x04000000
    return (disp if value & 2 else pc + disp) & 0xffffffff


def _source_gates(read) -> dict:
    calls = {
        0x802A3D6C: 0x8002F7E8,  # NW4R FLog first
        0x802A3D90: 0x8002F7E8,  # NW4R FLog second
        0x802A3DA8: 0x8002F75C,  # NW4R FExp
        0x802B2ECC: 0x8002F898,  # NW4R SinFIdx
    }
    if any(_branch(pc, read(pc)) != target for pc, target in calls.items()):
        raise Abstain('NATIVE_CALL_GATE')
    end = read(0x802A3DE0)
    if (end >> 26) != 19 or (end >> 1) & 0x3ff != 16:
        raise Abstain('NATIVE_HELPER_RETURN_GATE')
    for pc, offset in ((0x802B2ED4, 0x1b4), (0x802B2EF4, 0x1b0)):
        w = read(pc)
        if (w >> 26) != 52 or (w & 0xffff) != offset:
            raise Abstain('NATIVE_RESULT_STORE_GATE')
    first, last = SOURCE_WINDOWS[1]
    helper_calls = [pc for pc in range(first, last, 4)
                    if _branch(pc, read(pc)) == 0x802A3CF4]
    if len(helper_calls) != 2:
        raise Abstain('NATIVE_NONLINEAR_CALL_GATE')
    return {'f_log_direct_calls': 2, 'f_exp_direct_calls': 1,
            'sin_fidx_call_gated': True,
            'nonlinear_helper_call_pcs': [f'0x{pc:08X}' for pc in helper_calls],
            'derived_scalar_stores_gated': ['+0x1B4', '+0x1B0']}


def _lexical_consumers(windows: dict[tuple[int, int], bytes]) -> dict:
    lo, hi = SOURCE_WINDOWS[2]
    data = windows[lo, hi]
    result = {}
    for offset in (0x1b0, 0x1b4, 0x1b8):
        rows = []
        for ix in range(0, len(data), 4):
            op = struct.unpack_from('>I', data, ix)[0]
            if (op >> 26) in (48, 52) and (op & 0xffff) == offset:
                rows.append((lo+ix, 'lfs' if (op >> 26) == 48 else 'stfs'))
        result[f'+0x{offset:03X}'] = {
            'lexical_dform_count': len(rows),
            'sample_pc_operation': [f'0x{pc:08X}:{op}' for pc, op in rows[:6]],
            'receiver_proven': False,
        }
    return result


def _source_owners() -> bool:
    scripts_root = str(pathlib.Path(__file__).resolve().parent)
    if scripts_root not in sys.path:
        sys.path.insert(0, scripts_root)
    import audit_ball_xyz_source_callers_private as source
    intervals = source.load_public_text_units()
    expected = ((0x802A3CF4, 'RPGolMathTrig.cpp'),
                (0x802B2ECC, 'RPGolScene_unsplit.o'),
                (0x8002F898, 'math_triangular.cpp'))
    return all(any(lo <= pc < hi and suffix in name for lo, hi, name in intervals)
               for pc, suffix in expected)


def study(stage: str, checkout: pathlib.Path) -> dict:
    if not _source_owners():
        raise Abstain('PUBLIC_REV1_UNIT_MAP')
    ((archive, topology),) = _find_candidates(checkout)
    banks = _validate_banks(archive)
    report = {'status':'PREFLIGHT_PASS', 'stage':stage,
              'archive_topology':topology,
              'original_bank_sha_verified':len(banks),
              'public_rev1_unit_source_verified':True,
              'training_approved':False, 'allowed_to_publish':False}
    if stage == 'nonlinear':
        phase_files = {p:path for p,size,path,sha in banks if size == MEM1_SIZE}
        views = [_read_windows(phase_files[p]) for p in (1,5,7)]
        if views[0] != views[1] or views[1] != views[2]:
            raise Abstain('PHASE_SOURCE_NOT_IDENTICAL')
        report['phase_1_5_7_source_windows_identical'] = True
        report['native_gate_summary'] = _source_gates(lambda pc:_word(views[0],pc))
        report['lexical_calc_offset_census'] = _lexical_consumers(views[0])
        report['status'] = 'NONLINEAR_SOURCE_PASS'
        report['same_shot_native_ball_consumer_verified'] = False
        report['lexical_matches_are_receiver_proof'] = False
    # Independently recheck original 14 SHA values after all reads.
    second = _validate_banks(archive)
    if len(second) != 14 or tuple(x[3] for x in second) != tuple(x[3] for x in banks):
        raise Abstain('POST_SOURCE_SHA_GATE')
    report['original_sha_post_verified'] = True
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', required=True, choices=('preflight','nonlinear'))
    args = parser.parse_args(argv)
    try:
        result = study(args.stage, pathlib.Path(__file__).resolve().parents[1])
    except (Abstain, OSError, ValueError, KeyError, TypeError,
            UnicodeError, struct.error) as exc:
        code = exc.code if type(exc) is Abstain else 'UNQUALIFIED_PRIVATE_SOURCE'
        result = {'status':'ABSTAIN', 'stage':args.stage,'reason_code':code,
                  'training_approved':False, 'allowed_to_publish':False}
    print(json.dumps(result, sort_keys=True, separators=(',',':')))
    return 0 if result['status'] != 'ABSTAIN' else 2


if __name__ == '__main__':
    raise SystemExit(main())