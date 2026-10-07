from pathlib import Path

from lsprotocol import types
from pygls.lsp.server import LanguageServer

from sidenotes.notes import locate, parse

NOTES_DIR = ".sidenotes"

server = LanguageServer("sidenotes", "0.1.0")


def sidecar_path(uri: str) -> Path | None:
    """Locates where notes for a source file live.

    Args:
        uri: URI containing the absolute path to the source file.

    Returns:
        Path to the sidecar file, or None if the source file is outside the project.
    """
    root = server.workspace.root_path
    source = Path(server.workspace.get_text_document(uri).path)
    if root is None or not source.is_relative_to(root):
        return None
    return Path(root, NOTES_DIR, f"{source.relative_to(root)}.md")


def notes_by_line(uri: str) -> dict[int, str]:
    path = sidecar_path(uri)
    if path is None or not path.is_file():
        return {}
    lines = server.workspace.get_text_document(uri).lines
    return locate(parse(path.read_text()), lines)


@server.feature(types.TEXT_DOCUMENT_HOVER)
def hover(params: types.HoverParams) -> types.Hover | None:
    uri = params.text_document.uri
    path = sidecar_path(uri)
    body = notes_by_line(uri).get(params.position.line)
    if path is None or body is None:
        return None
    value = f"{body}\n\n---\n[edit note]({path.as_uri()})"
    return types.Hover(contents=types.MarkupContent(types.MarkupKind.Markdown, value))


def main() -> None:
    server.start_io()


if __name__ == "__main__":
    main()
