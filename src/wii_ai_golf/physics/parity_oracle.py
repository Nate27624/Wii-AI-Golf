"""Offline M2 synthetic parity oracle; never authenticates native Wii physics.

Owns only source-conditional comparison around the existing M1 AirborneTrace.
S002 attestation and basis results are *labels*, not trust roots: supplied
flags or claimed timestamps cannot certify guest PC, frame, Ball, or parity.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import re
import struct
from typing import Sequence

from wii_ai_golf.physics.airborne import AirborneTrace

_SCHEMA = "wii-golf-m2-synthetic-parity-v1"
_ID = re.compile(r"[A-Za-z][A-Za-z0-9_.:-]{0,63}\Z")
_SHA = re.compile(r"[0-9a-f]{40}\Z")
_MAX_SAMPLES = 10001


@dataclass(frozen=True)
class TraceIdentity:
    """Symbolic *comparison* identity, not a native receiver attestation.

    No native pointers, private memory or raw source archive hashes are needed.
    model_sha is a git commit-like 40-digit hex identifier, not an attestation.
    """

    source_revision: str
    source_cohort_tag: str
    boot_id: str
    scene_id: str
    shot_id: str
    selected_ball_tag: str
    ball_epoch: str
    model_sha: str
    physics_parameter_provenance: str
    coordinate_basis: str
    units: str
    numeric_precision: str


@dataclass(frozen=True)
class ReferenceSample:
    numerical_step: int
    position_xyz: tuple[float, float, float]
    velocity_xyz: tuple[float, float, float] | None = None
    guest_physics_frame: int | None = None
    atomic: bool = True
    source_quality: str = "synthetic"


@dataclass(frozen=True)
class EvidenceLabels:
    """Untrusted annotations supplied by callers, never native evidence.

    guest_step_status and basis_status accept the existing S002 classifiers'
    exact output values. Even their positive categories are not physical proof.
    """

    trace_kind: str
    clock_domain: str
    guest_step_status: str
    basis_status: str
    source_revision_qualified: bool = False
    source_archive_qualified: bool = False
    selected_receiver_qualified: bool = False
    selected_ball_xyz_qualified: bool = False
    selected_launch_v0_qualified: bool = False
    normalizer_branch_qualified: bool = False
    ppc_f32_qualified: bool = False
    host_f32_operations_matched: bool = False


def _identity(identity: TraceIdentity) -> None:
    if not isinstance(identity, TraceIdentity):
        raise ValueError("typed TraceIdentity required")
    for name in ("source_revision", "source_cohort_tag", "boot_id", "scene_id",
                 "shot_id", "selected_ball_tag", "ball_epoch",
                 "physics_parameter_provenance", "coordinate_basis", "units"):
        value = getattr(identity, name)
        if (type(value) is not str or not _ID.fullmatch(value)
                or re.search(r"0x[0-9a-f]{6,}", value, flags=re.I)):
            raise ValueError("invalid symbolic trace identity")
    if type(identity.model_sha) is not str or not _SHA.fullmatch(identity.model_sha):
        raise ValueError("invalid model SHA label")
    if identity.numeric_precision not in ("host_f32", "binary64"):
        raise ValueError("unsupported numeric precision")


def _xyz(value: object) -> tuple[float, float, float]:
    if type(value) not in (tuple, list) or len(value) != 3:
        raise ValueError("finite XYZ required")
    if any(type(x) not in (float, int) or not math.isfinite(x) or abs(x) > 1e12
           for x in value):
        raise ValueError("invalid finite XYZ")
    return tuple(float(x) for x in value)  # type: ignore[arg-type,return-value]


def _sample_rows(samples: Sequence, *, model: bool) -> tuple[list[tuple], str | None]:
    if type(samples) not in (list, tuple) or not 1 <= len(samples) <= _MAX_SAMPLES:
        raise ValueError("bounded nonempty sample sequence required")
    rows = []
    previous = -1
    for sample in samples:
        if model:
            if type(sample) not in (tuple, list) or len(sample) != 3:
                raise ValueError("M1 sample must be (step, position, velocity)")
            step, position, velocity = sample
        else:
            if not isinstance(sample, ReferenceSample):
                raise ValueError("typed ReferenceSample required")
            step, position, velocity = (sample.numerical_step, sample.position_xyz,
                                        sample.velocity_xyz)
            if type(sample.atomic) is not bool or type(sample.source_quality) is not str:
                raise ValueError("invalid reference sample provenance")
            if (sample.guest_physics_frame is not None
                    and (type(sample.guest_physics_frame) is not int
                         or not 0 <= sample.guest_physics_frame <= 1000000000)):
                raise ValueError("invalid guest-frame claim")
        if type(step) is not int or not 0 <= step <= 10000:
            raise ValueError("invalid numerical step")
        p = _xyz(position)
        v = _xyz(velocity) if velocity is not None else None
        if model and v is None:
            raise ValueError("M1 velocity required")
        rows.append((step, p, v))
        if step <= previous:
            return rows, "ABSTAIN_DUPLICATE_OR_NONMONOTONIC_STEP"
        previous = step
    return rows, None


def _report(status: str, *, model_count: int = 0, reference_count: int = 0,
            compared_steps: int = 0, skipped_steps: tuple[int, ...] = (),
            first_divergent_step: int | None = None,
            residuals: list[dict] | None = None,
            velocity_comparison: str = "UNKNOWN",
            f32_diagnostics: bool = False) -> dict:
    return {
        "schema": _SCHEMA, "status": status,
        "time_base": "unverified_numerical_steps",
        "model_count": model_count, "reference_count": reference_count,
        "compared_steps": compared_steps, "skipped_steps": list(skipped_steps),
        "first_divergent_step": first_divergent_step,
        "residuals": residuals if residuals is not None else [],
        "velocity_comparison": velocity_comparison,
        "host_f32_ulp_diagnostics": f32_diagnostics,
        "verified_native_guest_step_count": None,
        "guest_physics_clock_independently_verified": False,
        "selected_ball_world_xyz_verified": False,
        "native_game_parity_verified": False,
        "training_approved": False,
    }


def _word(value: float) -> int:
    try:
        return struct.unpack(">I", struct.pack(">f", value))[0]
    except (OverflowError, struct.error):
        raise ValueError("float32 diagnostic outside finite host range") from None


def _ulp(a: float, b: float) -> int:
    def ordered(word: int) -> int:
        return (~word & 0xffffffff) if word & 0x80000000 else word | 0x80000000
    return abs(ordered(_word(a)) - ordered(_word(b)))


def compare_airborne(
    model_trace: AirborneTrace,
    reference_samples: Sequence[ReferenceSample],
    *,
    model_identity: TraceIdentity,
    reference_identity: TraceIdentity,
    evidence: EvidenceLabels,
    position_atol: float = 0.0,
    velocity_atol: float = 0.0,
) -> dict:
    """Compare keyed *numerical steps* only when synthetic labels are safe.

    For a real/sanitized candidate, always abstain BEFORE exposing numerical
    residuals. Claimed source flags, guest clock and coordinate-basis statuses
    are not independent external proofs. Never zip disparate frame indices,
    interpolate a gap, or infer velocity by finite differences.
    """
    if not isinstance(model_trace, AirborneTrace) or not isinstance(evidence, EvidenceLabels):
        raise ValueError("typed M1 trace and EvidenceLabels required")
    _identity(model_identity)
    _identity(reference_identity)
    for name in ("position_atol", "velocity_atol"):
        value = locals()[name]
        if type(value) not in (int, float) or not math.isfinite(value) or value < 0 or value > 1e6:
            raise ValueError("invalid synthetic comparison tolerance")
    for name in ("source_revision_qualified", "source_archive_qualified",
                 "selected_receiver_qualified", "selected_ball_xyz_qualified",
                 "selected_launch_v0_qualified", "normalizer_branch_qualified",
                 "ppc_f32_qualified", "host_f32_operations_matched"):
        if type(getattr(evidence, name)) is not bool:
            raise ValueError("evidence labels must be strict booleans")
    if (model_trace.native_game_parity_verified is not False
            or model_trace.training_approved is not False
            or model_trace.time_base != "unverified_numerical_steps"
            or "zero_wind_only" not in model_trace.assumptions):
        return _report("ABSTAIN_MODEL_PROVENANCE")
    if model_identity.model_sha != reference_identity.model_sha:
        return _report("ABSTAIN_MODEL_SHA_MISMATCH")
    if model_identity != reference_identity:
        return _report("ABSTAIN_IDENTITY_OR_BASIS_MISMATCH")
    if model_trace.precision != model_identity.numeric_precision:
        return _report("ABSTAIN_NUMERIC_SEMANTICS_MISMATCH")

    # Observe the S002 evidence categories without treating user-provided
    # booleans, VI ticks, bridge callbacks or witness tags as native proof.
    if evidence.trace_kind != "synthetic":
        if evidence.clock_domain in ("host_callback", "vi_frame", "unknown"):
            return _report("ABSTAIN_UNVERIFIED_CLOCK_OR_IDENTITY")
        if (evidence.guest_step_status != "SYNTHETIC_CONTRACT_PASS"
                or not evidence.source_revision_qualified or not evidence.source_archive_qualified):
            return _report("ABSTAIN_UNVERIFIED_SOURCE_OR_GUEST_PC")
        if not evidence.selected_receiver_qualified:
            return _report("ABSTAIN_UNVERIFIED_SELECTED_BALL_RECEIVER")
        if not evidence.selected_launch_v0_qualified:
            return _report("ABSTAIN_UNVERIFIED_LAUNCH_V0")
        if (evidence.basis_status != "CONDITIONALLY_CONSISTENT"
                or not evidence.selected_ball_xyz_qualified):
            return _report("ABSTAIN_UNVERIFIED_COORDINATE_BASIS")
        if not evidence.normalizer_branch_qualified:
            return _report("ABSTAIN_UNVERIFIED_NORMALIZER_BRANCH")
        if not evidence.ppc_f32_qualified:
            return _report("ABSTAIN_UNVERIFIED_PPC_PRECISION")
        return _report("ABSTAIN_NATIVE_PARITY_REQUIRES_INDEPENDENT_PROOF")

    if (evidence.clock_domain != "synthetic_numerical_steps"
            or evidence.guest_step_status != "SYNTHETIC_CONTRACT_PASS"):
        return _report("ABSTAIN_UNVERIFIED_CLOCK_OR_IDENTITY")
    if evidence.basis_status not in ("SYNTHETIC_BASIS", "CONDITIONALLY_CONSISTENT"):
        return _report("ABSTAIN_UNVERIFIED_COORDINATE_BASIS")
    # Reject oversized input *before* traversing any reference provenance.
    # _sample_rows repeats this limit for defense in depth after the gate.
    if (type(reference_samples) not in (list, tuple)
            or not 1 <= len(reference_samples) <= _MAX_SAMPLES):
        raise ValueError("bounded nonempty reference sample sequence required")
    for entry in reference_samples:
        if not isinstance(entry, ReferenceSample):
            raise ValueError("typed reference samples only")
        if entry.guest_physics_frame is not None:
            return _report("ABSTAIN_UNVERIFIED_CLOCK_OR_IDENTITY")
        if entry.source_quality != "synthetic":
            return _report("ABSTAIN_UNVERIFIED_SOURCE_OR_GUEST_PC")
        if entry.atomic is not True:
            return _report("ABSTAIN_NONATOMIC_SAMPLE")
    model, model_order = _sample_rows(model_trace.samples, model=True)
    reference, reference_order = _sample_rows(reference_samples, model=False)
    if model_order or reference_order:
        return _report("ABSTAIN_DUPLICATE_OR_NONMONOTONIC_STEP",
                       model_count=len(model), reference_count=len(reference))
    model_steps = {row[0] for row in model}
    reference_steps = {row[0] for row in reference}
    union = model_steps | reference_steps
    skipped = tuple(sorted(set(range(0, max(union) + 1)) - (model_steps & reference_steps)))
    if skipped or model_steps != reference_steps:
        return _report("ABSTAIN_GAPPED_OR_UNALIGNED_STEPS",
                       model_count=len(model), reference_count=len(reference),
                       skipped_steps=skipped)

    host_f32 = (model_trace.precision == "host_f32"
                and evidence.host_f32_operations_matched)
    residuals: list[dict] = []
    first = None
    velocity_seen = 0
    for (step, mpos, mvel), (_, rpos, rvel) in zip(model, reference):
        pos_delta = tuple(a - b for a, b in zip(mpos, rpos))
        pos_norm = math.hypot(*pos_delta)
        if not math.isfinite(pos_norm):
            raise ValueError("nonfinite synthetic position residual")
        vel_delta = tuple(a - b for a, b in zip(mvel, rvel)) if rvel is not None else None
        vel_norm = math.hypot(*vel_delta) if vel_delta is not None else None
        if vel_norm is not None:
            velocity_seen += 1
            if not math.isfinite(vel_norm):
                raise ValueError("nonfinite synthetic velocity residual")
        if first is None and (pos_norm > position_atol
                              or (vel_norm is not None and vel_norm > velocity_atol)):
            first = step
        entry = {"numerical_step": step, "position_delta_xyz": pos_delta,
                 "position_l2": pos_norm, "velocity_delta_xyz": vel_delta,
                 "velocity_l2": vel_norm, "host_f32_position_ulp_xyz": None,
                 "host_f32_velocity_ulp_xyz": None}
        # M1 sample zero returns caller's unquantized p0/v0. Never claim
        # representational or PPC-bitwise equivalence from that sample.
        if host_f32 and step > 0:
            entry["host_f32_position_ulp_xyz"] = tuple(_ulp(a, b) for a, b in zip(mpos, rpos))
            if rvel is not None:
                entry["host_f32_velocity_ulp_xyz"] = tuple(_ulp(a, b) for a, b in zip(mvel, rvel))
        residuals.append(entry)
    velocity_status = ("UNKNOWN" if not velocity_seen else
                       "COMPLETE" if velocity_seen == len(reference) else "PARTIAL")
    return _report("ELIGIBLE_SYNTHETIC_COMPARISON",
                   model_count=len(model), reference_count=len(reference),
                   compared_steps=len(reference), first_divergent_step=first,
                   residuals=residuals, velocity_comparison=velocity_status,
                   f32_diagnostics=host_f32)
