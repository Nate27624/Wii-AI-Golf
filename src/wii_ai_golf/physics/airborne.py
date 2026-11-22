"""Offline zero-wind airborne trajectory candidate for Wii Sports Golf.

This module does NOT establish native launch velocity, native guest-frame
duration, selected-Ball receiver, PPC float32/FMA parity, or force timing.
All coordinates and physics parameters are explicit caller inputs.

Ownership: S003-airborne-integration-20261112-a, issue #415.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import struct
from typing import Iterable, Literal, TypeAlias

Vec: TypeAlias = tuple[float, float, float]
Sample: TypeAlias = tuple[int, Vec, Vec]
Precision = Literal["host_f32", "binary64"]
SpeedPolicy = Literal["held_input", "recompute_from_velocity"]

# Source-supported numeric candidates, not a fully verified flight contract.
SOURCE_DAMPING_CANDIDATE = 0.999000013
SOURCE_LIFT_GAIN_CANDIDATE = 0.0012
SOURCE_SIDE_GAIN_CANDIDATE = 0.001
SOURCE_LIFT_DECAY_CANDIDATE = 0.9985
SOURCE_SIDE_DECAY_CANDIDATE = 0.997


class UnverifiedNormalizerBranch(ValueError):
    """Source's zero/epsilon vector-normalization branch is not established."""


def _scalar(value: float, label: str) -> float:
    if type(value) not in (int, float):
        raise ValueError(f"{label} must be a finite number")
    val = float(value)
    if not math.isfinite(val):
        raise ValueError(f"{label} must be finite")
    return val


def _xyz(value: Iterable[float], label: str) -> Vec:
    try:
        data = tuple(value)
    except TypeError:
        raise ValueError(f"{label} must be finite XYZ") from None
    if len(data) != 3:
        raise ValueError(f"{label} must be finite XYZ")
    return tuple(_scalar(x, label) for x in data)  # type: ignore[return-value]


def _round(value: float, precision: Precision) -> float:
    if not math.isfinite(value):
        raise ValueError("nonfinite intermediate physics state")
    if precision == "binary64":
        return value
    try:
        v = struct.unpack(">f", struct.pack(">f", value))[0]
    except (OverflowError, struct.error):
        raise ValueError("physics state exceeds finite host float32 range") from None
    if not math.isfinite(v):
        raise ValueError("nonfinite host float32 result")
    return v


def _add(a: Vec, b: Vec, precision: Precision) -> Vec:
    return tuple(_round(_round(x, precision) + _round(y, precision), precision)
                 for x, y in zip(a, b))  # type: ignore[return-value]


def _scale(a: Vec, factor: float, precision: Precision) -> Vec:
    k = _round(factor, precision)
    return tuple(_round(_round(x, precision) * k, precision)
                 for x in a)  # type: ignore[return-value]


@dataclass(frozen=True)
class SourceSpinCandidate:
    """Exploratory source-basis spin, with explicitly UNKNOWN native guards.

    Caller supplies the INITIAL speed-like scalar; it must not be silently
    computed from v0. Recomputed speed after each step is an optional
    hypothesis, not a proven native speed-cache contract.
    """

    speed_like: float
    lift: float
    lateral: float
    normalizer_guard_assumption: float
    speed_policy: SpeedPolicy = "held_input"
    lift_decay: float = SOURCE_LIFT_DECAY_CANDIDATE
    lateral_decay: float = SOURCE_SIDE_DECAY_CANDIDATE

    def __post_init__(self) -> None:
        for name in ("speed_like", "lift", "lateral",
                     "normalizer_guard_assumption", "lift_decay", "lateral_decay"):
            _scalar(getattr(self, name), name)
        if self.speed_like < 0 or self.normalizer_guard_assumption < 0:
            raise ValueError("negative speed-like scalar or guard assumption")
        if not 0 <= self.lift_decay <= 1 or not 0 <= self.lateral_decay <= 1:
            raise ValueError("invalid spin decay")
        if self.speed_policy not in ("held_input", "recompute_from_velocity"):
            raise ValueError("unknown speed-cache hypothesis")


