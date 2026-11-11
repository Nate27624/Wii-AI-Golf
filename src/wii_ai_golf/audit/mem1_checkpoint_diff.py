"""Read-only, local-only B0/B1/B2/B3 whole-MEM1 checkpoint contrast.

Four *native plain* 24MiB MEM1 binary images, not savestates. No Dolphin,
network, controller, publication or pointer dereference. Outputs only
bank-relative 4KiB page aggregate counts, NEVER raw bytes, word values,
absolute pointer values, filenames or full word address inventories.
"""
from __future__ import annotations

from contextlib import ExitStack
import json
import mmap
from pathlib import Path
import re

MEM1_SIZE = 24 * 1024 * 1024
PAGE_SIZE = 4096
WORD_SIZE = 4
MAX_PAGES_OUT = 24
_VALID_GAME = b"RSPE01"
_GAME_REVISION = 1
_SAFE_PAGE = re.compile(r"\+0x[0-9A-F]{6}\Z")


def _same_word(left: memoryview, right: memoryview, index: int) -> bool:
    """Word equality only; no host-endian decoding or value export."""
    return left[index:index+WORD_SIZE] == right[index:index+WORD_SIZE]


def compare_mem1_views(b0, b1, b2, b3, *, page_size: int = PAGE_SIZE,
                       max_pages: int = MAX_PAGES_OUT) -> dict:
    """Compute page-level differences from four bytes-like MEM1 snapshots.

    Synthetic tests may use tiny buffers; CLI enforces exactly MEM1_SIZE.
    B1 is a timed still control. B2 is an operator-labelled pointer-only
    condition. B3 is idle after input stops; equality is not proof of
    a physical reversion or a game value's meaning.
    """
    if (type(page_size) is not int or page_size < 16 or
            page_size % WORD_SIZE or type(max_pages) is not int or
            not 1 <= max_pages <= MAX_PAGES_OUT):
        raise ValueError("Invalid study page budget")
    samples = (memoryview(x) for x in (b0, b1, b2, b3))
    views = tuple(samples)
    n = len(views[0])
    if (n == 0 or n % page_size or n % WORD_SIZE or
            any(len(x) != n for x in views)):
        raise ValueError("Four equal-length, word-aligned raw memory banks required")
    if n >= 8:
        for x in views:
            if bytes(x[:6]) != _VALID_GAME or x[7] != _GAME_REVISION:
                raise ValueError("Wrong game image/revision or non-plain MEM1 format")
    counts = {
        "pages_examined": n // page_size,
        "words_examined": n // WORD_SIZE,
        "B0_B1_idle_changed_words": 0,
        "B1_B2_aim_transition_changed_words": 0,
        "B2_B3_return_transition_changed_words": 0,
        "B2_only_returned_to_B1_value_words": 0,
        "B2_B3_persisted_after_stable_idle_words": 0,
        "B0_B1_stable_then_B2_changed_words": 0,
        "stable_all_four_words": 0,
    }
    ranked = []
    for start in range(0, n, page_size):
        v0,v1,v2,v3 = [v[start:start+page_size] for v in views]
        # Fast path for immutable pages, no raw words ever interpreted.
        if v0 == v1 == v2 == v3:
            counts["stable_all_four_words"] += page_size // WORD_SIZE
            continue
        idle = aim = ret = reversible = persistent = novelty = stable = 0
        for off in range(0, page_size, WORD_SIZE):
            a = _same_word(v0,v1,off)
            b = _same_word(v1,v2,off)
            c = _same_word(v2,v3,off)
            if not a: idle += 1
            if not b: aim += 1
            if not c: ret += 1
            if a and not b:
                novelty += 1
                if _same_word(v1,v3,off):
                    reversible += 1
                elif c:
                    persistent += 1
            if a and b and c: stable += 1
        counts["B0_B1_idle_changed_words"] += idle
        counts["B1_B2_aim_transition_changed_words"] += aim
        counts["B2_B3_return_transition_changed_words"] += ret
        counts["B2_only_returned_to_B1_value_words"] += reversible
        counts["B2_B3_persisted_after_stable_idle_words"] += persistent
        counts["B0_B1_stable_then_B2_changed_words"] += novelty
        counts["stable_all_four_words"] += stable
        # Rank candidate pages, not individual words, with idle noise
        # explicitly included. No guessed source semantics/float decoding.
        if idle or aim or ret:
            ranked.append({
                "mem1_relative_page": f"+0x{start:06X}",
                "idle_changed_words": idle,
                "aim_transition_changed_words": aim,
                "return_transition_changed_words": ret,
                "B2_transient_returned_to_B1_words": reversible,
                "B2_persisted_while_B3_idle_words": persistent,
                "B0_B1_stable_B2_changed_words": novelty,
                "candidate_only_not_gameplay_verified": True,
            })
    ranked.sort(key=lambda v: (
        -(v["B2_transient_returned_to_B1_words"] +
          v["B2_persisted_while_B3_idle_words"]),
        -v["B0_B1_stable_B2_changed_words"],
        v["idle_changed_words"],
        v["mem1_relative_page"],
    ))
    changed_pages = len(ranked)
    counts["pages_with_any_changes"] = changed_pages
    counts["candidate_pages_with_stable_B0_B1_and_changed_B2"] = sum(
        x["B0_B1_stable_B2_changed_words"] > 0 for x in ranked)
    if (sum(counts[k] for k in
            ("B0_B1_idle_changed_words", "B1_B2_aim_transition_changed_words",
             "B2_B3_return_transition_changed_words")) == 0):
        action = ("All four checkpoints are identical at aligned u32 granularity. "
                  "Verify actual distinct exported states and active game; "
                  "no field identification possible.")
    elif counts["B0_B1_stable_then_B2_changed_words"] == 0:
        action = ("No u32 changes were unique to B1-to-B2 after still B0-to-B1. "
                  "Do not infer absent aim physics; inspect source object "
                  "ownership and snapshot provenance.")
    else:
        action = ("Inspect high-ranked pages LOCALLY with reviewed source "
                  "symbols and debugger write-site evidence. A differential "
                  "page is not a verified aim/club/power field.")
    return {
        "kind": "local-mem1-four-checkpoint-differential",
        "schema_version": 1,
        "memory_bank": "Wii MEM1, cached PPC base 0x80000000",
        "plain_mem1_size_expected_bytes": MEM1_SIZE,
        "study": "FULL-STATE-BASELINE-01",
        "checkpoints": ["B0_ready_idle", "B1_delayed_idle",
                        "B2_operator_labelled_pointer_aim",
                        "B3_return_to_idle_after_input"],
        "word_comparison": "aligned_32_bit_equality_only",
        "page_size": page_size,
        "counts": counts,
        "top_candidate_pages": ranked[:max_pages],
        "candidate_pages_omitted": max(0, changed_pages - max_pages),
        "all_checkpoints_verified_same_live_boot": False,
        "operator_phase_labels_independently_verified": False,
        "game_mode_and_hole_verified": False,
        "club_pose_verified": False,
        "ball_position_verified": False,
        "power_verified": False,
        "real_swing_recorded": False,
        "allowed_to_publish": False,
        "source_and_runtime_owner_review_required": True,
        "next_action": action,
        "warning": ("Four snapshots from one boot are discovery-only. "
                    "Idle changes may include timers; B1->B2 may reflect "
                    "time, UI or allocator state. B3 is not an independent "
                    "negative control. Page offsets are not player fields. "
                    "All raw MEM1 remains PRIVATE."),
    }


