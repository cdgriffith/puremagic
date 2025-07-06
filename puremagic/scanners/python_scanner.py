import ast
import os
import re

from puremagic.scanners.helpers import Match

python_common_keywords = [
    re.compile("\bdef\b"),
    re.compile("\bclass\b"),
    re.compile("\bimport\b"),
    re.compile("\belif\b"),
    re.compile("\bwhile\b"),
    re.compile("\bexcept\b"),
    re.compile("\bfinally\b"),
    re.compile("\breturn\b"),
    re.compile("\byield\b"),
    re.compile("\blambda\b"),
    re.compile("\bTrue\b"),
    re.compile("\bFalse\b"),
    re.compile("\bNone\b"),
    re.compile("\b__version__\b"),
    re.compile("__main__"),
]

python_patterns = [
    re.compile(r"\bdef\s+\w+\s*\("),  # Function definitions
    re.compile(r"\bclass\s+\w+\s*[\(:]"),  # Class definitions
    re.compile(r"\bimport\s+\w+"),  # Import statements
    re.compile(r"\bfrom\s+\w+\s+import"),  # From-import statements
    re.compile(r"\bif\s+.*:"),  # If statements
    re.compile(r"\bfor\s+\w+\s+in\s+.*:"),  # For loops
    re.compile(r"\bwhile\s+.*:"),  # While loops
    re.compile(r"\btry\s*:"),  # Try blocks
    re.compile(r"\.append\("),  # Method calls
    re.compile(r"\.join\("),  # String operations
    re.compile(r"print\s*\("),  # Print statements
]


def main(file_path: os.PathLike | str, _, __) -> Match | None:
    file_size = os.path.getsize(file_path)
    if file_size > 1_000_000:
        return None
    if not str(file_path).endswith(".py") and file_size < 100:
        return None

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()

        # Parse to ensure it's valid Python syntax
        ast.parse(content)

        if not str(file_path).endswith(".py"):
            if not is_substantial_python_code(content):
                return None

    except (SyntaxError, UnicodeDecodeError, PermissionError, OSError):
        return None

    return Match(
        extension=".py",
        name="Python Script",
        mime_type="text/x-python",
        confidence=1.0,
    )


def is_substantial_python_code(content: str) -> bool:
    """
    Check if the content contains substantial Python code indicators.
    Returns True if the content appears to be meaningful Python code.
    """
    # Remove comments and strings to focus on actual code
    content_lines = content.splitlines()
    code_lines = []

    for line in content_lines:
        # Remove comments (basic approach - doesn't handle strings containing #)
        line = line.split("#")[0].strip()
        if line:  # Non-empty after removing comments
            code_lines.append(line)

    # If too few substantial lines, it's probably not real code
    if len(code_lines) < 2:
        return False

    code_text = " ".join(code_lines)

    # Check for Python keywords that indicate actual code

    # Count how many keywords are present
    keyword_count = 0
    for keyword in python_common_keywords:
        if keyword.search(code_text):
            keyword_count += 1

    # Require at least 2 keywords for substantial code
    if keyword_count < 2:
        return False

    # Check for common Python patterns
    for pattern in python_patterns:
        if pattern.search(code_text):
            return True
    return False
