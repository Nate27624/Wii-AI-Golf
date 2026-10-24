"""Conservative, loopback-only JSON-lines client for mcp-dolphin's Felk bridge v0.2.

Source: https://github.com/dmang-dev/mcp-dolphin/blob/main/bridge/mcp_bridge.py
This is a protocol client, not proof that the game recognizes scripted motion.
"""
from __future__ import annotations

import ipaddress
import json
import socket
from typing import Any


class BridgeProtocolError(RuntimeError):
    """Bridge returned an invalid or mismatched response."""


class BridgeRemoteError(RuntimeError):
    """Bridge returned a structured remote error."""


class FelkRPC:
    """Persistent RPC connection. Never connect to anything but loopback.

    The server polls its TCP socket on the emulator frame thread; when the
    emulator is paused, requests can time out. One outstanding request at a
    time avoids response interleaving. No frame-perfect guarantee is implied.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 55355,
                 timeout_s: float = 5.0, max_response_bytes: int = 65536) -> None:
        if host == "localhost":
            host = "127.0.0.1"
        try:
            if not ipaddress.ip_address(host).is_loopback:
                raise ValueError("Bridge connection must stay on loopback")
        except ValueError as exc:
            raise ValueError("Bridge host must be a numeric loopback address or 'localhost'") from exc
        if not 1 <= port <= 65535:
            raise ValueError("Port must be 1..65535")
        if timeout_s <= 0 or max_response_bytes < 128:
            raise ValueError("Positive timeout and max_response_bytes >= 128 required")
        self.host = host
        self.port = port
        self.timeout_s = timeout_s
        self.max_response_bytes = max_response_bytes
        self._socket: socket.socket | None = None
        self._buffer = bytearray()
        self._next_id = 1

    def __enter__(self) -> "FelkRPC":
        self.connect()
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def connect(self) -> None:
        if self._socket is not None:
            raise RuntimeError("Already connected")
        self._socket = socket.create_connection((self.host, self.port), timeout=self.timeout_s)
        self._socket.settimeout(self.timeout_s)
        self._buffer.clear()

    def close(self) -> None:
        if self._socket is not None:
            self._socket.close()
            self._socket = None
        self._buffer.clear()

    def _readline(self) -> bytes:
        assert self._socket is not None
        while b"\n" not in self._buffer:
            if len(self._buffer) > self.max_response_bytes:
                self.close()
                raise BridgeProtocolError("Bridge response exceeds size limit")
            chunk = self._socket.recv(4096)
            if not chunk:
                self.close()
                raise BridgeProtocolError("Bridge closed socket before completing response")
            self._buffer.extend(chunk)
        pos = self._buffer.index(b"\n")
        if pos > self.max_response_bytes:
            self.close()
            raise BridgeProtocolError("Bridge response exceeds size limit")
        line = bytes(self._buffer[:pos])
        del self._buffer[:pos + 1]
        return line

    def call(self, method: str, params: list[Any] | None = None) -> Any:
        if self._socket is None:
            raise RuntimeError("Not connected: use 'with FelkRPC() as bridge:'")
        if not method or not isinstance(method, str):
            raise ValueError("method must be nonempty string")
        msg_id = self._next_id
        self._next_id += 1
        body = json.dumps({"id": msg_id, "method": method, "params": [] if params is None else params},
                          allow_nan=False, separators=(",", ":")) + "\n"
        self._socket.sendall(body.encode("utf-8"))
        try:
            response = json.loads(self._readline())
        except (ValueError, UnicodeDecodeError) as exc:
            self.close()
            raise BridgeProtocolError("Invalid JSON response from bridge") from exc
        if not isinstance(response, dict) or response.get("id") != msg_id:
            self.close()
            raise BridgeProtocolError(f"RPC response ID mismatch (expected {msg_id})")
        if "error" in response:
            raise BridgeRemoteError(str(response["error"]))
        if "result" not in response:
            raise BridgeProtocolError("Response missing result/error")
        return response["result"]
