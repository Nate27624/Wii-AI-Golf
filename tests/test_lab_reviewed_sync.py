"""Reviewed-only UI sync must never import arbitrary PR code."""
import unittest
from pathlib import Path
from types import SimpleNamespace
from wii_ai_golf.lab.sync import sync_reviewed_main

def fake(commands,values):
    def run(cmd,**kw):
        op=tuple(cmd[3:])
        if op not in values: raise AssertionError(op)
        code,value=values[op]
        return SimpleNamespace(returncode=code,stdout=value,stderr=value if code else "")
    return run

class TestSafeSync(unittest.TestCase):
    def test_clean_main_fast_forward_only(self):
        values={
          ("branch","--show-current"):(0,"main"),
          ("status","--porcelain"):(0,""),
          ("remote","get-url","origin"):(0,"https://github.com/Nate27624/Wii-AI-Golf.git"),
          ("rev-parse","HEAD"):(0,"a"*40),
          ("fetch","origin","main"):(0,""),
          ("merge","--ff-only","origin/main"):(0,""),
        }
        result=sync_reviewed_main(Path("dummy"),runner=fake(None,values))
        self.assertFalse(result["updated"])
    def test_detached_refuses_before_fetch(self):
        with self.assertRaisesRegex(ValueError,"main branch"):
            sync_reviewed_main(Path("dummy"),runner=fake(None,{("branch","--show-current"):(0,"")}))
    def test_dirty_refuses_before_fetch(self):
        with self.assertRaisesRegex(ValueError,"Uncommitted"):
            sync_reviewed_main(Path("dummy"),runner=fake(None,{
                ("branch","--show-current"):(0,"main"),
                ("status","--porcelain"):(0," M src/x.py")}))
if __name__=="__main__":unittest.main()
