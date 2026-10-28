"""OFFLINE-only differential of four PRIVATE native Wii MEM1 checkpoints.

B0=stationary, B1=stationary later, B2=pointer-only, B3=released/still.
No emulator, network, RPC, ROM parsing, public publisher or game writes.
Conservative 4KiB page and aligned u32 EQUALITY differences only:
not proof of field types, origin, causality or scene identity.
The private detail report includes PAGE INDICES and word-relative positions;
stdout has AGGREGATES ONLY (not paths, addresses, dumps, values, hashes).
"""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import ExitStack
import hashlib
import json
from pathlib import Path
import stat
import sys

PAGE = 4096
MEM1_BYTES = 24 * 1024 * 1024
MAX_PRIVATE_PAGES = 4096
MAX_WORDS_PER_PAGE = 16

def _resolve_private(path: Path, root: Path) -> Path:
    # Resolve only after rejecting symlinks; never read from a git worktree.
    if path.is_symlink() or not path.is_file():
        raise ValueError("private dump missing or symlink")
    resolved = path.resolve(strict=True)
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError("private dump not under ignored sibling directory") from exc
    if not stat.S_ISREG(resolved.stat().st_mode):
        raise ValueError("nonregular private dump")
    return resolved

def _classify(a: int, b: int, c: int, d: int) -> str:
    if a == b == c == d:
        return "static"
    if a != b:
        return "idle_changed_or_ambiguous"
    if b != c and d == b:
        return "pointer_phase_reverted_candidate"
    if b != c and d == c:
        return "pointer_phase_persistent_candidate"
    if b == c and d != c:
        return "post_pointer_only_changed"
    return "other_ambiguous"