def _private_regular_file(path: Path, root: Path) -> Path:
    if path.is_symlink() or not path.is_file():
        raise ValueError("Expected existing nonsymlink private raw snapshot")
    resolved = path.resolve(strict=True)
    if not resolved.is_relative_to(root):
        raise ValueError("Snapshot must remain under operator-private data directory")
    if path.suffix.lower() not in (".bin", ".raw", ".mem"):
        raise ValueError("Native debugger output must be plain binary MEM1")
    if path.stat().st_size != MEM1_SIZE:
        raise ValueError("Expected exact 24MiB uncompressed MEM1 bytes; "
                         "not a savestate/partial dump/MEM2 image")
    return resolved


def analyze_private_mem1_files(paths, *, private_root: Path, output: Path,
                               max_pages: int = MAX_PAGES_OUT) -> dict:
    """Validate provenance/path/format before mmap and local-only output."""
    if len(paths) != 4:
        raise ValueError("Four checkpoint images required")
    private_root = Path(private_root).resolve(strict=True)
    if not private_root.is_dir():
        raise ValueError("Private root must exist")
    imgs = [_private_regular_file(Path(p), private_root) for p in paths]
    if len(set(imgs)) != 4:
        raise ValueError("Each checkpoint must be a distinct file")
    output = Path(output)
    if output.is_symlink() or output.exists():
        raise ValueError("Refusing existing/symlink output")
    if (output.suffix.lower() != ".json"
            or output.parent.resolve(strict=True) != private_root):
        raise ValueError("Sanitized output must be a new JSON file at private root")
    with ExitStack() as stack:
        files = [stack.enter_context(open(p, "rb")) for p in imgs]
        mems = [stack.enter_context(mmap.mmap(
                    f.fileno(), length=0, access=mmap.ACCESS_READ))
                for f in files]
        result = compare_mem1_views(*mems, max_pages=max_pages)
    with output.open("x", encoding="utf-8") as fp:
        json.dump(result, fp, indent=2, sort_keys=True, allow_nan=False)
        fp.write("\n")
    return result
