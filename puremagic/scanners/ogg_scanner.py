import os

from puremagic.scanners.helpers import Match

match_bytes = b"OggS"

# Ogg codec identification signatures found at the start of the first page payload.
# Each entry: (codec_id_bytes, extension, name, mime_type)
_OGG_CODEC_MAP = [
    (b"\x01vorbis", ".ogg", "Ogg Vorbis Audio", "audio/ogg"),
    (b"OpusHead", ".opus", "Ogg Opus Audio", "audio/ogg"),
    (b"\x80theora", ".ogv", "Ogg Theora Video", "video/ogg"),
    (b"\x7fFLAC", ".oga", "Ogg FLAC Audio", "audio/ogg"),
    (b"Speex   ", ".spx", "Ogg Speex Audio", "audio/ogg"),
    (b"fishead\x00", ".ogv", "Ogg Annodex", "video/ogg"),
    (b"\x01video", ".ogm", "OGM Video", "video/x-ogm+ogg"),
]


def main(file_path: os.PathLike, head: bytes, foot: bytes) -> Match | None:
    if not head or len(head) < 28:
        return None

    # Verify OggS capture pattern, version 0, and beginning-of-stream flag
    if head[:4] != match_bytes or head[4] != 0 or not (head[5] & 0x02):
        return None

    seg_count = head[26]
    payload_start = 27 + seg_count

    if payload_start >= len(head):
        return None

    payload = head[payload_start:]
    for codec_id, ext, name, mime in _OGG_CODEC_MAP:
        if payload.startswith(codec_id):
            return Match(ext, name, mime, confidence=0.9)

    return None
