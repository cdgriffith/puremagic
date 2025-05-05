import ast
import os

from puremagic.scanners.helpers import Match


def main(file_path: os.PathLike | str, *_, **__) -> Match | None:
    file_size = os.path.getsize(file_path)
    if file_size > 1_000_000:
        return None
    if not str(file_path).endswith(".py") and file_size < 100:
        return None

    try:
        with open(file_path, "r") as file:
            content = file.read()
        ast.parse(content)
    except Exception:
        return None
    return Match(
        extension=".py",
        name="Python Script",
        mime_type="text/x-python",
        confidence=1.0,
    )