@dataclass(frozen=True)
class FlightParameters:
    """Explicit assumed accelerations and damping per unverified step."""

    acceleration_xyz: Vec
    damping: float
    precision: Precision = "host_f32"
    spin: SourceSpinCandidate | None = None

    def __post_init__(self) -> None:
        _xyz(self.acceleration_xyz, "acceleration_xyz")
        _scalar(self.damping, "damping")
        if not 0 <= self.damping <= 1:
            raise ValueError("damping must be in [0,1]")
        if self.precision not in ("host_f32", "binary64"):
            raise ValueError("unsupported numerical precision")
        if self.spin is not None and not isinstance(self.spin, SourceSpinCandidate):
            raise ValueError("spin must be an explicit SourceSpinCandidate")


@dataclass(frozen=True)
class AirborneTrace:
    samples: tuple[Sample, ...]
    precision: Precision
    assumptions: tuple[str, ...]
    time_base: str = "unverified_numerical_steps"
    native_game_parity_verified: bool = False
    training_approved: bool = False


def source_direction_candidate(velocity: Vec, guard_assumption: float,
                               precision: Precision = "host_f32", *,
                               require_lift: bool = True,
                               require_side: bool = True) -> tuple[Vec, Vec]:
    """Return required (lift, side) unit directions; unused terms become zero.

    S=(vz,0,-vx), L=(-vx*vy,vx^2+vz^2,-vz*vy). Their native zero/epsilon
    predicates are UNKNOWN. An inactive term must not force normalization of
    its vanishing direction (e.g. vy=0: |L|=horizontal_speed**2 while
    |S|=horizontal_speed). This skip is a candidate, NOT a native CFG proof.
    """
    v = _xyz(velocity, "velocity")
    guard = _scalar(guard_assumption, "normalizer_guard_assumption")
    if (guard < 0 or precision not in ("host_f32", "binary64")
            or type(require_lift) is not bool or type(require_side) is not bool):
        raise ValueError("invalid normalizer guard, precision or required terms")
    vx, vy, vz = (_round(x, precision) for x in v)
    side = (vz, 0.0, -vx)
    lift = (_round(-vx * vy, precision),
            _round(_round(vx * vx, precision) + _round(vz * vz, precision), precision),
            _round(-vz * vy, precision))

    directions: list[Vec] = []
    for raw, required in ((lift, require_lift), (side, require_side)):
        if not required:
            directions.append((0.0, 0.0, 0.0))
            continue
        length = math.hypot(*raw)
        if not math.isfinite(length) or length <= guard:
            raise UnverifiedNormalizerBranch(
                "ABSTAIN_UNVERIFIED_NORMALIZER_BRANCH: required force direction"
            )
        directions.append(tuple(_round(x / length, precision) for x in raw))
    return directions[0], directions[1]


def _spin_force(velocity: Vec, speed: float, lift: float, side: float,
                guard: float, precision: Precision) -> Vec:
    if speed == 0 or (lift == 0 and side == 0):
        return (0.0, 0.0, 0.0)
    lift_hat, side_hat = source_direction_candidate(
        velocity, guard, precision,
        require_lift=(lift != 0), require_side=(side != 0))
    lift_gain = _round(_round(SOURCE_LIFT_GAIN_CANDIDATE, precision)
                       * _round(speed, precision), precision)
    lift_gain = _round(lift_gain * _round(lift, precision), precision)
    side_gain = _round(_round(SOURCE_SIDE_GAIN_CANDIDATE, precision)
                       * _round(speed, precision), precision)
    side_gain = _round(side_gain * _round(side, precision), precision)
    return _add(_scale(lift_hat, lift_gain, precision),
                _scale(side_hat, side_gain, precision), precision)


