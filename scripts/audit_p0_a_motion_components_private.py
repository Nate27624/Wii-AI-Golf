#!/usr/bin/env python3
"""Exact-SHA read-only posthoc study of 46-packet manual-a-miss-v1.
No Dolphin, no controller input, no raw RAM upload, no training labels.
"""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
import math
from pathlib import Path
import re
import statistics
import struct

PHASES = ("I0", "AH", "AR", "M0", "I1")
STREAM = "candidate-events-PRIVATE.jsonl"
MANIFEST = "manifest-PRIVATE.json"
TOTAL = 46
CHANNELS = {
    "selected_record_plus_0x30": (0x30, 0x34, 0x38),
    "selected_record_plus_0x90": (0x90, 0x94, 0x98),
    "aim_candidate_plus_0x3c": (0x3c,),
}
HEX32 = re.compile(r"^[a-fA-F0-9]{8}$")
HEX256 = re.compile(r"^[a-fA-F0-9]{64}$")

class Abstain(ValueError):
    pass

def require(test, reason):
    if not test:
        raise Abstain(reason)

def safe_bytes(file, maximum):
    require(file.is_file() and not file.is_symlink(), "missing_or_symlinked_private_file")
    require(0 < file.stat().st_size <= maximum, "unbounded_private_file")
    return file.read_bytes()

def locate(captures_root, expected):
    require(captures_root.is_dir() and not captures_root.is_symlink(),
            "missing_or_symlinked_captures_root")
    matched = []
    for folder in captures_root.glob("p0-manual-a-*-PRIVATE"):
        if folder.is_symlink() or not folder.is_dir():
            continue
        file = folder / STREAM
        if file.is_symlink() or not file.is_file() or not 0 < file.stat().st_size <= 2*1024*1024:
            continue
        if sha256(file.read_bytes()).hexdigest() == expected:
            matched.append(folder)
    require(len(matched) == 1, "exact_sha_run_not_unique_or_not_found")
    return matched[0]

def load(run_dir, captures_root, expected_sha256):
    require(type(expected_sha256) is str and HEX256.fullmatch(expected_sha256),
            "invalid_expected_sha")
    expected_sha256 = expected_sha256.lower()
    require((run_dir is None) != (captures_root is None), "ambiguous_run_selector")
    folder = run_dir if run_dir is not None else locate(captures_root, expected_sha256)
    require(folder.is_dir() and not folder.is_symlink(), "invalid_run_directory")
    file = folder / STREAM
    raw = safe_bytes(file, 2*1024*1024)
    digest = sha256(raw).hexdigest()
    require(digest == expected_sha256, "sha256_mismatch")
    try:
        manifest = json.loads(safe_bytes(folder / MANIFEST, 65536))
        lines = raw.decode("utf-8").splitlines()
        require(len(lines) == TOTAL, "incorrect_packet_count")
        events = [json.loads(line) for line in lines]
    except (ValueError, UnicodeError) as exc:
        raise Abstain("unreadable_manifest_or_stream") from exc
    require(type(manifest) is dict and manifest.get("status") == "ABORTED"
            and manifest.get("protocol") == "manual-a-miss-v1"
            and type(manifest.get("run_samples")) is int and manifest["run_samples"] == TOTAL
            and manifest.get("private_sha256") == digest
            and manifest.get("training_approved") is False, "manifest_gate_failed")
    require(all(type(e) is dict for e in events), "invalid_sample_record")
    expected = [p for p in PHASES for _ in range(8)] + ["M1"]*6
    require([e.get("phase") for e in events] == expected, "unexpected_phase_order")
    owner = events[0].get("source_owner_pointer_digest_private")
    require(type(owner) is str and len(owner)>0, "missing_owner_digest")
    keys, prior_end = None, None
    for n, e in enumerate(events):
        index = n % 8 if n < 40 else n-40
        require(type(e.get("sample_index")) is int and e["sample_index"] == index,
                "sample_index_order_mismatch")
        require(e.get("source_owner_pointer_digest_private") == owner,
                "source_identity_changed")
        start, end = e.get("monotonic_start_ns"), e.get("monotonic_end_ns")
        require(type(start) is int and type(end) is int and start >= 0 and end >= start
                and (prior_end is None or start >= prior_end), "host_clock_or_order_invalid")
        prior_end = end
        words = e.get("candidate_words_private_be_u32_hex")
        require(type(words) is dict, "invalid_candidate_map")
        if keys is None:
            keys = frozenset(words)
        require(frozenset(words) == keys, "source_candidate_channels_changed")
        for key, seq in words.items():
            require(type(seq) is list and 1 <= len(seq) <= 64
                    and all(type(w) is str and HEX32.fullmatch(w) for w in seq),
                    "invalid_BE32_candidate_words")
        require(all(key in words and len(words[key]) == len(offsets)
                    for key, offsets in CHANNELS.items()), "required_channel_missing")
    require(sha256(safe_bytes(file, 2*1024*1024)).hexdigest() == digest,
            "stream_modified_during_read")
    return events, digest

