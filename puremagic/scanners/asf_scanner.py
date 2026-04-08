import os
import struct

from puremagic.scanners.helpers import Match

# ASF Header Object GUID
match_bytes = b"\x30\x26\xb2\x75\x8e\x66\xcf\x11\xa6\xd9\x00\xaa\x00\x62\xce\x6c"

_STREAM_PROPS_GUID = b"\x91\x07\xdc\xb7\xb7\xa9\xcf\x11\x8e\xe6\x00\xc0\x0c\x20\x53\x65"
_AUDIO_MEDIA_GUID = b"\x40\x9e\x69\xf8\x4d\x5b\xcf\x11\xa8\xfd\x00\x80\x5f\x5c\x44\x2b"
_VIDEO_MEDIA_GUID = b"\xc0\xef\x19\xbc\x4d\x5b\xcf\x11\xa8\xfd\x00\x80\x5f\x5c\x44\x2b"


def main(file_path: os.PathLike, head: bytes, foot: bytes) -> Match | None:
    if not head or len(head) < 30:
        return None
    if head[:16] != match_bytes:
        return None

    header_size = struct.unpack_from("<Q", head, 16)[0]
    obj_count = struct.unpack_from("<I", head, 24)[0]

    # Read the full ASF header if our head buffer is too small
    if header_size > len(head):
        try:
            with open(file_path, "rb") as f:
                data = f.read(min(int(header_size), 65536))
        except (OSError, ValueError):
            return None
    else:
        data = head

    has_audio = False
    has_video = False
    offset = 30  # Past header GUID(16) + size(8) + count(4) + reserved(2)

    for _ in range(min(obj_count, 50)):
        if offset + 24 > len(data):
            break
        obj_guid = data[offset : offset + 16]
        obj_size = struct.unpack_from("<Q", data, offset + 16)[0]
        if obj_size < 24:
            break

        if obj_guid == _STREAM_PROPS_GUID and offset + 40 <= len(data):
            stream_type = data[offset + 24 : offset + 40]
            if stream_type == _VIDEO_MEDIA_GUID:
                has_video = True
            elif stream_type == _AUDIO_MEDIA_GUID:
                has_audio = True

        offset += int(obj_size)

    if has_video:
        return Match(".wmv", "Windows Media Video", "video/x-ms-wmv")
    if has_audio:
        return Match(".wma", "Windows Media Audio", "audio/x-ms-wma")

    return Match(".asf", "Advanced Systems Format", "video/x-ms-asf")
