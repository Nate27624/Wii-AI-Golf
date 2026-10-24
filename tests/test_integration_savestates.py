import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from wii_ai_golf.integration.savestates import StateCatalog, StateManager, StateProfile


class FakeRPC:
    def __init__(self, valid=True):
        self.commands = []
        self.valid = valid
    def call(self, method, params=None):
        self.commands.append((method, params))
        if method == "bridge.ping":
            return {"bridge_version": "0.3.0"} if self.valid else None
        return None


class StateTests(unittest.TestCase):
    def test_slot_range_and_name_restrictions(self):
        for slot in (-1, 100, 255, True):
            with self.subTest(slot=slot), self.assertRaises(ValueError):
                StateProfile("first_shot", slot)
        for name in ("", "Other Name", "../foo", "A"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                StateProfile(name, 20)

    def test_manifest_roundtrip_and_unique_slots(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "catalog.json"
            catalog = StateCatalog(path)
            catalog.add(StateProfile("first_shot", 20, "Before swing", "RSPE01"))
            with self.assertRaises(ValueError):
                catalog.add(StateProfile("second", 20))
            with self.assertRaises(ValueError):
                catalog.add(StateProfile("first_shot", 21))
            catalog.save()
            recovered = StateCatalog(path)
            self.assertEqual(recovered.get("first_shot").slot, 20)
            self.assertEqual(json.loads(path.read_text())["schema_version"], 1)
            with self.assertRaises(ValueError):
                recovered.get("missing")

    def test_save_requires_overwrite_and_ping(self):
        rpc = FakeRPC()
        manager = StateManager(rpc)
        profile = StateProfile("shot", 20)
        with self.assertRaises(ValueError):
            manager.request_capture(profile)
        self.assertEqual(rpc.commands, [])
        response = manager.request_capture(profile, allow_overwrite=True)
        self.assertEqual(response["action"], "capture_requested")
        self.assertEqual(rpc.commands, [("bridge.ping", None), ("savestate.save_to_slot", [20])])

    def test_load_uses_named_slot(self):
        rpc = FakeRPC()
        result = StateManager(rpc).request_load(StateProfile("shot", 36))
        self.assertEqual(result["slot"], 36)
        self.assertEqual(rpc.commands[-1], ("savestate.load_from_slot", [36]))
        with self.assertRaises(RuntimeError):
            StateManager(FakeRPC(valid=False)).request_load(StateProfile("shot", 20))

    def test_bad_manifest_rejected(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "catalog.json"
            path.write_text('{"schema_version": 2, "profiles": []}', encoding="utf-8")
            with self.assertRaises(ValueError):
                StateCatalog(path)


if __name__ == "__main__":
    unittest.main()
