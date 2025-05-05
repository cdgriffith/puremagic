from puremagic.scanners.helpers import Match

match_bytes = b"%PDF"


def main(_, head: bytes, foot: bytes) -> Match | None:
    if b"%PDF-" in head and b"startxref" in foot:
        return Match(".pdf", "PDF document", "application/pdf")
    return None
