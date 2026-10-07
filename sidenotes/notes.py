ANCHOR_PREFIX = "@@ "


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
