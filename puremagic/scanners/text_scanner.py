from __future__ import annotations

import os
from typing import Optional

from puremagic.scanners.helpers import Match


def main(file_path: os.PathLike | str, _, __) -> Optional[Match]:
    with open(file_path, "rb") as file:
        head = file.read(1_000_000)
        if len(head) < 8:
            return Match("", "very short file", "application/octet-stream", confidence=0.5)
        try:
            head.decode("ascii")
        except UnicodeDecodeError:
            return Match("", "data", "application/octet-stream", confidence=0.5)
        crlf = head.count(b"\r\n")
        lf = head.count(b"\n")
        cr = head.count(b"\r")
        if crlf + lf + cr == 0:
            return Match(".txt", "ASCII text", "text/plain", confidence=0.9)

        if crlf > lf and crlf > cr:
            return Match(".txt", "ASCII text, with CRLF line terminators", "text/plain", confidence=0.9)
        if cr > lf and cr > crlf:
            return Match(".txt", "ASCII text, with CR line terminators", "text/plain", confidence=0.9)
        if lf > cr and lf > crlf:
            return Match(".txt", "ASCII text, with LF line terminators", "text/plain", confidence=0.9)
        return Match(".txt", "ASCII text", "text/plain", confidence=0.9)
