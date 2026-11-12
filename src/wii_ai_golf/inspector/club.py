"""Read-only Rev1 Golf selected-club label for a source-qualified live sample.

Operator confirmed 17 phase first/second/heldout observations including all four
clubs. Separately original Rev1 code has UP/DOWN transitions 0..3 via
lwz r3,-0x5A80(r13); stw index,+0x1C(r3). Relative to independently
validated PlayerManager global r13-0x5AB0 = 0x804BF8D0, the conditional
static SDA join gives r13-0x5A80 = 0x804BF900. This separate pointer
was live-tested successfully; native r13 register itself was not read.
Never infer training approval or club state from PlayerManager+0x1C.
"""
from __future__ import annotations

CLUB_GLOBAL_SLOT = 0x804BF900  # published RSPE01 Rev1 .sbss pointer slot
CLUB_FIELD_OFFSET = 0x1C      # bounded u32 in pointer's source-selected owner
PLAYER_MANAGER_GLOBAL_SLOT = 0x804BF8D0  # a DIFFERENT .sbss root, NOT club
CLUB_NAMES = ("DRIVER", "IRON", "WEDGE", "PUTTER")


def club_label(index: object) -> str:
    """Any missing/malformed or out-of-bound live sample stays UNKNOWN."""
    if type(index) is not int or not 0 <= index < len(CLUB_NAMES):
        return "UNKNOWN"
    return CLUB_NAMES[index]
