import sys
from pathlib import Path

from lsprotocol import types
from pygls.lsp.server import LanguageServer

from sidenotes.notes import add_note, locate, new_note, parse, sidecar_for

MARKER = " 📝"

server = LanguageServer("sidenotes", "0.1.0")


def sidecar_path(uri: str) -> Path | None:
    """Locates where notes for a source file live.

    Args:
        uri: URI containing the absolute path to the source file.

    Returns:
        Path to the sidecar file, or None if the source file is outside the project.
    """
    root = server.workspace.root_path
    if root is None:
        return None
    return sidecar_for(Path(root), Path(server.workspace.get_text_document(uri).path))


def read_notes(path: Path | None) -> dict[str, str]:
    if path is None or not path.is_file():
        return {}
    return parse(path.read_text())


def notes_by_line(uri: str) -> dict[int, str]:
    lines = server.workspace.get_text_document(uri).lines
    return locate(read_notes(sidecar_path(uri)), lines)


@server.feature(types.TEXT_DOCUMENT_HOVER)
def hover(params: types.HoverParams) -> types.Hover | None:
    uri = params.text_document.uri
    path = sidecar_path(uri)
    body = notes_by_line(uri).get(params.position.line)
    if path is None or body is None:
        return None
    value = f"{body}\n\n---\n[edit note]({path.as_uri()})"
    return types.Hover(contents=types.MarkupContent(types.MarkupKind.Markdown, value))


@server.feature(types.TEXT_DOCUMENT_INLAY_HINT)
def inlay_hints(params: types.InlayHintParams) -> list[types.InlayHint]:
    uri = params.text_document.uri
    lines = server.workspace.get_text_document(uri).lines
    hints = []
    for line in sorted(notes_by_line(uri)):
        if params.range.start.line <= line <= params.range.end.line:
            end = len(lines[line].rstrip("\r\n"))
            position = types.Position(line=line, character=end)
            hints.append(types.InlayHint(position=position, label=MARKER))
    return hints


@server.feature(types.TEXT_DOCUMENT_CODE_ACTION)
def code_actions(params: types.CodeActionParams) -> list[types.CodeAction]:
    uri = params.text_document.uri
    path = sidecar_path(uri)
    lines = server.workspace.get_text_document(uri).lines
    row = params.range.start.line
    if path is None or row >= len(lines):
        return []
    text = new_note(read_notes(path), lines[row])
    if text is None:
        return []
    # Insert at the top so the edit never depends on the sidecar's unsaved length.
    top = types.Position(line=0, character=0)
    sidecar = types.OptionalVersionedTextDocumentIdentifier(uri=path.as_uri())
    insert = types.TextEdit(range=types.Range(start=top, end=top), new_text=text)
    create = types.CreateFile(
        uri=path.as_uri(), options=types.CreateFileOptions(ignore_if_exists=True)
    )
    edit = types.WorkspaceEdit(
        document_changes=[
            create,
            types.TextDocumentEdit(text_document=sidecar, edits=[insert]),
        ]
    )
    return [types.CodeAction(title="Add sidenote", edit=edit)]


def add_command(root: str, source: str, row: str) -> None:
    """Adds a note from the command line for editor tasks bound to a key.

    Prints the sidecar location as path:line, pointing at the empty line to type on.

    Args:
        root: Project root directory.
        source: Absolute path to the source file.
        row: 1-based line number as the editor report it.
    """
    path = add_note(Path(root), Path(source), int(row) - 1)
    if path is None:
        sys.exit(1)
    print(f"{path}:2")


def main() -> None:
    if sys.argv[1:2] == ["add"]:
        add_command(*sys.argv[2:])
    else:
        server.start_io()


if __name__ == "__main__":
    main()
