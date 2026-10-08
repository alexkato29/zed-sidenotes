import pytest

from sidenotes.notes import add_note, locate, new_note, parse

PARSE_CASES = {
    "empty sidecar": ("", {}),
    "single note": ("@@ a\nbody", {"a": "body"}),
    "two notes": ("@@ a\nx\n@@ b\ny", {"a": "x", "b": "y"}),
    "text before the first anchor is ignored": ("intro\n@@ a\nx", {"a": "x"}),
    "note with no body": ("@@ a\n@@ b\ny", {"a": "", "b": "y"}),
    "anchor is stripped": ("@@   x = 1  \nbody", {"x = 1": "body"}),
    "blank lines trimmed from both ends of a body": (
        "@@ a\n\n\nbody\n\n@@ b\ny",
        {"a": "body", "b": "y"},
    ),
    "last note in the file is trimmed too": ("@@ a\n\nbody\n\n", {"a": "body"}),
    "inner blank lines kept": (
        "@@ a\npara one\n\npara two",
        {"a": "para one\n\npara two"},
    ),
    "first line keeps its indentation": (
        "@@ a\n\n    x = 1\n    y = 2\n@@ b\ny",
        {"a": "    x = 1\n    y = 2", "b": "y"},
    ),
    "stray empty anchor is ignored": ("@@ a\nx\n@@ \ny", {"a": "x\ny"}),
    "same anchor twice, last wins": ("@@ a\nfirst\n@@ a\nsecond", {"a": "second"}),
    "body line starting with the prefix opens a note": (
        "@@ a\nx\n@@ -1,3 +1,4 @@\ny",
        {"a": "x", "-1,3 +1,4 @@": "y"},
    ),
}


@pytest.mark.parametrize(
    ("text", "expected"), PARSE_CASES.values(), ids=PARSE_CASES.keys()
)
def test_parse(text, expected):
    assert parse(text) == expected


LOCATE_CASES = {
    "exact line": ({"x = 1": "n"}, ["x = 1\n"], {0: "n"}),
    "indentation and newline ignored": ({"x = 1": "n"}, ["    x = 1\n"], {0: "n"}),
    "last line without a newline": ({"x = 1": "n"}, ["y = 2\n", "x = 1"], {1: "n"}),
    "every identical line gets the note": (
        {"return c": "n"},
        ["return c\n", "y = 2\n", "    return c\n"],
        {0: "n", 2: "n"},
    ),
    "two notes": (
        {"x = 1": "first", "y = 2": "second"},
        ["x = 1\n", "z = 3\n", "y = 2\n"],
        {0: "first", 2: "second"},
    ),
    "no matching line": ({"x = 1": "n"}, ["y = 2\n"], {}),
    "a longer line containing the anchor does not match": (
        {"x = 1": "n"},
        ["x = 10\n"],
        {},
    ),
    "blank lines never match": ({"x = 1": "n"}, ["\n", "   \n"], {}),
    "no notes": ({}, ["x = 1\n"], {}),
}


@pytest.mark.parametrize(
    ("notes", "lines", "expected"), LOCATE_CASES.values(), ids=LOCATE_CASES.keys()
)
def test_locate(notes, lines, expected):
    assert locate(notes, lines) == expected


EXISTING = "@@ y = 2\nwhy y\n"


def test_new_note_parses_and_matches_its_line():
    line = "    x = 1\n"
    sidecar = new_note(parse(EXISTING), line) + EXISTING

    assert parse(sidecar) == {"x = 1": "", "y = 2": "why y"}
    assert locate(parse(sidecar), [line]) == {0: ""}


def test_new_note_leaves_an_empty_line_for_the_body():
    sidecar = new_note(parse(EXISTING), "x = 1\n") + EXISTING

    assert sidecar.split("\n")[:3] == ["@@ x = 1", "", "@@ y = 2"]


@pytest.mark.parametrize("line", ["", "\n", "   \n"])
def test_new_note_not_offered_on_blank_line(line):
    assert new_note({}, line) is None


def test_new_note_not_offered_on_annotated_line():
    assert new_note({"x = 1": "why x"}, "    x = 1\n") is None


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def test_add_note_creates_sidecar(tmp_path):
    source = write(tmp_path / "src" / "demo.py", "x = 1\n    y = 2\n")

    sidecar = add_note(tmp_path, source, row=1)

    assert sidecar == tmp_path / ".sidenotes" / "src" / "demo.py.md"
    assert sidecar.read_text() == "@@ y = 2\n\n"


def test_add_note_goes_above_existing_notes(tmp_path):
    source = write(tmp_path / "demo.py", "x = 1\ny = 2\n")
    sidecar = write(tmp_path / ".sidenotes" / "demo.py.md", EXISTING)

    assert add_note(tmp_path, source, row=0) == sidecar
    assert sidecar.read_text() == "@@ x = 1\n\n" + EXISTING


@pytest.mark.parametrize("row", [1, 2, 3], ids=["annotated", "blank", "past the end"])
def test_add_note_declined_leaves_sidecar_untouched(tmp_path, row):
    source = write(tmp_path / "demo.py", "x = 1\ny = 2\n\n")
    sidecar = write(tmp_path / ".sidenotes" / "demo.py.md", EXISTING)

    assert add_note(tmp_path, source, row) is None
    assert sidecar.read_text() == EXISTING


def test_add_note_declined_outside_project(tmp_path):
    source = write(tmp_path / "elsewhere" / "demo.py", "x = 1\n")
    root = tmp_path / "project"
    root.mkdir()

    assert add_note(root, source, row=0) is None
    assert not (root / ".sidenotes").exists()
