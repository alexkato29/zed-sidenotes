from pathlib import Path

ANCHOR_PREFIX = "@@ "
NOTES_DIR = ".sidenotes"


def parse(text: str) -> dict[str, str]:
    """Parses sidecar text into notes.

    A line starting with "@@ " opens a note. The rest of that line is the anchor (the
    source line the note attaches to). Every following line up to the next anchor line
    is the note's markdown body.

    Args:
        text: Full contents of a sidecar file.

    Returns:
        Dict mapping each anchor to its body.
    """
    mappings: dict[str, str] = {}

    notes: list[str] = []
    for line in text.split("\n"):
        if line.startswith(ANCHOR_PREFIX):
            anchor = line[len(ANCHOR_PREFIX):].strip()
            # When a stray `@@` is present with no line we just pretend it does not
            # exist.
            if anchor:
                if notes:
                    mappings[notes[0]] = "\n".join(notes[1:]).strip("\n")
                notes = [anchor]
        elif notes:
            notes.append(line)

    if notes:
        mappings[notes[0]] = "\n".join(notes[1:]).strip("\n")

    return mappings


def locate(notes: dict[str, str], lines: list[str]) -> dict[int, str]:
    """Finds the source lines that carry a note.

    Args:
        notes: Dict mapping each anchor to its body, as returned by parse.
        lines: Source file lines in order. Each may end with a newline.

    Returns:
        Dict mapping 0-based line numbers to note bodies.
    """
    mapping: dict[int, str] = {}
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if stripped in notes:
            mapping[idx] = notes[stripped]
    return mapping


def new_note(notes: dict[str, str], line: str) -> str | None:
    """Builds the sidecar text that starts a note for a source line.

    The server inserts the returned text at the very top of the sidecar above any notes
    already there.

    Args:
        notes: Dict mapping each anchor to its body, as returned by parse.
        line: The source line under the cursor. May be indented and end with a newline.

    Returns:
        Text to insert, or None if no note should be offered for this line.
    """
    line = line.strip()
    if not line or line in notes:
        return None
    else:
        return ANCHOR_PREFIX + line + "\n\n"


def remove_note(text: str, anchor: str) -> str:
    """Removes a note from sidecar text.

    Args:
        text: Full contents of a sidecar file.
        anchor: Anchor of the note to remove, already stripped.

    Returns:
        The sidecar text without that note's anchor line and body.
    """
    skipping = False
    kept = []
    for line in text.split("\n"):
        if line.startswith(ANCHOR_PREFIX):
            curr_anchor = line[len(ANCHOR_PREFIX):].strip()
            if curr_anchor:
                skipping = curr_anchor == anchor
        if not skipping:
            kept.append(line)

    return "\n".join(kept)


def sidecar_for(root: Path, source: Path) -> Path | None:
    """Locates where notes for a source file live.

    Args:
        root: Project root directory.
        source: Absolute path to the source file.

    Returns:
        Path to the sidecar file, or None if the source file is outside the project.
    """
    if not source.is_relative_to(root):
        return None
    return root / NOTES_DIR / f"{source.relative_to(root)}.md"


def add_note(root: Path, source: Path, row: int) -> Path | None:
    """Starts a note in the sidecar on disk for one line of a source file.

    Args:
        root: Project root directory.
        source: Absolute path to the source file.
        row: 0-based line number in the source file.

    Returns:
        Path to the sidecar file, or None if no note was added.
    """
    path = sidecar_for(root, source)
    lines = source.read_text().splitlines()
    if path is None or row >= len(lines):
        return None
    existing = path.read_text() if path.is_file() else ""
    text = new_note(parse(existing), lines[row])
    if text is None:
        return None
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text + existing)
    return path
