import os
from io import BytesIO
from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest

import puremagic
from test.common import (
    RESOURCE_DIR,
    IMAGE_DIR,
    VIDEO_DIR,
    AUDIO_DIR,
    OFFICE_DIR,
    ARCHIVE_DIR,
    MEDIA_DIR,
    SYSTEM_DIR,
    LOCAL_DIR,
)


TGA_FILE = os.path.join(IMAGE_DIR, "test.tga")


class MockBytesIO(BytesIO):
    def seek(self, offset, whence=0):
        if offset < 0:
            raise OSError("Invalid seek position")
        return super().seek(offset, whence)


mp4magic = b"\x00\x00\x00\x1c\x66\x74\x79\x70\x4d\x53\x4e\
\x56\x01\x29\x00\x46\x4d\x53\x4e\x56\x6d\x70\x34\x32"
expect_ext = ".mp4"
expect_mime = "video/mp4"


def group_run(directory):
    failures = []
    ext_failures = []
    mime_failures = []
    for item in os.listdir(directory):
        try:
            ext = puremagic.from_file(os.path.join(directory, item))
        except puremagic.PureError:
            failures.append(item)
        else:
            if not item.endswith(ext):
                ext_failures.append((item, ext))

        try:
            mime = puremagic.from_file(os.path.join(directory, item), mime=True)
        except puremagic.PureError:
            failures.append(item)
        else:
            if not mime:
                mime_failures.append(item)
    if failures:
        raise AssertionError(
            "The following items could not be identified from the {} folder: {}".format(directory, ", ".join(failures))
        )
    if ext_failures:
        raise AssertionError(
            "The following files did not have the expected extensions: {}".format(
                ", ".join([f'"{item}" expected "{ext}"' for item, ext in ext_failures])
            )
        )
    if mime_failures:
        raise AssertionError("The following files did not have a mime type: {}".format(", ".join(mime_failures)))


def test_file():
    """File identification"""
    with NamedTemporaryFile(delete=False) as mp4file:
        mp4file.write(mp4magic)

    ext = puremagic.from_file(mp4file.name)
    os.unlink(mp4file.name)
    assert expect_ext == ext


def test_hex_string():
    """Hex string identification"""
    ext = puremagic.from_string(mp4magic)
    assert expect_ext == ext


def test_string():
    """String identification"""
    ext = puremagic.from_string(bytes(mp4magic))
    assert expect_ext == ext


def test_string_with_confidence():
    """String identification: magic_string"""
    ext = puremagic.magic_string(bytes(mp4magic))
    assert expect_ext == ext[0].extension
    with pytest.raises(ValueError):
        puremagic.magic_string("")


def test_magic_string_with_filename_hint():
    """String identification: magic_string with hint"""
    filename = os.path.join(OFFICE_DIR, "test.xlsx")
    with open(filename, "rb") as f:
        data = f.read()
    ext = puremagic.magic_string(data, filename=filename)
    assert ext[0].extension == ".xlsx"


def test_not_found():
    """Bad file type via string"""
    try:
        with pytest.raises(puremagic.PureError):
            puremagic.from_string("not applicable string")
    except TypeError:
        # Python 2.6 doesn't support using
        # assertRaises as a context manager
        pass


def test_magic_file():
    """File identification with magic_file"""
    assert puremagic.magic_file(TGA_FILE)[0].extension == ".tga"
    open("test_empty_file", "w").close()
    try:
        with pytest.raises(ValueError):
            puremagic.magic_file("test_empty_file")
    finally:
        os.unlink("test_empty_file")


def test_stream():
    """Stream identification"""
    ext = puremagic.from_stream(BytesIO(mp4magic))
    assert expect_ext == ext
    with pytest.raises(ValueError):
        puremagic.from_stream(BytesIO(b""))


def test_magic_stream():
    """File identification with magic_stream"""
    with open(TGA_FILE, "rb") as f:
        stream = BytesIO(f.read())
    result = puremagic.magic_stream(stream, TGA_FILE)
    assert result[0].extension == ".tga"
    with pytest.raises(ValueError):
        puremagic.magic_stream(BytesIO(b""))


def test_small_stream_error():
    ext = puremagic.from_stream(MockBytesIO(b"#!/usr/bin/env python"))
    assert ext == ".py"


def test_mime():
    """Identify mime type"""
    assert puremagic.from_file(TGA_FILE, True) == "image/tga"


def test_images():
    """Test common image formats"""
    group_run(IMAGE_DIR)


def test_video():
    """Test common video formats"""
    group_run(VIDEO_DIR)


def test_audio():
    """Test common audio formats"""
    group_run(AUDIO_DIR)


def test_office():
    """Test common office document formats"""
    # Office files have very similar magic numbers, and may overlap
    for item in os.listdir(OFFICE_DIR):
        puremagic.from_file(os.path.join(OFFICE_DIR, item))


def test_archive():
    """Test common compressed archive formats"""
    # pcapng files from https://wiki.wireshark.org/Development/PcapNg
    group_run(ARCHIVE_DIR)


def test_media():
    """Test common media formats"""
    group_run(MEDIA_DIR)


def test_system():
    """Test common system formats"""
    group_run(SYSTEM_DIR)


def test_ext():
    """Test ext from filename"""
    ext = puremagic.ext_from_filename("test.tar.bz2")
    assert ext == ".tar.bz2", ext


def test_cmd_options():
    """Test CLI options"""
    try:
        from puremagic.main import command_line_entry  # noqa: PLC0415
    except ImportError:
        raise AssertionError("could not load command_line_entry")

    command_line_entry(__file__, os.path.join(AUDIO_DIR, "test.mp3"), "-v")
    command_line_entry(__file__, "DOES NOT EXIST FILE")
    command_line_entry(__file__, os.path.join(RESOURCE_DIR, "fake_file"), "-v")


def test_bad_magic_input():
    """Test bad magic input"""
    with pytest.raises(ValueError):
        puremagic.main.perform_magic(None, None, None)


def test_fake_file():
    assert puremagic.magic_file(filename=Path(LOCAL_DIR, "resources", "fake_file"))[0].confidence == 0.5
