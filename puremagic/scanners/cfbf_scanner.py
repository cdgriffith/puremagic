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

# Multi-stream detection: all listed streams must be present.
# Each entry: (required_streams, extension, name, mime_type)
_MULTI_STREAM_MATCHES = [
    (("_StringPool", "_StringData"), ".msi", "Windows Installer Package", "application/x-msi"),
]

# Root directory entry CLSIDs that identify specific formats.
# CLSIDs are stored in mixed-endian format in CFBF files.
# Each entry: (clsid_bytes, extension, name, mime_type)
_CLSID_MATCHES = [
    # Microsoft Project 98/2000/2002/2003: {74b78f3a-c8c8-11d1-be11-00c04fb6faf1}
    (
        b"\x3a\x8f\xb7\x74\xc8\xc8\xd1\x11\xbe\x11\x00\xc0\x4f\xb6\xfa\xf1",
        ".mpp",
        "Microsoft Project",
        "application/vnd.ms-project",
    ),
    # Microsoft Project 4.x: {72fd3320-9a05-11cf-85a4-00a0c904de5f}
    (
        b"\x20\x33\xfd\x72\x05\x9a\xcf\x11\x85\xa4\x00\xa0\xc9\x04\xde\x5f",
        ".mpp",
        "Microsoft Project",
        "application/vnd.ms-project",
    ),
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


def _extract_root_clsid(dir_data: bytes) -> bytes | None:
    """Extract the CLSID from the root directory entry (obj_type 5)."""
    for i in range(0, len(dir_data), 128):
        entry = dir_data[i : i + 128]
        if len(entry) < 96:
            break
        if entry[66] == 5:  # Root storage
            return entry[80:96]
    return None


def _identify_format(stream_names: set[str], dir_data: bytes) -> Match | None:
    """Match stream names and CLSIDs against known CFBF format signatures."""
    # Check prefix matches first (e.g. __substg1.0_ for MSG)
    for name in stream_names:
        for prefix, ext, fmt_name, mime in _PREFIX_MATCHES:
            if name.startswith(prefix):
                return Match(ext, fmt_name, mime)

    # Check exact stream name matches in priority order
    for stream_name, ext, fmt_name, mime in _STREAM_MATCHES:
        if stream_name in stream_names:
            return Match(ext, fmt_name, mime)

    # Check multi-stream matches (all required streams must be present)
    for required_streams, ext, fmt_name, mime in _MULTI_STREAM_MATCHES:
        if all(s in stream_names for s in required_streams):
            return Match(ext, fmt_name, mime)

    # Check root CLSID
    root_clsid = _extract_root_clsid(dir_data)
    if root_clsid:
        for clsid, ext, fmt_name, mime in _CLSID_MATCHES:
            if root_clsid == clsid:
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
    return _identify_format(stream_names, dir_data)