def bit_values(events, phase, key, component):
    return [int(e["candidate_words_private_be_u32_hex"][key][component], 16)
            for e in events if e["phase"] == phase]

def be_float(word):
    f = struct.unpack(">f", word.to_bytes(4, "big"))[0]
    return f if math.isfinite(f) and abs(f) <= 1e7 else None

def analyze(events, digest):
    require(len(events) == TOTAL, "wrong_packet_count")
    result = {}
    for key, offsets in CHANNELS.items():
        channels = {}
        for component, offset in enumerate(offsets):
            baseline = bit_values(events, "I0", key, component)[0]
            previous = None
            phases = {}
            for phase in PHASES:
                words = bit_values(events, phase, key, component)
                require(len(words) == 8, "incomplete_control_phase")
                floats = [be_float(word) for word in words]
                row = {
                    "unique_words": len(set(words)),
                    "adjacent_word_transitions": sum(x != y for x,y in zip(words,words[1:])),
                    "different_from_I0_first_count": sum(x != baseline for x in words),
                    "first_equals_I0_first": words[0] == baseline,
                    "first_equals_previous_phase_last": None if previous is None else words[0] == previous[-1],
                    "finite_BE_float_candidate": all(x is not None for x in floats),
                }
                if all(x is not None for x in floats) and be_float(baseline) is not None:
                    row["median_delta_vs_I0_first"] = round(statistics.median(floats)-be_float(baseline),9)
                    row["within_phase_range"] = round(max(floats)-min(floats),9)
                phases[phase] = row
                previous = words
            channels["record_plus_0x%02x" % offset] = phases
        result[key] = channels
    def first(key, comp, phase):
        return bit_values(events, phase, key, comp)[0]
    matrix=[]
    for p,q in zip(PHASES,PHASES[1:]):
        a = first("aim_candidate_plus_0x3c",0,p) == first("aim_candidate_plus_0x3c",0,q)
        x = first("selected_record_plus_0x90",1,p) == first("selected_record_plus_0x90",1,q)
        z = first("selected_record_plus_0x90",2,p) == first("selected_record_plus_0x90",2,q)
        matrix.append({"from":p,"to":q,"aim3c_same":a,"x94_same":x,"x98_same":z,
                       "x94_changed_while_aim_same":a and not x})
    return {
        "status":"EXACT_SHA_RETROSPECTIVE_CANDIDATE_ONLY",
        "original_stream_sha256":digest,
        "protocol":"manual-a-miss-v1",
        "total_packets":46,
        "complete_no_contact_controls":{p:8 for p in PHASES},
        "quarantined_M1":{"packets":6,"human_observed":"HIT",
                          "machine_aligned_contact":False,"used_in_controls":False},
        "per_component":result,
        "phase_boundary_equality":matrix,
        "host_times_are_not_guest_physics_frames":True,
        "game_A_pressed_verified":False,
        "swing_power_verified":False,
        "training_approved":False
    }

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    target=p.add_mutually_exclusive_group(required=True)
    target.add_argument("--run-dir",type=Path)
    target.add_argument("--captures-root",type=Path)
    p.add_argument("--expected-sha256",required=True)
    args=p.parse_args(argv)
    try:
        events,digest=load(args.run_dir,args.captures_root,args.expected_sha256)
        print(json.dumps(analyze(events,digest),indent=2,sort_keys=True,allow_nan=False))
        return 0
    except (Abstain,OSError,ValueError,TypeError,KeyError,OverflowError) as exc:
        reason=str(exc) if isinstance(exc,Abstain) else "offline_reader_error"
        print(json.dumps({"status":"ABSTAIN","reason":reason,"training_approved":False}))
        return 2

if __name__=="__main__":
    raise SystemExit(main())
