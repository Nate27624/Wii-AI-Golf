"""DISABLED-BY-DEFAULT S001 frame-coroutine selected-ball micro-watch core.

No transport, Dolphin/Felk import, launcher, controller, bridge patch, file
writing, or public publisher. S001 must explicitly review/call capture() from
the EXISTING frame coroutine. Source-backed direct memory.read_u32 reads only.
This is not an automatic live sampler or a proven game-ball XYZ decoder.

The private sample shape targets S001/S002 PR #165's future temporal consumer.
An external caller MUST supply genuine _frame_count values from its existing
frame coroutine, not commanded trace indices or GUI dump timestamps.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

MEM1_BASE, MEM1_END = 0x80000000, 0x81800000
MEM2_BASE, MEM2_END = 0x90000000, 0x94000000
STATIC_SCENE = 0x804BF4D8
STATIC_CONFIG = 0x804BF8C4
STATIC_FIELD = 0x804BF868
STATIC_PLAYER_MANAGER = 0x804BF8D0
BALL_DATA_START, BALL_DATA_END = 0x803C7918, 0x803C7A50
GAME_REV1_HEADER = (0x52535045, 0x30310001)  # RSPE01, revision 1
SOURCE_CONTRACT = "S002-160-selected-ball-start-rev1"
STAGES = ("idle_before", "idle_after", "event_before", "event_after")
MAX_U32_READS_PER_CAPTURE = 48
MAX_FRAME_SPAN = 2


class WatchRejected(ValueError):
    """Failed safely. Never include live runtime values/addresses in errors."""


def _mapped(address: int, n: int, *, region: str) -> bool:
    if type(address) is not int or address % 4 or n <= 0 or n % 4:
        return False
    base, end = ((MEM1_BASE, MEM1_END) if region == "MEM1"
                 else (MEM2_BASE, MEM2_END))
    return base <= address and address + n <= end


def _ppc_dform(word: int, opcode: int, dst: int, base: int, imm: int) -> bool:
    return (word >> 26 == opcode and (word >> 21) & 31 == dst
            and (word >> 16) & 31 == base and (word & 0xFFFF) == imm & 0xFFFF)


def _ppc_add(word: int, dst: int, base: int, other: int) -> bool:
    return (word >> 26 == 31 and (word >> 1) & 1023 == 266
            and (word >> 21) & 31 == dst
            and (word >> 16) & 31 == base
            and (word >> 11) & 31 == other)


# Exact source instructions already vetted by S002 #160 on operator Rev1 DOL.
# Opcode/operand assertions cannot alone establish world-coordinate semantics.
_SOURCE_DFORMS = (
    (0x802A31E8, 32, 0, 29, 0x34C),  # selector index
    (0x802A31EC, 7, 0, 0, 0xCC),    # 4-record stride
    (0x802A31F4, 14, 0, 3, 4),
    (0x802A31F8, 36, 0, 29, 0x334), # selected record writer
    (0x802A03A0, 32, 4, 3, 0x88),  # ball child
    (0x802A03B4, 32, 4, 4, 0x4C),  # VEC3 pointer
    (0x802A03B8, 52, 2, 4, 0),     # stfs X
    (0x802A03C0, 52, 0, 4, 4),     # stfs Y
    (0x802A03C8, 52, 0, 4, 8),     # stfs Z
    (0x802922EC, 32, 3, 3, 0x50), # selected start getter
    (0x802922F0, 32, 3, 3, 0x4C), # its translation pointer
)


@dataclass(frozen=True)
class CaptureEnvelope:
    """No RAM words. Safe diagnostics only; not an export of the sample."""
    stage: str
    read_count: int
    frame_span: int
    verified_source_shape: bool


class SelectedBallMicroWatch:
    """Single-caller, one-boot private in-memory capture helper.

    Called from an existing S001 Felk frame coroutine with memory.read_u32
    and its own frame counter. Four explicit captures, one per phase. It does
    not schedule events, send input, assign human observations or write files.
    """

    def __init__(self, boot_token: str):
        if (type(boot_token) is not str or
                not 8 <= len(boot_token) <= 128):
            raise ValueError("Explicit private per-boot session token required")
        self._token = boot_token
        self._samples: list[dict] = []
        self._diagnostics: list[CaptureEnvelope] = []

    def capture(
        self,
        stage: str,
        read_u32: Callable[[int], int],
        frame_count: Callable[[], int],
    ) -> CaptureEnvelope:
        if (len(self._samples) >= len(STAGES)
                or stage != STAGES[len(self._samples)]):
            raise WatchRejected("Unexpected or repeated prospective phase")
        if not callable(read_u32) or not callable(frame_count):
            raise WatchRejected("Frame-thread read callbacks required")
        try:
            start = frame_count()
            if type(start) is not int or start < 0:
                raise WatchRejected("Actual frame counter missing")
            used = 0

            def take(address: int, *, region="MEM2") -> int:
                nonlocal used
                if used >= MAX_U32_READS_PER_CAPTURE:
                    raise WatchRejected("Per-capture read limit exceeded")
                if not _mapped(address, 4, region=region):
                    raise WatchRejected("Source-directed memory read out of bank")
                used += 1
                value = read_u32(address)
                if type(value) is not int or not 0 <= value <= 0xFFFFFFFF:
                    raise WatchRejected("Invalid source memory word")
                return value

            def vec(address: int) -> list[int]:
                if not _mapped(address, 12, region="MEM2"):
                    raise WatchRejected("Unmapped source VEC3")
                return [take(address + 4 * i) for i in range(3)]

            if tuple(take(MEM1_BASE + 4*i, region="MEM1")
                     for i in range(2)) != GAME_REV1_HEADER:
                raise WatchRejected("Wrong Wii Sports disc/revision")
            for pc, op, dst, base, imm in _SOURCE_DFORMS:
                if not _ppc_dform(take(pc, region="MEM1"), op, dst, base, imm):
                    raise WatchRejected("Rev1 source callsite mismatch")
            if not _ppc_add(take(0x802A31F0, region="MEM1"), 3, 29, 0):
                raise WatchRejected("Selected-record PPC register flow mismatch")

            manager = take(STATIC_SCENE, region="MEM1")
            if not _mapped(manager, 0x1C, region="MEM1"):
                raise WatchRejected("Scene manager owner missing")
            scene = take(manager + 0x0C, region="MEM1")
            if not _mapped(scene, 0xA0, region="MEM2"):
                raise WatchRejected("Golf scene missing")
            if (take(manager + 0x18, region="MEM1") != 5 or
                    take(scene + 0x1C) != 5 or
                    take(scene + 0x20) != manager or
                    take(scene + 0x54) != 2):
                raise WatchRejected("Golf scene/sport/backlink gate failed")

            config = take(STATIC_CONFIG, region="MEM1")
            if not _mapped(config, 0x9C, region="MEM2"):
                raise WatchRejected("Config owner missing")
            if take(config + 0x94) != 4:
                raise WatchRejected("Wrong source-gated game mode")
            hole = take(config + 0x98)
            if hole not in range(9):
                raise WatchRejected("Unknown mode4 course index")

            main = take(scene + 0x9C)
            if (not _mapped(main, 4, region="MEM2")
                    or not 0x803C7798 <= take(main) < 0x803C77C0):
                raise WatchRejected("Golf main constructor-data identity mismatch")
            pm = take(STATIC_PLAYER_MANAGER, region="MEM1")
            if not _mapped(pm, 0x354, region="MEM2"):
                raise WatchRejected("Roster manager missing")
            if not 0x803C7DD0 <= take(pm) < 0x803C7DE0:
                raise WatchRejected("Player manager constructor-data identity mismatch")
            selected = take(pm + 0x334)
            matches = [index for index in range(4)
                       if selected == pm + 4 + index * 0xCC]
            if len(matches) != 1:
                raise WatchRejected("Selected record does not match source stride")
            index = matches[0]
            rec = pm + 4 + 0xCC * index

            ball = take(rec + 0x88)
            if not _mapped(ball, 0x50, region="MEM2"):
                raise WatchRejected("Ball-related object missing")
            firstword = take(ball)
            if not BALL_DATA_START <= firstword < BALL_DATA_END:
                raise WatchRejected("Ball class-data hint missing")
            ball_vec_ptr = take(ball + 0x4C)
            if ball_vec_ptr != ball + 0x30:
                raise WatchRejected("Ball Base translation selfref mismatch")

            field = take(STATIC_FIELD, region="MEM1")
            if not _mapped(field, 0xA8, region="MEM2"):
                raise WatchRejected("Field manager missing")
            start_obj = take(field + 0x50)
            if not _mapped(start_obj, 0x50, region="MEM2"):
                raise WatchRejected("Start object missing")
            if (take(start_obj + 0x48) != start_obj + 0x0C
                    or take(start_obj + 0x4C) != start_obj + 0x30):
                raise WatchRejected("Start Base translation selfref mismatch")

            ball_words = vec(ball_vec_ptr)
            start_words = vec(start_obj + 0x30)
            rec_054_words = vec(rec + 0x54)
            rec_060_words = vec(rec + 0x60)

            end = frame_count()
            if (type(end) is not int or end < start or
                    end - start > MAX_FRAME_SPAN):
                raise WatchRejected("Non-atomic or unbounded frame bracket")
            if self._samples and start <= self._samples[-1]["frame_end"]:
                raise WatchRejected("Capture frames overlap or rewind")
            sample = {
                "stage": stage, "boot_token": self._token,
                "game_id": "RSPE01", "revision": 1, "scene_id": 5,
                "sport_id": 2, "game_mode": 4, "hole_index": hole,
                "selected_record_index": index, "frame_start": start,
                "frame_end": end,
                "acquisition_source": "same_felk_frame_coroutine",
                "source_path_gates_passed": True,
                "selected_record_pointer": rec,
                "ball_owner_pointer": ball,
                "start_object_pointer": start_obj,
                "selected_ball_vec": ball_words,
                "current_start_vec": start_words,
                "record_pos_054_vec": rec_054_words,
                "record_pos_060_vec": rec_060_words,
            }
            # Atomic commit only after every gate and counter check passes.
            self._samples.append(sample)
            diagnostic = CaptureEnvelope(stage, used, end - start, True)
            self._diagnostics.append(diagnostic)
            return diagnostic
        except WatchRejected:
            raise
        except Exception as exc:
            raise WatchRejected("Source-gated read failed, no sample committed") from None

    def private_samples(self) -> list[dict]:
        """IN-MEMORY private values; S001/S000 own any future persistence."""
        return [{k: (list(v) if isinstance(v, list) else v)
                 for k, v in sample.items()} for sample in self._samples]

    def safe_diagnostics(self) -> list[dict]:
        return [{"stage": d.stage, "read_count": d.read_count,
                 "frame_span": d.frame_span, "verified_source_shape": d.verified_source_shape}
                for d in self._diagnostics]
