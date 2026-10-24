import unittest

from wii_ai_golf.integration.atomic_client import AtomicSample, AtomicTraceClient


class MockExtension:
    def __init__(self):
        self.state = {"state": "idle"}
        self.n = 0
        self.commands = []

    def call(self, method, params=None):
        self.commands.append((method, params))
        if method == "trace.submit":
            self.n = len(params[1])
            self.state = {"id": 1, "state": "scheduled", "applied_frames": 0}
        if method == "trace.status":
            self.state = {"id": 1, "state": "complete", "applied_frames": self.n}
        if method == "trace.abort":
            self.state["state"] = "aborted"
        return dict(self.state)


class AtomicClientTests(unittest.TestCase):
    def test_submit_status(self):
        mock = MockExtension()
        cli = AtomicTraceClient(mock)
        result = cli.run([AtomicSample(True, (0, 1, 0)), AtomicSample(False, (0, 1, 0))])
        self.assertEqual(result["applied_frames"], 2)
        self.assertEqual(mock.commands[0][0], "trace.submit")
        self.assertEqual(mock.commands[0][1][1][1], [False, 0, 1, 0])

    def test_never_claim_complete_without_ack(self):
        class Stalled(MockExtension):
            def call(self, method, params=None):
                if method == "trace.status":
                    return {"id": 1, "state": "running", "applied_frames": 0}
                return super().call(method, params)
        mock = Stalled()
        with self.assertRaises(TimeoutError):
            AtomicTraceClient(mock, max_polls=2).run([AtomicSample(True, (0, 1, 0))])
        self.assertEqual(mock.commands[-1][0], "trace.abort")

    def test_reject_nonfinite_samples(self):
        with self.assertRaises(ValueError):
            AtomicSample(True, (0, float("nan"), 0))

    def test_refuse_empty_trace(self):
        with self.assertRaises(ValueError):
            AtomicTraceClient(MockExtension()).submit([])


if __name__ == "__main__":
    unittest.main()
