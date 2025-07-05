"""
Scanner for audio file formats, replacing the functionality of the legacy sndhdr module.

Other formats are already handled via standard magic_data logic.
"""

import struct
from typing import Optional

from puremagic.scanners.helpers import Match

fssd_match_bytes = b"FSSD"
hcom_match_bytes = b"HCOM"
sndr_match_bytes = b"\0\0"


def get_short_le(b: bytes) -> int:
    """Get a 2-byte little-endian integer from bytes."""
    return struct.unpack("<H", b)[0]


def test_hcom(head: bytes) -> Optional[Match]:
    """Test for HCOM format."""
    if head[65:69] == b"FSSD" and head[128:132] == b"HCOM":
        return Match(
            extension=".hcom",
            name="Macintosh HCOM Audio File",
            mime_type="audio/x-hcom",
            confidence=1.0,
        )
    return None

def main(_, head: bytes, __) -> Optional[Match]:
    try:
        rate = get_short_le(head[2:4])
        if 4000 <= rate <= 48000:
            return Match(
                extension=".sndr",
                name=f"Macintosh SNDR Resource - {rate} rate",
                mime_type="audio/x-sndr",
                confidence=0.1,  # Lower confidence due to simple format
            )
    except (IndexError, struct.error):
        pass
    return test_hcom(head)
