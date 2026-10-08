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


def markers(client, source, first_line, last_line):
    client.open(source)
    hints = client.request(
        "textDocument/inlayHint",
        {
            "textDocument": {"uri": source.as_uri()},
            "range": {
                "start": {"line": first_line, "character": 0},
                "end": {"line": last_line, "character": 0},
            },
        },
    )
    return [
        (hint["position"]["line"], hint["position"]["character"], hint["label"])
        for hint in hints
    ]


def test_marker_at_end_of_every_annotated_line(client, tmp_path):
    source = write(tmp_path / "demo.py", "x = 1\ny = 2\n    x = 1\n")
    write(tmp_path / ".sidenotes" / "demo.py.md", "@@ x = 1\nwhy x\n")

    assert markers(client, source, 0, 3) == [(0, 5, " 📝"), (2, 9, " 📝")]


def test_markers_limited_to_requested_range(client, tmp_path):
    source = write(tmp_path / "demo.py", "x = 1\ny = 2\n    x = 1\n")
    write(tmp_path / ".sidenotes" / "demo.py.md", "@@ x = 1\nwhy x\n")

    assert markers(client, source, 1, 3) == [(2, 9, " 📝")]


def test_no_markers_without_sidecar(client, tmp_path):
    source = write(tmp_path / "demo.py", "x = 1\n")

    assert markers(client, source, 0, 1) == []


def actions(client, source, line):
    client.open(source)
    position = {"line": line, "character": 0}
    return client.request(
        "textDocument/codeAction",
        {
            "textDocument": {"uri": source.as_uri()},
            "range": {"start": position, "end": position},
            "context": {"diagnostics": []},
        },
    )


def test_add_sidenote_creates_sidecar_and_inserts_anchor_at_top(client, tmp_path):
    source = write(tmp_path / "src" / "demo.py", "x = 1\n    y = 2\n")
    sidecar = (tmp_path / ".sidenotes" / "src" / "demo.py.md").as_uri()

    [action] = actions(client, source, line=1)
    create, insert = action["edit"]["documentChanges"]

    assert action["title"] == "Add sidenote"
    assert create == {
        "kind": "create",
        "uri": sidecar,
        "options": {"ignoreIfExists": True},
    }
    assert insert["textDocument"]["uri"] == sidecar
    top = {"line": 0, "character": 0}
    assert insert["edits"] == [
        {"range": {"start": top, "end": top}, "newText": "@@ y = 2\n\n"}
    ]


def test_add_sidenote_not_offered_on_annotated_line(client, tmp_path):
    source = write(tmp_path / "demo.py", "x = 1\n")
    write(tmp_path / ".sidenotes" / "demo.py.md", "@@ x = 1\nwhy x\n")

    assert actions(client, source, line=0) == []


def test_add_sidenote_not_offered_on_blank_line(client, tmp_path):
    source = write(tmp_path / "demo.py", "x = 1\n\n")

    assert actions(client, source, line=1) == []


def test_add_sidenote_not_offered_outside_project(client, tmp_path_factory):
    source = write(tmp_path_factory.mktemp("elsewhere") / "demo.py", "x = 1\n")

    assert actions(client, source, line=0) == []
