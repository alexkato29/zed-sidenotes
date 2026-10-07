import pytest

from sidenotes.notes import locate, parse

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
