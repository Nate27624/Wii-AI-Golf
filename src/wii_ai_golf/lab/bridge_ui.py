"""Presentation model for source-only V1/V2 bridge inspection in the Golf Lab.

Never contacts Dolphin. Historical copy identity and safety are different from
whether Wii Sports recognizes an input or whether a shot hits the ball.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..shared.bridge_provenance import audit_bridge_sources, inspect_bridge_file


@dataclass(frozen=True)
class BridgeView:
    state: str
    title: str
    detail: str
    current_revision: str
    current_sha: str | None
    backup_sha: str | None
    prepared_sha: str | None
    can_prepare: bool
    can_test: bool

    def as_text(self) -> str:
        def abbrev(sha: str | None) -> str:
            return sha[:16] + "…" if sha else "unavailable"
        return (
            f"{self.title}\n\n"
            f"Installed bridge: {self.current_revision}  |  SHA {abbrev(self.current_sha)}\n"
            f"Saved historical backup: {abbrev(self.backup_sha)}\n"
            f"Separate V1 test copy: {abbrev(self.prepared_sha)}\n\n"
            f"{self.detail}\n\n"
            "These checks inspect local files only. They do not verify which "
            "bridge Dolphin loaded, swing strength, ball contact, or score."
        )


def inspect_game_bridges(root: Path) -> BridgeView:
    """Provide a truthful, actionable status before enabling any game buttons."""
    current = root.parent / "tools" / "mcp_bridge_swing.py"
    isolated = root.parent / "tools" / "mcp_bridge_swing_legacy_eval.py"
    report = audit_bridge_sources(current)
    active = report["current"]
    saved = report["saved_pre_v2_backup"]
    candidate = inspect_bridge_file(isolated)

    v2_ok = active["revision"] == "V2-neutral-button-only"
    backup_ok = bool(saved["safe_for_isolated_legacy_copy"])
    prepared_safe = bool(candidate["safe_for_isolated_legacy_copy"])
    prepared_matches = bool(
        prepared_safe and backup_ok and candidate["sha256"] == saved["sha256"]
    )
    base = {
        "current_revision": active["revision"],
        "current_sha": active["sha256"],
        "backup_sha": saved["sha256"],
        "prepared_sha": candidate["sha256"],
    }
    if not v2_ok:
        return BridgeView(
            "blocked", "Bridge comparison cannot start",
            "The installed swing bridge is not identified as V2. "
            "Review the installed bridge before comparing V1 and V2. "
            "No files will be replaced automatically.",
            can_prepare=False, can_test=False, **base,
        )
    if not backup_ok:
        return BridgeView(
            "blocked", "Historical V1 backup unavailable",
            "No structurally valid, non-autoloading pre-V2 backup was found. "
            "The Lab will not fabricate a legacy bridge or overwrite V2. "
            "Inspect the saved backup provenance with the integration agent.",
            can_prepare=False, can_test=False, **base,
        )
    if candidate["exists"] and not prepared_matches:
        return BridgeView(
            "blocked", "Existing V1 test copy does not match the backup",
            "A separate test copy exists but cannot be verified as identical "
            "to the saved V1 backup. The Lab will not overwrite it or run it. "
            "Ask the integration agent to inspect the mismatch.",
            can_prepare=False, can_test=False, **base,
        )
    if prepared_matches:
        return BridgeView(
            "ready", "Ready for one historical V1 shot",
            "The isolated V1 bridge exactly matches the verified saved backup. "
            "Close Dolphin before step 3. Leave A prime at 0 and observed A lead "
            "at 0 for the controlled comparison; the actual hit is unverified.",
            can_prepare=False, can_test=True, **base,
        )
    return BridgeView(
        "needs_preparation", "Historical V1 backup found",
        "Step 2 can create a separate V1 diagnostic copy from this verified "
        "backup. This does not modify the installed V2 bridge or savestates.",
        can_prepare=True, can_test=False, **base,
    )
