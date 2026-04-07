import os

from puremagic.scanners.helpers import Match

match_bytes = b"\x1a\x45\xdf\xa3"


def main(file_path: os.PathLike, head: bytes, foot: bytes) -> Match | None:
    if not head or len(head) < 8:
        return None
    if head[:4] != match_bytes:
        return None

    # Search for DocType string in the EBML header (first 64 bytes)
    search_area = head[:64]
    if b"webm" in search_area:
        return Match(".webm", "WebM Video", "video/webm")
    if b"matroska" in search_area:
        return Match(".mkv", "Matroska Video", "video/x-matroska")

    return None
