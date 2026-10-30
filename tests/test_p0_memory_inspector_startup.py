"""Pure and UI fake tests for explicit PowerShell game startup handoff."""
from pathlib import Path
import tempfile
import sys
import unittest
from unittest.mock import patch, Mock

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from wii_ai_golf.inspector import startup


class StartupTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup)
        self.base=Path(t.name)
        self.runtime=self.base/'Wii-AI-Golf'
        self.runtime.mkdir()
        self.inspector=self.base/'Wii-AI-Golf-Inspector';self.inspector.mkdir()
        (self.runtime/'scripts').mkdir()
        (self.runtime/'research').mkdir()
        (self.runtime/'scripts'/'launch_golf.py').write_text('')
        (self.runtime/'scripts'/'launch_hitting_green.py').write_text('')
        (self.runtime/'research'/'savestates.local.json').write_text('{}')
        self.python=self.base/'Pytho\'n'/'python.exe';self.python.parent.mkdir()
        self.python.write_text('')

    def test_runtime_checkout_prefers_canonical_private_catalog(self):
        self.assertEqual(startup.runtime_checkout(self.inspector),self.runtime)
        self.assertEqual(startup.runtime_checkout(self.runtime),self.runtime)

    def test_missing_private_catalog_blocks_before_process_spawn(self):
        (self.runtime/'research'/'savestates.local.json').unlink()
        with self.assertRaisesRegex(startup.StartupError,'savestate'):
            startup.runtime_checkout(self.inspector)

    def test_fresh_launch_uses_existing_launcher_without_swing(self):
        args=startup.powershell_command(self.runtime,self.python,55355,attach=False)
        self.assertEqual(args[:4],['powershell.exe','-NoProfile','-NoExit','-Command'])
        code=args[-1]
        self.assertIn('launch_golf.py',code)
        self.assertIn('--profile green-pre-start --port 55355',code)
        self.assertNotIn('--attach-running',code)
        self.assertNotIn('--swing',code)
        self.assertIn("Pytho''n",code)
        self.assertIn("Set-Location -LiteralPath",code)

    def test_existing_bridge_uses_existing_attach_reset_and_menu_dispatch(self):
        code=startup.powershell_command(self.runtime,self.python,55355,attach=True)[-1]
        self.assertIn('launch_hitting_green.py',code)
        self.assertIn('--attach-running --send-live',code)
        self.assertNotIn('--swing',code)

    def test_port_validation_and_no_shell_reinterpretation(self):
        for p in (0,-1,65536,True,3.5):
            with self.subTest(p=p),self.assertRaises(startup.StartupError):
                startup.powershell_command(self.runtime,self.python,p,attach=False)

    def test_open_bridge_probe_is_loopback_only(self):
        with patch.object(startup.socket,'create_connection',side_effect=OSError) as c:
            self.assertFalse(startup.occupied_bridge(55355))
            self.assertEqual(c.call_args.args[0],('127.0.0.1',55355))
        with patch.object(startup.socket,'create_connection') as c:
            self.assertTrue(startup.occupied_bridge(55355))

    def test_gui_handler_opens_powershell_after_confirm_and_stops_sampler(self):
        try:
            from wii_ai_golf.inspector import gui
        except ImportError:
            self.skipTest('Tkinter unavailable')
        class Var:
            def __init__(self,value=''):self.value=value
            def get(self):return self.value
            def set(self,value):self.value=value
        class FakeThread:
            def __init__(self):self.joins=[]
            def is_alive(self):return not self.joins
            def join(self,timeout):self.joins.append(timeout)
        class FakeWorker:
            def __init__(self):self.thread=FakeThread();self.stopped=False
            def stop(self):self.stopped=True
        obj=object.__new__(gui.Inspector)
        worker=FakeWorker();obj.live_worker=worker;obj.live_port=Var('55355')
        obj.a_status=Var('A RELEASED');obj.a_reason=Var('candidate')
        obj.status=Var();obj.live_last=10
        obj.a_indicator=Mock();obj.startup_process=None
        obj.draw_a_overlay=Mock()
        with patch.object(gui.platform,'system',return_value='Windows'), \
             patch.object(gui,'runtime_checkout',return_value=self.runtime), \
             patch.object(gui,'occupied_bridge',return_value=True), \
             patch.object(gui,'powershell_command',return_value=['powershell.exe','-NoExit']), \
             patch.object(gui.messagebox,'askyesno',return_value=True), \
             patch.object(gui.subprocess,'Popen',return_value=Mock(poll=lambda:0)) as popen:
            obj.open_game_startup()
        self.assertTrue(worker.stopped)
        self.assertEqual(worker.thread.joins,[2.0])
        self.assertIsNone(obj.live_worker)
        self.assertEqual(obj.a_status.get(),'A UNKNOWN')
        self.assertIn('No swing',obj.status.get())
        self.assertEqual(popen.call_args.args[0],['powershell.exe','-NoExit'])
        self.assertFalse(popen.call_args.kwargs['shell'])

    def test_gui_cancel_and_non_windows_never_start(self):
        try:from wii_ai_golf.inspector import gui
        except ImportError:self.skipTest('Tkinter unavailable')
        class Var:
            def get(self):return '55355'
        obj=object.__new__(gui.Inspector);obj.startup_process=None;obj.live_port=Var()
        with patch.object(gui.platform,'system',return_value='Windows'), \
             patch.object(gui,'runtime_checkout',return_value=self.runtime), \
             patch.object(gui,'occupied_bridge',return_value=False), \
             patch.object(gui,'powershell_command',return_value=['powershell.exe']), \
             patch.object(gui.messagebox,'askyesno',return_value=False), \
             patch.object(gui.subprocess,'Popen') as popen:
            obj.open_game_startup();popen.assert_not_called()
        with patch.object(gui.platform,'system',return_value='Linux'), \
             patch.object(gui.messagebox,'showerror'), \
             patch.object(gui.subprocess,'Popen') as popen:
            obj.open_game_startup();popen.assert_not_called()

if __name__=='__main__':unittest.main()
