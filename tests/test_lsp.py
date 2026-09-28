"""Exercise the configured command against the Rust language server."""

import json
import os
from pathlib import Path
from queue import Empty, Queue
import re
import shutil
import subprocess
import sys
from threading import Thread
from time import monotonic
import unittest


ROOT = Path(__file__).resolve().parent.parent
SETTINGS = json.loads(re.sub(r"(?m)^\s*//.*$", "", (ROOT / "LSP-vibescript.sublime-settings").read_text()))
BINARY = os.environ.get("VIBES_BINARY") or shutil.which(SETTINGS["command"][0])


def frame(message):
    payload = json.dumps({"jsonrpc": "2.0", **message}).encode()
    return f"Content-Length: {len(payload)}\r\n\r\n".encode() + payload


def messages(stream):
    while True:
        header = stream.readline()
        if not header:
            return
        while not header.endswith(b"\r\n\r\n"):
            line = stream.readline()
            if not line:
                raise EOFError("server closed stdout during a message header")
            header += line
        length = int(re.search(rb"Content-Length:\s*(\d+)", header, re.I)[1])
        body = stream.read(length)
        if len(body) != length:
            raise EOFError("server closed stdout during a message body")
        yield json.loads(body)


class LspTestCase(unittest.TestCase):
    def diagnostics(self, source):
        with subprocess.Popen(self.command, stdin=subprocess.PIPE,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE) as server:
            inbox = Queue()
            stderr = []
            deadline = monotonic() + 15

            def read_stdout():
                try:
                    for message in messages(server.stdout):
                        inbox.put(message)
                except Exception as error:
                    inbox.put(error)
                finally:
                    inbox.put(None)

            readers = [Thread(target=read_stdout, daemon=True),
                       Thread(target=lambda: stderr.append(server.stderr.read()), daemon=True)]
            for reader in readers:
                reader.start()

            def send(message):
                server.stdin.write(frame(message))
                server.stdin.flush()

            def receive(predicate):
                while True:
                    try:
                        message = inbox.get(timeout=max(0, deadline - monotonic()))
                    except Empty:
                        raise TimeoutError("timed out waiting for a language server response") from None
                    if message is None:
                        raise EOFError("server closed stdout before the expected response")
                    if isinstance(message, Exception):
                        raise message
                    if predicate(message):
                        return message

            try:
                send({"id": 1, "method": "initialize", "params": {
                    "processId": None, "rootUri": None, "capabilities": {},
                }})
                initialize = receive(lambda message: message.get("id") == 1)
                self.assertTrue(initialize["result"]["capabilities"]["hoverProvider"])
                send({"method": "initialized", "params": {}})
                uri = "file:///editor-tooling-test.vibe"
                send({"method": "textDocument/didOpen", "params": {"textDocument": {
                    "uri": uri, "languageId": "vibescript", "version": 1, "text": source,
                }}})
                published = receive(lambda message: message.get("method") == "textDocument/publishDiagnostics"
                                    and message.get("params", {}).get("uri") == uri)
                send({"id": 2, "method": "shutdown", "params": None})
                shutdown = receive(lambda message: message.get("id") == 2)
                self.assertNotIn("error", shutdown)
                send({"method": "exit"})
                server.stdin.close()
                server.wait(timeout=max(0, deadline - monotonic()))
            finally:
                if server.poll() is None:
                    server.kill()
                server.wait(timeout=5)
                for reader in readers:
                    reader.join(timeout=5)
            self.assertEqual(server.returncode, 0, b"".join(stderr).decode())
            self.assertEqual(b"".join(stderr), b"")
            return published["params"]["diagnostics"]


@unittest.skipUnless(BINARY, "set VIBES_BINARY or put Rust vibes on PATH")
class LanguageServerTests(LspTestCase):
    command = [BINARY, *SETTINGS["command"][1:]]

    def test_static_types_and_floor_division(self):
        source = '# vibe: 0.80\ntype Pair = [int, string]\nvalue: int = 7 // 2\nvalue //= 2\n'
        self.assertEqual(self.diagnostics(source), [])

    def test_type_mismatch_has_rust_diagnostic(self):
        diagnostics = self.diagnostics('value: int = "wrong"\n')
        self.assertTrue(any(item.get("code") == "V0101" for item in diagnostics), diagnostics)


class LifecycleTests(LspTestCase):
    command = [sys.executable, str(ROOT / "tests/fixtures/lifecycle_server.py")]

    def test_waits_for_delayed_responses_and_diagnostics(self):
        self.assertEqual(self.diagnostics("value: int = 1\n"), [])


if __name__ == "__main__":
    unittest.main()
