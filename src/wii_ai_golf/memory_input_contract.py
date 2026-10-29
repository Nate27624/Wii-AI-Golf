"""Offline provenance contract for proposed input/actor/result joins.

Source offsets and callback traces alone are NOT verified Wii physics. This
module performs no RAM reads, emulator actions, publication or training.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Rejection(str, Enum):
    RUN_MISMATCH = "run_mismatch"
    SHOT_MISMATCH = "shot_mismatch"
    FRAME_MISMATCH = "guest_frame_mismatch"
    STALE_FRAME = "stale_frame"
    ACTOR_MISMATCH = "actor_mismatch"
    OBJECT_REPLACED = "object_replaced"
    CONTACT_UNVERIFIED = "contact_unverified"
    D1_CONTRADICTION = "d1_airborne_start_contradiction"
    CENSORED_OUTCOME = "censored_outcome"
    OUTCOME_UNVERIFIED = "outcome_unverified"
    NO_PHYSICAL_PROOF = "no_physical_proof"


@dataclass(frozen=True)
class InputReceipt:
    run_id: str
    shot_id: str
    guest_frame: int
    requested_a: bool
    callback_seen: bool
    game_side_a_accepted: bool
    contact_witness: bool


@dataclass(frozen=True)
class ActorReceipt:
    run_id: str
    shot_id: str
    guest_frame: int
    selected_address: int
    selected_generation: str
    global_address: int
    global_generation: str
    rendered_address: int
    rendered_generation: str
    source_state: str
    human_label: str


@dataclass(frozen=True)
class OutcomeReceipt:
    run_id: str
    shot_id: str
    guest_frame: int
    actor_address: int
    actor_generation: str
    source: str
    measurement: str
    censored: bool
    distance_label: str = ""


@dataclass(frozen=True)
class JoinDecision:
    # This indicates internally consistent SYNTHETIC fixtures, NOT real data.
    synthetic_consistent: bool
    real_training_eligible: bool
    validity_mask: tuple[str, ...]
    rejected: tuple[Rejection, ...]


def join_memory_input_observation(
    input_receipt: InputReceipt,
    actor: ActorReceipt,
    outcome: OutcomeReceipt,
    *,
    max_frame_lag: int = 0,
) -> JoinDecision:
    """Abstain on absent physical proof; never approve real-game training.

    Addresses must be positive candidate identifiers and generation/lifetime
    tokens must agree: equal pointers without equal lifetime IDs are unsafe.
    Frame tolerance defaults to exactly one guest frame; a positive permitted
    lag is explicit and does not imply observed physics continuity.
    """
    if max_frame_lag < 0:
        raise ValueError("max_frame_lag cannot be negative")
    rejected: list[Rejection] = []

    def reject(reason: Rejection) -> None:
        if reason not in rejected:
            rejected.append(reason)

    ids = (input_receipt.run_id, actor.run_id, outcome.run_id)
    shots = (input_receipt.shot_id, actor.shot_id, outcome.shot_id)
    if not all(ids) or len(set(ids)) != 1:
        reject(Rejection.RUN_MISMATCH)
    if not all(shots) or len(set(shots)) != 1:
        reject(Rejection.SHOT_MISMATCH)

    frames = (input_receipt.guest_frame, actor.guest_frame, outcome.guest_frame)
    if any(type(f) is not int or f < 0 for f in frames):
        reject(Rejection.FRAME_MISMATCH)
    elif len(set(frames)) != 1:
        reject(Rejection.FRAME_MISMATCH)
        if max(frames) - min(frames) > max_frame_lag:
            reject(Rejection.STALE_FRAME)

    addresses = (actor.selected_address, actor.global_address,
                 actor.rendered_address, outcome.actor_address)
    if any(type(a) is not int or a <= 0 for a in addresses) or len(set(addresses)) != 1:
        reject(Rejection.ACTOR_MISMATCH)

    generations = (actor.selected_generation, actor.global_generation,
                   actor.rendered_generation, outcome.actor_generation)
    if not all(generations) or len(set(generations)) != 1:
        reject(Rejection.OBJECT_REPLACED)

    if not (input_receipt.requested_a and input_receipt.callback_seen
            and input_receipt.game_side_a_accepted and input_receipt.contact_witness):
        reject(Rejection.CONTACT_UNVERIFIED)

    if actor.human_label.lower() == "airborne" and actor.source_state.upper() == "START":
        reject(Rejection.D1_CONTRADICTION)

    if (outcome.censored or outcome.distance_label == "offgreen_100ft_penalty"
            or outcome.measurement == "offgreen_100ft_penalty"):
        reject(Rejection.CENSORED_OUTCOME)
    if outcome.source != "synthetic" or outcome.measurement != "synthetic_distance":
        reject(Rejection.OUTCOME_UNVERIFIED)

    # Explicitly avoid silently converting a consistent toy fixture to an
    # independently verified physical sample.
    synthetic_consistent = not rejected
    return JoinDecision(
        synthetic_consistent=synthetic_consistent,
        real_training_eligible=False,
        validity_mask=("synthetic_internal_join",) if synthetic_consistent else (),
        rejected=tuple(rejected) + (Rejection.NO_PHYSICAL_PROOF,),
    )