def sample_trajectory(initial_position_xyz: Vec,
                      initial_velocity_xyz: Vec,
                      params: FlightParameters, *,
                      steps: int) -> AirborneTrace:
    """Produce (0,p0,v0), (1,p1,v1), ... with source-guided candidate order.

    For each step u=v+a; p_next=p+u; v_next=d*u. In host_f32 mode each
    scalar operation is rounded to IEEE binary32 on the host. This is NOT
    native Gekko FMA, instruction order or guest-tick proof. Inputs at
    sample zero are returned EXACTLY as supplied; state is quantized
    before first host_f32 arithmetic.
    """
    if not isinstance(params, FlightParameters):
        raise ValueError("explicit FlightParameters required")
    if type(steps) is not int or not 1 <= steps <= 10000:
        raise ValueError("steps must be an integer 1..10000")
    initial_p = _xyz(initial_position_xyz, "initial_position_xyz")
    initial_v = _xyz(initial_velocity_xyz, "initial_velocity_xyz")
    precision = params.precision

    p = tuple(_round(x, precision) for x in initial_p)
    v = tuple(_round(x, precision) for x in initial_v)
    a = tuple(_round(x, precision) for x in params.acceleration_xyz)
    damping = _round(params.damping, precision)
    samples: list[Sample] = [(0, initial_p, initial_v)]

    spin = params.spin
    if spin is not None:
        speed = _round(spin.speed_like, precision)
        lift = _round(spin.lift, precision)
        lateral = _round(spin.lateral, precision)

    for index in range(1, steps + 1):
        if spin is not None:
            force = _spin_force(v, speed, lift, lateral,
                                spin.normalizer_guard_assumption, precision)
            effective_a = _add(a, force, precision)
        else:
            effective_a = a

        # Deliberately source-guided candidate order; no new CCD here.
        u = _add(v, effective_a, precision)
        p = _add(p, u, precision)
        v = _scale(u, damping, precision)
        samples.append((index, p, v))

        if spin is not None:
            lift = _round(lift * _round(spin.lift_decay, precision), precision)
            lateral = _round(lateral * _round(spin.lateral_decay, precision), precision)
            if spin.speed_policy == "recompute_from_velocity":
                speed = _round(math.hypot(*v), precision)

    assumptions = (
        "zero_wind_only",
        "supplied_acceleration_not_verified_native_q",
        "source_guided_update_order_not_guest_verified",
        "unverified_numerical_step_not_seconds_or_guest_frame",
        "selected_ball_v0_and_receiver_unverified",
        "input_state_quantized_before_first_step",
        "host_float32_not_ppc_fma" if precision == "host_f32"
        else "binary64_exploratory_not_native_float32",
    )
    if spin is not None:
        assumptions += (
            "source_direction_candidates_not_verified_per_selected_ball",
            "normalizer_guard_assumed_not_source_verified",
            "speed_cache_policy_assumed_not_verified",
            "force_magnitude_and_decay_timing_assumed",
        )
    return AirborneTrace(tuple(samples), precision, assumptions)


def predict_provisional_contact(trace: AirborneTrace, terrain: Iterable[object],
                                *, contact_mode: str = "point_center",
                                assume_tree_free: bool = False) -> dict:
    """Consume existing S003 first-contact API. No duplicate collision code."""
    if not isinstance(trace, AirborneTrace):
        raise ValueError("explicit AirborneTrace required")
    from wii_ai_golf.physics.first_contact import predict_contact_from_trajectory

    result = dict(predict_contact_from_trajectory(
        trace.samples, terrain, contact_mode=contact_mode,
        assume_tree_free=assume_tree_free))
    result["trajectory_provenance"] = "S003_M1_OFFLINE_ZERO_WIND_CANDIDATE"
    result["trajectory_assumptions"] = list(trace.assumptions)
    result["time_base"] = "unverified_numerical_steps"
    result["native_game_parity_verified"] = False
    result["training_approved"] = False
    return result
