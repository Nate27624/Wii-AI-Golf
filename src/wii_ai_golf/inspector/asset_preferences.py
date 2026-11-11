"""Local-only inspector startup asset selections (paths, never private geometry).

An explicit successful selection is remembered under the user's OS config
directory, outside every Git worktree. On restart the normal strict private
loaders validate the bytes again. No ROM-derived coordinates, models or
textures are copied into this settings record.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import json
import os
from pathlib import Path
import stat
import tempfile

from .tree_positions import EXPECTED_NAME, load_private_tree_positions, TreePositionsError

SETTINGS_FILE = "inspector-assets-v1.json"
SETTINGS_VERSION = 1
MAX_SETTINGS_BYTES = 8192
MAX_PATH_CHARS = 2048


class SavedAssetError(ValueError):
    """Unsafe or malformed local inspector asset settings."""


@dataclass(frozen=True)
class AssetSelections:
    terrain_obj: str | None = None
    tree_json: str | None = None
    auto_find_trees: bool = True


def local_settings_path() -> Path:
    """Per-user settings directory, never inside the checkout."""
    if os.name == "nt":
        root = os.environ.get("LOCALAPPDATA")
        base = Path(root) if root and Path(root).is_absolute() else Path.home() / "AppData" / "Local"
        return base / "WiiAIGolf" / SETTINGS_FILE
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg) if xdg and Path(xdg).is_absolute() else Path.home() / ".config"
    return base / "wii-ai-golf" / SETTINGS_FILE


def _is_link(path: Path) -> bool:
    try:
        st = path.lstat()
    except FileNotFoundError:
        return False
    return path.is_symlink() or bool(
        getattr(st, "st_file_attributes", 0)
        & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))


def _validate_settings_location(path: Path) -> None:
    if not path.is_absolute():
        raise SavedAssetError("Settings path must be absolute")
    # Reject linked/junction settings file and parent; avoid writing elsewhere.
    if _is_link(path) or _is_link(path.parent):
        raise SavedAssetError("Linked settings file/directory refused")
    if path.exists() and not path.is_file():
        raise SavedAssetError("Settings must be a regular local file")


def _safe_path(value: object) -> bool:
    return (value is None or
            (type(value) is str and 0 < len(value) <= MAX_PATH_CHARS
             and "\x00" not in value and "\n" not in value and "\r" not in value
             and Path(value).is_absolute()))


def _validate(selections: AssetSelections) -> None:
    if type(selections) is not AssetSelections:
        raise SavedAssetError("Unexpected saved selections object")
    if not _safe_path(selections.terrain_obj) or not _safe_path(selections.tree_json):
        raise SavedAssetError("Invalid saved local asset path")
    if type(selections.auto_find_trees) is not bool:
        raise SavedAssetError("Invalid tree auto-discovery setting")


def load_asset_selections(path: Path | None = None) -> AssetSelections:
    file = local_settings_path() if path is None else Path(path)
    _validate_settings_location(file)
    if not file.exists():
        return AssetSelections()
    if not 0 < file.stat().st_size <= MAX_SETTINGS_BYTES:
        raise SavedAssetError("Local inspector settings exceed safe bound")
    try:
        raw = json.loads(file.read_text("utf-8"), parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Nonfinite JSON")))
    except (UnicodeError, ValueError) as exc:
        raise SavedAssetError("Malformed local inspector settings") from exc
    if type(raw) is not dict or set(raw) != {"version", "terrain_obj", "tree_json", "auto_find_trees"}:
        raise SavedAssetError("Unexpected inspector asset settings schema")
    if type(raw["version"]) is not int or raw["version"] != SETTINGS_VERSION:
        raise SavedAssetError("Unsupported inspector asset settings version")
    selections = AssetSelections(raw["terrain_obj"], raw["tree_json"], raw["auto_find_trees"])
    _validate(selections)
    return selections


def save_asset_selections(selections: AssetSelections, path: Path | None = None) -> Path:
    """Atomically replace only the path record; never store source file bytes."""
    _validate(selections)
    file = local_settings_path() if path is None else Path(path)
    _validate_settings_location(file)
    if not file.parent.exists():
        file.parent.mkdir(parents=True, exist_ok=True)
    _validate_settings_location(file)
    payload = json.dumps({
        "version": SETTINGS_VERSION,
        "terrain_obj": selections.terrain_obj,
        "tree_json": selections.tree_json,
        "auto_find_trees": selections.auto_find_trees,
    }, sort_keys=True).encode("utf-8")
    if len(payload) > MAX_SETTINGS_BYTES:
        raise SavedAssetError("Inspector settings exceed safe bound")
    # Atomic write in same directory; no hidden data or assets are committed.
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(prefix=".inspector-assets-", suffix=".tmp",
                                         dir=file.parent, delete=False) as tmp:
            temp_path = Path(tmp.name)
            tmp.write(payload)
            tmp.flush()
            os.fsync(tmp.fileno())
        os.replace(temp_path, file)
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
    return file


def remember_asset(selections: AssetSelections, kind: str, filename: str | Path | None) -> AssetSelections:
    """Pure preference update; the GUI validates every asset before calling."""
    if kind not in ("terrain_obj", "tree_json"):
        raise SavedAssetError("Unknown inspector asset type")
    value = None if filename is None else str(Path(filename).resolve(strict=True))
    if kind == "tree_json":
        updated = replace(selections, tree_json=value, auto_find_trees=value is not None)
    else:
        updated = replace(selections, terrain_obj=value)
    _validate(updated)
    return updated


def private_tree_candidates(checkout: Path) -> tuple[Path, ...]:
    """Only specific known local private paths, no recursive/remote lookup."""
    base = Path(checkout).resolve()
    return (
        base.parent / "Wii-AI-Golf-Data" / "derived" / EXPECTED_NAME,
        base.parent / "Wii Golf AI" / "Wii-AI-Golf-Data" / "derived" / EXPECTED_NAME,
        base / "Wii-AI-Golf-Data" / "derived" / EXPECTED_NAME,
    )


def inspect_private_trees(checkout: Path) -> tuple[Path | None, tuple[tuple[Path, str], ...]]:
    """Validate known PRIVATE locations and report why each was not used.

    This deliberately never scans arbitrary directories and never bypasses
    the strict schema, Git-location or Windows reparse-point checks. Results
    contain paths and diagnostic strings only, not coordinate data.
    """
    checked: list[tuple[Path, str]] = []
    seen: set[str] = set()
    for path in private_tree_candidates(checkout):
        key = str(path).casefold() if os.name == "nt" else str(path)
        if key in seen:
            continue
        seen.add(key)
        if not path.is_file():
            checked.append((path, "missing"))
            continue
        try:
            load_private_tree_positions(path)
        except (TreePositionsError, OSError, ValueError) as exc:
            checked.append((path, f"rejected: {exc}"))
            continue
        checked.append((path, "validated"))
        return path, tuple(checked)
    return None, tuple(checked)


def discover_private_tree(checkout: Path) -> Path | None:
    """Backward-compatible read-only strict automatic lookup."""
    result, _ = inspect_private_trees(checkout)
    return result
