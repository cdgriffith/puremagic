import os
import struct

from puremagic.scanners.helpers import Match

match_bytes = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
match_bytes_short = b"\xd0\xcf\x11\xe0"

# Stream names that identify specific CFBF-based formats, checked in priority order.
# Each entry: (stream_name, extension, name, mime_type)
# Using startswith for prefix matching where noted.
_STREAM_MATCHES = [
    ("__nameid_version1.0", ".msg", "Outlook Message", "application/vnd.ms-outlook"),
    ("PowerPoint Document", ".ppt", "PowerPoint Presentation", "application/vnd.ms-powerpoint"),
    ("Current User", ".ppt", "PowerPoint Presentation", "application/vnd.ms-powerpoint"),
    ("Workbook", ".xls", "Excel Spreadsheet", "application/vnd.ms-excel"),
    ("Book", ".xls", "Excel Spreadsheet", "application/vnd.ms-excel"),
    ("WordDocument", ".doc", "Word Document", "application/msword"),
    ("VisioDocument", ".vsd", "Visio Drawing", "application/x-visio"),
    ("Quill", ".pub", "Publisher Document", "application/x-mspublisher"),
]

_PREFIX_MATCHES = [
    ("__substg1.0_", ".msg", "Outlook Message", "application/vnd.ms-outlook"),
]


def _extract_stream_names(dir_data: bytes) -> set[str]:
    """Parse CFBF directory entries and return the set of stream/storage names."""
    names: set[str] = set()
    for i in range(0, len(dir_data), 128):
        entry = dir_data[i : i + 128]
        if len(entry) < 128:
            break
        name_size = struct.unpack_from("<H", entry, 64)[0]
        if name_size < 2 or name_size > 64:
            continue
        obj_type = entry[66]
        # obj_type: 0=unknown, 1=storage, 2=stream, 5=root
        if obj_type not in (1, 2, 5):
            continue
        name = entry[: name_size - 2].decode("utf-16-le", errors="ignore")
        if name:
            names.add(name)
    return names


def _identify_format(stream_names: set[str]) -> Match | None:
    """Match stream names against known CFBF format signatures."""
    # Check prefix matches first (e.g. __substg1.0_ for MSG)
    for name in stream_names:
        for prefix, ext, fmt_name, mime in _PREFIX_MATCHES:
            if name.startswith(prefix):
                return Match(ext, fmt_name, mime)

    # Check exact stream name matches in priority order
    for stream_name, ext, fmt_name, mime in _STREAM_MATCHES:
        if stream_name in stream_names:
            return Match(ext, fmt_name, mime)

    return None


def main(file_path: os.PathLike, head: bytes, foot: bytes) -> Match | None:
    if len(head) < 76:
        return None

    # Verify magic bytes
    if head[:8] != match_bytes:
        if head[:4] != match_bytes_short:
            return None

    # Parse CFBF header
    sector_shift = struct.unpack_from("<H", head, 30)[0]
    if sector_shift not in (9, 12):
        return None
    sector_size = 1 << sector_shift

    first_dir_secid = struct.unpack_from("<i", head, 48)[0]
    if first_dir_secid < 0:
        return None

    # Directory sector offset: header occupies first sector_size bytes
    dir_offset = (first_dir_secid + 1) * sector_size

    try:
        with open(file_path, "rb") as f:
            f.seek(dir_offset)
            dir_data = f.read(sector_size)
    except (OSError, ValueError):
        return None

    if not dir_data:
        return None

    stream_names = _extract_stream_names(dir_data)
    return _identify_format(stream_names)
