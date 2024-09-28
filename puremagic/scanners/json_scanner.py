import os
import json

from puremagic.scanners.helpers import Match

match_bytes = b"{"


def main(file_path: os.PathLike | str, head: bytes, foot: bytes) -> Match | None:
    if not (head.strip().startswith(b"{") and foot.strip().endswith(b"}")):
        return None
    try:
        with open(file_path, "rb") as file:
            json.load(file)
    except (json.decoder.JSONDecodeError, OSError):
        return None
    return Match(
        extension=".json",
        name="JSON File",
        mime_type="application/json",
        confidence=1.0,
    )
