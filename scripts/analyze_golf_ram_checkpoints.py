"""Offline four-checkpoint Wii Sports RAM differentiation; local private output only.

Reads raw, headerless MEM1/MEM2 images. Never opens Dolphin or publishes data.
Candidates are exploratory contrasts, NOT validated gameplay variables.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import hashlib
import json
import mmap
from pathlib import Path
import struct

SIZES = {"mem1": 24 * 1024 * 1024, "mem2": 64 * 1024 * 1024}
PAGE_BYTES = 4096


def _changed_bytes(x: int) -> int:
    return sum(bool(x & mask) for mask in (0xFF, 0xFF00, 0xFF0000, 0xFF000000))


def analyze_four(b0, b1, b2, b3, *, page_bytes: int = PAGE_BYTES, top_pages: int = 20) -> dict:
    """Compare four equal-length, big-endian-aligned byte buffers.

    B0 ready, B1 idle, B2 pointer-only, B3 return to stillness.
    Candidate words reflect controlled correlations, never semantic identity.
    """
    n = len(b0)
    if n == 0 or n % 4 or any(len(x) != n for x in (b1, b2, b3)):
        raise ValueError("Four equal-length nonempty 4-byte-aligned RAM images required")
    if page_bytes < 4 or page_bytes % 4 or top_pages < 1 or top_pages > 100:
        raise ValueError("Invalid page size or top-pages limit")
    count = (n + page_bytes - 1) // page_bytes
    names = ("idle_changed_words", "aim_changed_words", "return_changed_words",
             "reversible_aim_candidates", "persistent_aim_candidates", "ambiguous_aim_words")
    pages = [{key: 0 for key in names} for _ in range(count)]
    offsets = [[] for _ in range(count)]  # Private local offset samples; never RAM contents.
    totals = {key: 0 for key in names}
    byte_changes = {"idle": 0, "aim": 0, "return": 0}
    readers = (struct.iter_unpack(">I", x) for x in (b0, b1, b2, b3))
    for index, row in enumerate(zip(*readers)):
        a, b, c, d = (v[0] for v in row)
        if a == b == c == d:
            continue
        page_index = (index * 4) // page_bytes
        p = pages[page_index]
        idle, aim, ret = a != b, b != c, c != d
        reversible = a == b == d and c != b
        persistent = a == b and c == d and c != b
        ambiguous = aim and not (reversible or persistent)
        for label, yes in zip(names, (idle, aim, ret, reversible, persistent, ambiguous)):
            if yes:
                p[label] += 1
                totals[label] += 1
        if idle:
            byte_changes["idle"] += _changed_bytes(a ^ b)
        if aim:
            byte_changes["aim"] += _changed_bytes(b ^ c)
        if ret:
            byte_changes["return"] += _changed_bytes(c ^ d)
        if (reversible or persistent) and len(offsets[page_index]) < 8:
            offsets[page_index].append({"relative_byte_offset": index * 4,
                                        "pattern": "reversible" if reversible else "persistent"})
    ranked = sorted((i for i, p in enumerate(pages)
                     if p["reversible_aim_candidates"] or p["persistent_aim_candidates"]),
                    key=lambda i: (pages[i]["reversible_aim_candidates"] * 5
                                   + pages[i]["persistent_aim_candidates"] * 2
                                   - pages[i]["idle_changed_words"],
                                   pages[i]["reversible_aim_candidates"], -i), reverse=True)
    top = [{"page_index": i, "relative_page_offset": i * page_bytes,
            **pages[i], "local_candidate_offsets": offsets[i]} for i in ranked[:top_pages]]
    return {"schema": "offline-four-checkpoint-private-v1", "local_only_no_upload": True,
            "source_ownership_verified": False, "game_power_verified": False,
            "frame_atomicity_verified": False, "contact_verified": False,
            "semantic_note": "B0/B1/B2/B3 comparisons are exploratory, not named game fields",
            "bytes_analyzed": n, "page_bytes": page_bytes, "counts": totals,
            "changed_bytes": byte_changes, "candidate_page_count": len(ranked),
            "top_candidate_pages": top}


def _private_output_path(requested: str, script_path: Path) -> Path:
    root = (script_path.resolve().parent.parent.parent / "Wii-AI-Golf-Data").resolve()
    out = Path(requested).resolve()
    if root not in out.parents or out.suffix.lower() != ".json":
        raise ValueError("Output must be a .json file inside sibling Wii-AI-Golf-Data")
    if out.exists():
        raise ValueError("Output file already exists; refusing overwrite")
    return out


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mem", choices=SIZES, required=True)
    for label in ("b0", "b1", "b2", "b3"):
        parser.add_argument("--" + label, type=Path, required=True)
    parser.add_argument("--out", help="Optional PRIVATE report under sibling Wii-AI-Golf-Data")
    parser.add_argument("--top-pages", type=int, default=20)
    args = parser.parse_args(argv)
    sources = [getattr(args, k).resolve() for k in ("b0", "b1", "b2", "b3")]
    if len(set(sources)) != 4:
        parser.error("All four checkpoint paths must be distinct")
    if any(not p.is_file() or p.stat().st_size != SIZES[args.mem] for p in sources):
        parser.error(f"Expected four headerless {args.mem.upper()} images of exactly {SIZES[args.mem]} bytes")
    try:
        target = _private_output_path(args.out, Path(__file__)) if args.out else None
        with ExitStack() as stack:
            maps = [stack.enter_context(mmap.mmap(stack.enter_context(p.open("rb")).fileno(),
                                                   0, access=mmap.ACCESS_READ)) for p in sources]
            report = analyze_four(*maps, top_pages=args.top_pages)
            report["region"] = args.mem
            report["private_source_sha256"] = [hashlib.sha256(x).hexdigest() for x in maps]
        if target:
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("x", encoding="utf-8") as out:
                json.dump(report, out, indent=2, sort_keys=True)
                out.write("\n")
        # Console intentionally omits file names, hashes, and candidate byte offsets.
        print(json.dumps({"region": args.mem, "local_only": True,
                          "counts": report["counts"], "changed_bytes": report["changed_bytes"],
                          "candidate_page_count": report["candidate_page_count"],
                          "private_report_written": target is not None}, indent=2))
    except (ValueError, OSError) as exc:
        parser.error(f"Private offline analysis failed ({type(exc).__name__}); inspect local inputs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
