"""Reject requests sent before delayed lifecycle responses and diagnostics."""

from pathlib import Path
from queue import Empty, Queue
import sys
from threading import Thread

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from test_lsp import frame, messages


inbox = Queue()


def read_requests():
    for message in messages(sys.stdin.buffer):
        inbox.put(message)
    inbox.put(None)


def expect(method):
    message = inbox.get(timeout=5)
    assert message is not None and message.get("method") == method, message
    return message


def require_wait():
    try:
        message = inbox.get(timeout=0.05)
    except Empty:
        return
    raise AssertionError(f"client continued before a response: {message}")


def send(message):
    sys.stdout.buffer.write(frame(message))
    sys.stdout.buffer.flush()


Thread(target=read_requests, daemon=True).start()
initialize = expect("initialize")
require_wait()
send({"id": initialize["id"], "result": {"capabilities": {"hoverProvider": True}}})
expect("initialized")
opened = expect("textDocument/didOpen")
require_wait()
send({"method": "window/logMessage", "params": {"type": 3, "message": "checking"}})
send({"method": "textDocument/publishDiagnostics", "params": {
    "uri": opened["params"]["textDocument"]["uri"], "diagnostics": [],
}})
shutdown = expect("shutdown")
require_wait()
send({"id": shutdown["id"], "result": None})
expect("exit")
