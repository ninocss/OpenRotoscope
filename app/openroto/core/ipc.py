from __future__ import annotations

import contextlib
import json
import socket
import threading
from collections.abc import Callable
from typing import Any


class BridgeConnectionError(RuntimeError):
    pass


class BridgeClient:
    """Authenticated JSON-lines connection to the script running in Resolve."""

    def __init__(
        self,
        host: str,
        port: int,
        token: str,
        on_message: Callable[[dict[str, Any]], None] | None = None,
        on_disconnect: Callable[[str], None] | None = None,
    ) -> None:
        if host not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("Bridge host must be loopback")
        self._address = (host, port)
        self._token = token
        self._on_message = on_message
        self._on_disconnect = on_disconnect
        self._socket: socket.socket | None = None
        self._reader: threading.Thread | None = None
        self._send_lock = threading.Lock()
        self._closed = threading.Event()

    @property
    def connected(self) -> bool:
        return self._socket is not None and not self._closed.is_set()

    def connect(self, timeout: float = 8.0) -> None:
        if self.connected:
            return
        try:
            connection = socket.create_connection(self._address, timeout=timeout)
            connection.settimeout(None)
        except OSError as error:
            raise BridgeConnectionError(
                "Could not connect to DaVinci Resolve. Start OpenRoto from "
                "Workspace > Scripts > OpenRoto."
            ) from error
        self._socket = connection
        self._closed.clear()
        self.send("hello", app="OpenRoto", protocol=1)
        self._reader = threading.Thread(
            target=self._read_loop, name="Resolve bridge", daemon=True
        )
        self._reader.start()

    def send(self, message_type: str, **payload: Any) -> None:
        if self._socket is None:
            raise BridgeConnectionError("Resolve bridge is not connected")
        message = {"type": message_type, "token": self._token, **payload}
        data = (json.dumps(message, separators=(",", ":")) + "\n").encode("utf-8")
        with self._send_lock:
            try:
                self._socket.sendall(data)
            except OSError as error:
                self.close()
                raise BridgeConnectionError("Connection to Resolve was lost") from error

    def close(self) -> None:
        self._closed.set()
        connection, self._socket = self._socket, None
        if connection is not None:
            with contextlib.suppress(OSError):
                connection.shutdown(socket.SHUT_RDWR)
            connection.close()
        self._on_message = None
        self._on_disconnect = None

    def _read_loop(self) -> None:
        assert self._socket is not None
        buffer = b""
        disconnect_reason = "DaVinci Resolve closed the OpenRoto connection."
        try:
            while not self._closed.is_set():
                chunk = self._socket.recv(65536)
                if not chunk:
                    break
                buffer += chunk
                if len(buffer) > 4 * 1024 * 1024:
                    disconnect_reason = "Resolve sent an invalid oversized message."
                    break
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    if not line:
                        continue
                    message = json.loads(line.decode("utf-8"))
                    if isinstance(message, dict) and self._on_message is not None:
                        self._on_message(message)
        except (OSError, ValueError, json.JSONDecodeError) as error:
            disconnect_reason = f"Connection to DaVinci Resolve was lost: {error}"
        finally:
            unexpected = not self._closed.is_set()
            on_disconnect = self._on_disconnect
            self.close()
            if unexpected and on_disconnect is not None:
                on_disconnect(disconnect_reason)
