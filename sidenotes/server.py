import sys
from pathlib import Path

from lsprotocol import types
from pygls.lsp.server import LanguageServer

from sidenotes.notes import (
    NOTES_DIR,
    add_note,
    locate,
    new_note,
    parse,
    remove_note,
    sidecar_for,
)

MARKER = " 📝"
DELETE_COMMAND = "sidenotes.delete"

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
    """Shows the note for the hovered line with a link to edit it."""
    uri = params.text_document.uri
    path = sidecar_path(uri)
    body = notes_by_line(uri).get(params.position.line)
    if path is None or body is None:
        return None
    value = f"{body}\n\n---\n[Edit Note]({path.as_uri()})"
    return types.Hover(contents=types.MarkupContent(types.MarkupKind.Markdown, value))


@server.feature(types.TEXT_DOCUMENT_INLAY_HINT)
def inlay_hints(params: types.InlayHintParams) -> list[types.InlayHint]:
    """Marks the end of every line that has a note."""
    uri = params.text_document.uri
    lines = server.workspace.get_text_document(uri).lines
    hints = []
    for line in sorted(notes_by_line(uri)):
        if params.range.start.line <= line <= params.range.end.line:
            end = len(lines[line].rstrip("\r\n"))
            position = types.Position(line=line, character=end)
            hints.append(types.InlayHint(position=position, label=MARKER))
    return hints


@server.feature(types.INITIALIZED)
def watch_sidecars(params: types.InitializedParams) -> None:
    """Asks the editor to report sidecar files changing on disk."""
    watchers = [types.FileSystemWatcher(glob_pattern=f"**/{NOTES_DIR}/**/*.md")]
    registration = types.Registration(
        id="sidenotes-sidecars",
        method=types.WORKSPACE_DID_CHANGE_WATCHED_FILES,
        register_options=types.DidChangeWatchedFilesRegistrationOptions(watchers),
    )
    server.client_register_capability(types.RegistrationParams([registration]))


@server.feature(types.WORKSPACE_DID_CHANGE_WATCHED_FILES)
def refresh_markers(params: types.DidChangeWatchedFilesParams) -> None:
    """Redraws the markers after a sidecar is saved, created or deleted."""
    server.workspace_inlay_hint_refresh(None)


@server.feature(types.TEXT_DOCUMENT_CODE_ACTION)
def code_actions(params: types.CodeActionParams) -> list[types.CodeAction]:
    """Offers "Add sidenote" or "Delete sidenote" for the line under the cursor.

    A line that already has a note gets Delete, which removes the note from the
    sidecar on disk. Any other non-blank line gets Add, which creates the sidecar if
    it is missing and inserts a new anchor at the top. Nothing is offered on a blank
    line or a file outside the project.
    """
    uri = params.text_document.uri
    path = sidecar_path(uri)
    lines = server.workspace.get_text_document(uri).lines
    row = params.range.start.line
    if path is None or row >= len(lines):
        return []
    notes = read_notes(path)
    anchor = lines[row].strip()
    if anchor in notes:
        command = types.Command(
            title="Delete sidenote", command=DELETE_COMMAND, arguments=[uri, anchor]
        )
        return [types.CodeAction(title=command.title, command=command)]
    text = new_note(notes, lines[row])
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


@server.command(DELETE_COMMAND)
def delete_note(uri: str, anchor: str) -> None:
    """Removes a note from the sidecar on disk and redraws the markers.

    Args:
        uri: URI of the source file the note belongs to.
        anchor: Anchor of the note to remove.
    """
    path = sidecar_path(uri)
    if path is None or not path.is_file():
        return
    path.write_text(remove_note(path.read_text(), anchor))
    server.workspace_inlay_hint_refresh(None)


def add_command(root: str, source: str, row: str) -> None:
    """Adds a note from the command line for editor tasks bound to a key.

    Prints the sidecar location as path:line, pointing at the empty line to type on.
    Exits with status 1 if no note was added.

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
