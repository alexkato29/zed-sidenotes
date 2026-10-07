import json
import subprocess
import sys

import pytest


class Client:
    """Minimal LSP client speaking JSON-RPC to a server subprocess."""

    def __init__(self, root):
        self.proc = subprocess.Popen(
            [sys.executable, "-m", "sidenotes.server"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
        )
        self.last_id = 0
        self.request(
            "initialize",
            {"processId": None, "rootUri": root.as_uri(), "capabilities": {}},
        )
        self.notify("initialized", {})

    def notify(self, method, params, **extra):
        body = json.dumps(
            {"jsonrpc": "2.0", "method": method, "params": params, **extra}
        ).encode()
        self.proc.stdin.write(b"Content-Length: %d\r\n\r\n%s" % (len(body), body))
        self.proc.stdin.flush()

    def request(self, method, params):
        self.last_id += 1
        self.notify(method, params, id=self.last_id)
        while True:
            length = 0
            while line := self.proc.stdout.readline().strip():
                if line.lower().startswith(b"content-length:"):
                    length = int(line.split(b":")[1])
            message = json.loads(self.proc.stdout.read(length))
            if message.get("id") == self.last_id:
                return message["result"]

    def open(self, path):
        self.notify(
            "textDocument/didOpen",
            {
                "textDocument": {
                    "uri": path.as_uri(),
                    "languageId": "python",
                    "version": 1,
                    "text": path.read_text(),
                }
            },
        )


@pytest.fixture
def client(tmp_path):
    client = Client(tmp_path)
    yield client
    client.proc.kill()


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def hover(client, source, line):
    client.open(source)
    return client.request(
        "textDocument/hover",
        {
            "textDocument": {"uri": source.as_uri()},
            "position": {"line": line, "character": 0},
        },
    )


def test_hover_shows_note_with_link_to_sidecar(client, tmp_path):
    source = write(tmp_path / "src" / "demo.py", "x = 1\ny = 2\n")
    sidecar = write(tmp_path / ".sidenotes" / "src" / "demo.py.md", "@@ y = 2\nwhy y\n")

    value = hover(client, source, line=1)["contents"]["value"]

    assert value.startswith("why y")
    assert f"[edit note]({sidecar.as_uri()})" in value


def test_hover_on_line_without_note(client, tmp_path):
    source = write(tmp_path / "demo.py", "x = 1\ny = 2\n")
    write(tmp_path / ".sidenotes" / "demo.py.md", "@@ y = 2\nwhy y\n")

    assert hover(client, source, line=0) is None


def test_hover_without_sidecar(client, tmp_path):
    source = write(tmp_path / "demo.py", "x = 1\n")

    assert hover(client, source, line=0) is None


def test_hover_on_file_outside_project(client, tmp_path_factory):
    source = write(tmp_path_factory.mktemp("elsewhere") / "demo.py", "x = 1\n")

    assert hover(client, source, line=0) is None
