from __future__ import annotations

import os
from typing import Optional

from puremagic.scanners.helpers import Match

match_bytes = b"%PDF"


def main(_, head: bytes, foot: bytes) -> Optional[Match]:
    if b"%PDF-" in head and b"startxref" in foot:
        return Match(".pdf", "PDF document", "application/pdf")
    return None
