"""Auto-run allowlist never starts live or input-dependent work."""
import importlib.util
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("run_lab_offline_batch",ROOT/"scripts"/"run_lab_offline_batch.py")
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class BatchTests(unittest.TestCase):
    def test_live_and_planned_never_selected(self):
        catalog=[
            {"id":"core.tests","kind":"tests_all","mode":"offline"},
            {"id":"evaluation.trace","kind":"focused_trace","mode":"offline"},
            {"id":"evaluation.capture","kind":"capture","mode":"live"},
            {"id":"modeling.sweep","kind":"unavailable","mode":"planned"},
            {"id":"learning.demo","kind":"demo","mode":"offline"},
        ]
        self.assertEqual(module.eligible(catalog),["core.tests","learning.demo"])
    def test_user_manifest_cannot_make_live_kind_auto_run(self):
        items=[{"id":"evil.test","kind":"capture","mode":"offline"},
               {"id":"evil.demo","kind":"demo","mode":"live"}]
        self.assertEqual(module.eligible(items),[])
if __name__=="__main__":unittest.main()
