import ast
import os

from puremagic.scanners.helpers import Match

# AST node types that are strong indicators of real Python code
_PYTHON_NODE_TYPES = (
    ast.Import,
    ast.ImportFrom,
    ast.FunctionDef,
    ast.AsyncFunctionDef,
    ast.ClassDef,
    ast.For,
    ast.AsyncFor,
    ast.While,
    ast.With,
    ast.AsyncWith,
    ast.Try,
    ast.Raise,
    ast.Assert,
)


def _has_python_constructs(tree: ast.Module, threshold: int = 4) -> bool:
    """Walk the AST and check for node types that indicate real Python code.

    Simple expressions (tuples, names, constants) can appear in CSV, config files,
    and other non-Python text that happens to parse. Real Python code will contain
    imports, function/class definitions, control flow, etc.
    """
    count = 0
    for node in ast.walk(tree):
        if isinstance(node, _PYTHON_NODE_TYPES):
            count += 1
            if count >= threshold:
                return True
    return False


def main(file_path: os.PathLike | str, _, __) -> Match | None:
    file_size = os.path.getsize(file_path)
    if file_size > 1_000_000:
        return None
    if not str(file_path).endswith(".py") and file_size < 100:
        return None

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()

        tree = ast.parse(content)

        if not str(file_path).endswith(".py"):
            if not _has_python_constructs(tree):
                return None

    except (SyntaxError, UnicodeDecodeError, PermissionError, OSError):
        return None

    return Match(
        extension=".py",
        name="Python Script",
        mime_type="text/x-python",
        confidence=1.0,
    )