def compare(paths: tuple[Path, Path, Path, Path], *,
            nbytes: int = MEM1_BYTES, page_bytes: int = PAGE) -> tuple[dict, dict]:
    """Strict equal-length snapshots; streams 4 pages, no whole-RAM allocation."""
    if len(paths) != 4 or len(set(paths)) != 4:
        raise ValueError("four distinct checkpoint paths are required")
    if nbytes < page_bytes or nbytes % page_bytes or page_bytes % 4:
        raise ValueError("invalid page or region size")
    for path in paths:
        if path.stat().st_size != nbytes:
            raise ValueError("MEM1 snapshot length mismatch, unknown dump format")

    counts: Counter[str] = Counter()
    phase_counts: Counter[str] = Counter()
    detailed = []
    relevant_total = 0
    hashes = [hashlib.sha256() for _ in paths]
    with ExitStack() as stack:
        readers = [stack.enter_context(p.open("rb")) for p in paths]
        for page_index in range(nbytes // page_bytes):
            buffers = [fp.read(page_bytes) for fp in readers]
            for hash_state, chunk in zip(hashes, buffers):
                hash_state.update(chunk)
            if any(len(b) != page_bytes for b in buffers):
                raise ValueError("short checkpoint read")
            n_idle = n_pointer = n_recovery = 0
            by_class: Counter[str] = Counter()
            sample_offsets: list[str] = []
            for offset in range(0, page_bytes, 4):
                a, b, c, d = (int.from_bytes(buf[offset:offset+4], "big")
                              for buf in buffers)
                category = _classify(a, b, c, d)
                by_class[category] += 1
                counts[category] += 1
                n_idle += a != b
                n_pointer += b != c
                n_recovery += c != d
                if (category in ("pointer_phase_reverted_candidate",
                                 "pointer_phase_persistent_candidate")
                        and len(sample_offsets) < MAX_WORDS_PER_PAGE):
                    sample_offsets.append(f"+0x{offset:03X}")
            phase_counts["idle_comparison_changed_words"] += n_idle
            phase_counts["pointer_comparison_changed_words"] += n_pointer
            phase_counts["recovery_comparison_changed_words"] += n_recovery
            if n_idle or n_pointer or n_recovery:
                relevant_total += 1
                # Collect all bounded 6,144 pages first, then rank and cap.
                # Truncating *before* ranking would miss late high-signal pages.
                detailed.append({
                        "page_index_private": page_index,
                        "idle_changed_words": n_idle,
                        "pointer_changed_words": n_pointer,
                        "recovery_changed_words": n_recovery,
                        "category_counts": dict(by_class),
                        "candidate_word_offsets_private": sample_offsets,
                    })
        if any(fp.read(1) for fp in readers):
            raise ValueError("trailing bytes after expected MEM1 size")

    # Prioritize pages with candidate reversion, but demote idle-change pages.
    detailed.sort(key=lambda p: (
        -p["category_counts"].get("pointer_phase_reverted_candidate", 0),
        -p["category_counts"].get("pointer_phase_persistent_candidate", 0),
        p["idle_changed_words"], p["page_index_private"]))
    detailed = detailed[:MAX_PRIVATE_PAGES]
    total_words = nbytes // 4
    summary = {
        "kind": "offline_private_mem1_control_diff_sanitized",
        "schema_version": 1,
        "operator_labeled_single_session_unverified": True,
        "source_dump_format_verified": False,
        "game_revision_scene_or_hole_verified": False,
        "game_power_or_player_fields_verified": False,
        "sampling_is_non_atomic_across_checkpoints": True,
        "checkpoint_count": 4,
        "mem1_bytes": nbytes,
        "pages_compared": nbytes // page_bytes,
        "changed_pages_any_phase": relevant_total,
        "word_category_counts": dict(sorted(counts.items())),
        "phase_pair_change_counts": dict(sorted(phase_counts.items())),
        "private_page_details_truncated": relevant_total > MAX_PRIVATE_PAGES,
        "warning": (
            "Only equality change patterns under operator-labeled conditions; "
            "no causality, field identity, endian semantics, source type, "
            "applied pointer motion or shot power proven. "
            "Offsets and RAM values are excluded from stdout."
        ),
    }
    detail = {
        "kind": "LOCAL_PRIVATE_MEM1_PAGE_INDEX_DO_NOT_UPLOAD",
        "schema_version": 1,
        "mem1_address_base_hypothesis": "0x80000000",
        "source_region_mapping_verified": False,
        "page_bytes": page_bytes,
        "checkpoint_sha256_PRIVATE": [h.hexdigest() for h in hashes],
        "pages_ranked": detailed,
        "pages_ranked_truncated": relevant_total > MAX_PRIVATE_PAGES,
        "must_not_publish": True,
    }
    assert sum(counts.values()) == total_words
    return summary, detail

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--b0", type=Path, required=True)
    parser.add_argument("--b1", type=Path, required=True)
    parser.add_argument("--b2", type=Path, required=True)
    parser.add_argument("--b3", type=Path, required=True)
    parser.add_argument("--private-report", type=Path, required=True,
                        help="NEW local PRIVATE JSON filename under ignored Data")
    args = parser.parse_args(argv)
    try:
        root = (Path(__file__).resolve().parents[2] /
                "Wii-AI-Golf-Data").resolve(strict=True)
        if not root.is_dir():
            raise ValueError("missing private sibling directory")
        paths = tuple(_resolve_private(p, root) for p in
                      (args.b0, args.b1, args.b2, args.b3))
        output = args.private_report
        if output.is_symlink() or output.exists() or not output.parent.is_dir():
            raise ValueError("private report path invalid or occupied")
        parent = output.parent.resolve(strict=True)
        try:
            parent.relative_to(root)
        except ValueError as exc:
            raise ValueError("report not in private data directory") from exc
        if output.suffix.lower() != ".json":
            raise ValueError("private report must end in .json")
        summary, detail = compare(paths)
        # open 'x' guarantees never overwriting previous private evidence.
        with output.open("x", encoding="utf-8") as fp:
            json.dump(detail, fp, indent=2, sort_keys=True, allow_nan=False)
            fp.write("\n")
        print(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False))
        return 0
    except (OSError, ValueError, AssertionError):
        # Uniform privacy-safe error; never print filenames or private words.
        print("Offline MEM1 audit stopped: invalid private dump/report or "
              "unverified 24MiB binary layout", file=sys.stderr)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
