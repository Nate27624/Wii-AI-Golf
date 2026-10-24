"""Save/load/list named local Dolphin savestate checkpoints.

The JSON registry contains labels and slots, never game ROMs or savestate bytes.
"""
import argparse
import json
from pathlib import Path

from wii_ai_golf.integration.rpc import FelkRPC
from wii_ai_golf.integration.savestates import SavestateManager, read_registry, register, resolve

DEFAULT_REGISTRY = Path("research/local-savestates.json")


def main() -> None:
    p = argparse.ArgumentParser(description="Named savestate checkpoints for any Wii AI Golf training scene")
    p.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    p.add_argument("--port", type=int, default=55355)
    sub = p.add_subparsers(dest="command", required=True)
    reg = sub.add_parser("register", help="Assign a stable name to an emulator slot")
    reg.add_argument("name")
    reg.add_argument("--slot", type=int, required=True)
    reg.add_argument("--note", default="")
    reg.add_argument("--overwrite", action="store_true")
    for command in ("save", "load"):
        q = sub.add_parser(command)
        q.add_argument("checkpoint", help="Registered name or numeric slot")
        q.add_argument("--confirm-overwrite", action="store_true") if command == "save" else None
    sub.add_parser("list")
    args = p.parse_args()
    if args.command == "register":
        register(args.registry, args.name, args.slot, args.note, overwrite=args.overwrite)
        print(f"Registered checkpoint {args.name} -> slot {args.slot}")
        return
    if args.command == "list":
        print(json.dumps(read_registry(args.registry), indent=2))
        return
    slot = resolve(args.registry, args.checkpoint)
    if args.command == "save" and not args.confirm_overwrite:
        p.error("Saving overwrites the current contents of that Dolphin slot. Pass --confirm-overwrite.")
    with FelkRPC(port=args.port) as rpc:
        manager = SavestateManager(rpc)
        getattr(manager, args.command)(slot)
    print(f"{args.command} requested for slot {slot}. Confirm on-screen state; an RPC acknowledgement does not independently verify restore success.")


if __name__ == "__main__":
    main()
