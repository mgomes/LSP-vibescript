"""Exercise the configured command against the Rust language server."""

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import unittest


ROOT = Path(__file__).resolve().parent.parent
SETTINGS = json.loads(re.sub(r"(?m)^\s*//.*$", "", (ROOT / "LSP-vibescript.sublime-settings").read_text()))
BINARY = os.environ.get("VIBES_BINARY") or shutil.which(SETTINGS["command"][0])


def frame(message):
    payload = json.dumps({"jsonrpc": "2.0", **message}).encode()
    return f"Content-Length: {len(payload)}\r\n\r\n".encode() + payload


def messages(payload):
    while payload:
        header, body = payload.split(b"\r\n\r\n", 1)
        length = int(re.search(rb"Content-Length:\s*(\d+)", header, re.I)[1])
        yield json.loads(body[:length])
        payload = body[length:]


@unittest.skipUnless(BINARY, "set VIBES_BINARY or put Rust vibes on PATH")
class LanguageServerTests(unittest.TestCase):
    def diagnostics(self, source):
        request = b"".join(frame(message) for message in [
            {"id": 1, "method": "initialize", "params": {"processId": None, "rootUri": None, "capabilities": {}}},
            {"method": "initialized", "params": {}},
            {"method": "textDocument/didOpen", "params": {"textDocument": {
                "uri": "file:///editor-tooling-test.vibe", "languageId": "vibescript", "version": 1, "text": source,
            }}},
            {"id": 2, "method": "shutdown", "params": None},
            {"method": "exit"},
        ])
        result = subprocess.run([BINARY, *SETTINGS["command"][1:]], input=request, capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertEqual(result.stderr, b"")
        replies = list(messages(result.stdout))
        initialize = next(reply for reply in replies if reply.get("id") == 1)
        self.assertTrue(initialize["result"]["capabilities"]["hoverProvider"])
        published = [reply["params"]["diagnostics"] for reply in replies
                     if reply.get("method") == "textDocument/publishDiagnostics"]
        self.assertTrue(published, "server did not publish diagnostics")
        return published[-1]

    def test_static_types_and_floor_division(self):
        source = '# vibe: 0.80\ntype Pair = [int, string]\nvalue: int = 7 // 2\nvalue //= 2\n'
        self.assertEqual(self.diagnostics(source), [])

    def test_type_mismatch_has_rust_diagnostic(self):
        diagnostics = self.diagnostics('value: int = "wrong"\n')
        self.assertTrue(any(item.get("code") == "V0101" for item in diagnostics), diagnostics)


if __name__ == "__main__":
    unittest.main()
