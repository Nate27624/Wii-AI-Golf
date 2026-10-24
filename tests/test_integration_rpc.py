import json
import socketserver
import threading
import unittest

from wii_ai_golf.integration.rpc import BridgeProtocolError, BridgeRemoteError, FelkRPC


class _Handler(socketserver.StreamRequestHandler):
    def handle(self):
        for line in self.rfile:
            request = json.loads(line)
            if request["method"] == "id-mismatch":
                reply = {"id": request["id"] + 100, "result": "no"}
            elif request["method"] == "remote-error":
                reply = {"id": request["id"], "error": "simulation failed"}
            elif request["method"] == "oversize":
                reply = {"id": request["id"], "result": "x" * 512}
            else:
                reply = {"id": request["id"], "result": request["params"]}
            text = json.dumps(reply).encode() + b"\n"
            self.wfile.write(text[:7])
            self.wfile.flush()
            self.wfile.write(text[7:])
            self.wfile.flush()


class _Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


class RPCWireTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = _Server(("127.0.0.1", 0), _Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def bridge(self, **kwargs):
        return FelkRPC(port=self.server.server_address[1], **kwargs)

    def test_response_and_ids_across_requests(self):
        with self.bridge() as b:
            self.assertEqual(b.call("echo", [1, 2]), [1, 2])
            self.assertEqual(b.call("echo", [3]), [3])

    def test_detect_remote_error(self):
        with self.bridge() as b:
            with self.assertRaisesRegex(BridgeRemoteError, "simulation failed"):
                b.call("remote-error")

    def test_reject_bad_id(self):
        with self.bridge() as b:
            with self.assertRaisesRegex(BridgeProtocolError, "ID mismatch"):
                b.call("id-mismatch")

    def test_reject_oversized_response(self):
        with self.bridge(max_response_bytes=128) as b:
            with self.assertRaisesRegex(BridgeProtocolError, "size limit"):
                b.call("oversize")

    def test_disallow_remote_host(self):
        with self.assertRaises(ValueError):
            FelkRPC(host="8.8.8.8")
        with self.assertRaises(ValueError):
            FelkRPC(host="my-remote-pc")

    def test_require_connection(self):
        with self.assertRaises(RuntimeError):
            self.bridge().call("echo")


if __name__ == "__main__":
    unittest.main()
