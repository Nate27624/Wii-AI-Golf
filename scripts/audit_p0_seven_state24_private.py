"""Seven-phase selected-player +0x024 *shape* crosswalk (offline, private).

Inherits PR #231's SHA, revision, scene and selected source-owner reader. The
known source writer literal set 1..5 was separately established by PR #162;
this tool neither re-disassembles the writer nor names its runtime semantics.
Only source-relative equality classes and guarded booleans are emitted.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import json
import mmap
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit_p0_seven_numbered_source_pairs_private as upstream

STATE_WORD_INDEX = 0x24 // 4
KNOWN_SOURCE_LITERALS = frozenset((1, 2, 3, 4, 5))
WITHIN_SHOT = ((1, 2), (5, 6), (6, 7), (5, 7))
CLUB_CONFOUNDED = (3, 4)


def _state_word(sample: dict) -> int:
    whole = sample.get('whole_record')
    if not isinstance(whole, (tuple, list)) or len(whole) != 51:
        raise ValueError('selected player record not 51 words')
    v = whole[STATE_WORD_INDEX]
    if type(v) is not int or not 0 <= v <= 0xFFFFFFFF:
        raise ValueError('invalid selected player state word')
    return v


def _triplet(sample: dict, key: str) -> tuple:
    triplets = sample['triplets']
    x = triplets[key]
    if not isinstance(x, (list, tuple)) or len(x) != 3 or not all(type(v) is int for v in x):
        raise ValueError('invalid source-selected geometry triplet')
    return tuple(x)


def _same_geometry(a: dict, b: dict) -> bool:
    keys = ('field', 'pin_obj', 'start_obj', 'cfg_bc', 'cfg_c0', 'cfg_c4')
    pin_a, pin_b = a['pin'], b['pin']
    if not all(isinstance(p, (tuple, list)) and len(p) == 3 and
               all(type(v) is int for v in p) for p in (pin_a, pin_b)):
        raise ValueError('invalid source pin translation')
    return (all(a[k] == b[k] for k in keys) and
            tuple(pin_a) == tuple(pin_b) and
            _triplet(a, 'source_current_start') == _triplet(b, 'source_current_start'))


def _selected_chain_stable(a: dict, b: dict) -> bool:
    return (
        a['selected_index'] == b['selected_index'] and
        a['hole'] == b['hole'] and
        # The source selected player's record+0x88 is the linked ball object.
        a['whole_record'][0x88 // 4] == b['whole_record'][0x88 // 4] and
        _same_geometry(a, b)
    )


def summarize(samples: dict[int, dict]) -> dict:
    if set(samples) != set(range(1, 8)):
        raise ValueError('exactly seven numbered source-gated samples required')
    words = {n: _state_word(samples[n]) for n in range(1, 8)}
    # Opaque, deterministic FIRST-APPEARANCE labels. Never emit u32 values,
    # their hashes, or a table mapping labels to private source values.
    opaque = {}
    rows = []
    for n in range(1, 8):
        v = words[n]
        if v not in opaque:
            opaque[v] = f'group_{len(opaque)+1}'
        rows.append({
            'number': n,
            'equality_group': opaque[v],
            'is_zero': v == 0,
            'in_source_1_to_5_literal_set': v in KNOWN_SOURCE_LITERALS,
            'unexpected_nonzero_value': v != 0 and v not in KNOWN_SOURCE_LITERALS,
            'phase_label_machine_verified': False,
        })

    edges = []
    for a, b in (*WITHIN_SHOT, CLUB_CONFOUNDED):
        x, y = samples[a], samples[b]
        if not _selected_chain_stable(x, y):
            raise ValueError('source-selected owner/ball or geometry changed')
        ball_a = _triplet(x, 'ball_object_0x030')
        ball_b = _triplet(y, 'ball_object_0x030')
        edges.append({
            'transition': f'{a}_to_{b}',
            'same_shot_human_note_only': (a, b) in WITHIN_SHOT,
            'different_clubs_or_input_confound': (a, b) == CLUB_CONFOUNDED,
            'selected_owner_ball_geometry_verified_stable': True,
            'state24_changed': words[a] != words[b],
            'ball_candidate_changed_components': sum(p != q for p, q in zip(ball_a, ball_b)),
            'causal_swing_or_physical_semantics_verified': False,
        })

    return {
        'kind': 'P0-SEVEN-SOURCE-SELECTED-STATE24-EQUALITY-ONLY',
        'archive_sha_and_rev1_selection_gated_by_upstream': True,
        'selected_player_record_relative_offset': '+0x024',
        'source_writer_literal_set_historically_documented': True,
        'source_writer_instructions_reverified_in_this_study': False,
        'distinct_private_state_values_count': len(opaque),
        'snapshots': rows,
        'comparisons': edges,
        'phase_mapping_machine_verified': False,
        'same_guest_frame_per_pair_verified': False,
        'same_boot_verified': False,
        'actual_game_state_enum_decoded': False,
        'shot_state_verified': False,
        'ball_world_xyz_verified': False,
        'ball_velocity_verified': False,
        'shot_power_verified': False,
        'contact_verified': False,
        'training_approved': False,
        'allowed_to_publish': False,
    }


def analyze(archive: Path) -> dict:
    # Exactly PR #231's parser, manifest, archive confinement and SHA contract.
    folder_map = upstream._check_archive(archive)
    with ExitStack() as stack:
        samples = {}
        for n in range(1, 8):
            banks = []
            for i, size in enumerate(upstream.SIZE):
                f = stack.enter_context(upstream.src._file(
                    folder_map[n], f'{n}.{i+1}.raw', size).open('rb'))
                banks.append(stack.enter_context(mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)))
            samples[n] = upstream._get(upstream.roster.TwoBankReader(*banks))
            # _get() returned a source-selected whole_record and geometry;
            # no numeric values are ever serialized.
        return summarize(samples)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archive', required=True, type=Path)
    args = p.parse_args(argv)
    try:
        report = analyze(args.archive)
    except (ValueError, TypeError, KeyError, OSError, OverflowError, IndexError):
        print('P0 state24 source audit ABSTAINED: archive, source or stable geometry gate failed',
              file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
