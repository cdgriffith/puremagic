import os
from io import BytesIO
from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest

import puremagic
from test.common import (
    ARCHIVE_DIR,
    AUDIO_DIR,
    IMAGE_DIR,
    LOCAL_DIR,
    MEDIA_DIR,
    OFFICE_DIR,
    RESOURCE_DIR,
    SYSTEM_DIR,
    VIDEO_DIR,
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


@pytest.mark.parametrize("path_type", [str, Path])
@pytest.mark.parametrize(
    "filename, expected",
    [("README", ""), ("report.PDF", ".pdf"), ("archive.tar.bz2", ".tar.bz2"), (".profile", ".profile")],
)
def test_ext_ignores_parent_directory_dots(path_type, filename, expected):
    filename = path_type(os.path.join("directory.with.dots", filename))
    assert puremagic.ext_from_filename(filename) == expected


def test_cmd_options():
    """Test CLI options"""
    try:
        from puremagic.main import command_line_entry
    except ImportError:
        raise AssertionError("could not load command_line_entry")

    command_line_entry(__file__, os.path.join(AUDIO_DIR, "test.mp3"), "-v")
    command_line_entry(__file__, "DOES NOT EXIST FILE")
    command_line_entry(__file__, os.path.join(RESOURCE_DIR, "fake_file"), "-v")


@pytest.mark.parametrize("mime", [False, True])
@pytest.mark.parametrize("verbose", [False, True])
def test_cmd_directory_options(tmp_path, capsys, mime, verbose):
    from puremagic.main import command_line_entry

    images = [("test.gif", ".gif", "image/gif"), ("test.png", ".png", "image/png")]
    expected = set()
    for name, extension, mime_type in images:
        filename = tmp_path / name
        filename.write_bytes((Path(IMAGE_DIR) / name).read_bytes())
        expected.add(f"'{filename}' : {mime_type if mime else extension}")
    empty = tmp_path / "empty"
    empty.touch()
    expected.add(f"'{empty}' : could not be Identified")
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "nested.gif").write_bytes((Path(IMAGE_DIR) / "test.gif").read_bytes())

    args = [str(tmp_path)]
    if mime:
        args.append("-m")
    if verbose:
        args.append("-v")
    command_line_entry(*args)

    out = capsys.readouterr().out
    summaries = [line for line in out.splitlines() if line.startswith("'")]
    assert len(summaries) == len(expected)
    assert set(summaries) == expected
    assert str(nested) not in out
    assert out.count("Total Possible Matches:") == (len(images) if verbose else 0)
    if verbose:
        for name, extension, mime_type in images:
            filename = tmp_path / name
            summary = f"'{filename}' : {mime_type if mime else extension}"
            assert f"{summary}\nTotal Possible Matches:" in out
            assert f"Extension: {extension}" in out
            assert f"Mime Type: {mime_type}" in out


@pytest.mark.parametrize("nested_only", [False, True])
def test_cmd_empty_directory_verbose(tmp_path, capsys, nested_only):
    from puremagic.main import command_line_entry

    if nested_only:
        (tmp_path / "nested").mkdir()

    command_line_entry(str(tmp_path), "-v")

    assert capsys.readouterr().out == ""


def test_cmd_verbose_file_errors(tmp_path, capsys):
    from puremagic.main import command_line_entry

    missing = tmp_path / "missing"
    empty = tmp_path / "empty"
    empty.touch()
    image = tmp_path / "test.gif"
    image.write_bytes((Path(IMAGE_DIR) / "test.gif").read_bytes())

    command_line_entry(str(missing), str(empty), str(image), "-v")

    out = capsys.readouterr().out
    assert out.startswith(
        f"File '{missing}' does not exist!\n"
        f"'{empty}' : could not be Identified\n"
        f"'{image}' : .gif\nTotal Possible Matches:"
    )
    assert out.count("Total Possible Matches:") == 1
    assert "Extension: .gif" in out


def test_bad_magic_input():
    """Test bad magic input"""
    with pytest.raises(ValueError):
        puremagic.main.perform_magic(None, None, None)  # type: ignore[invalid-argument-type]


def test_from_extension():
    """Test from_extension lookup"""
    assert puremagic.from_extension(".pdf") == "application/pdf"
    assert puremagic.from_extension("pdf") == "application/pdf"
    assert puremagic.from_extension("PDF") == "application/pdf"
    assert puremagic.from_extension(".jpg") == "image/jpeg"
    assert puremagic.from_extension("png") == "image/png"
    # Test name mode
    name = puremagic.from_extension(".pdf", mime=False)
    assert name != ""
    # Test unknown extension raises PureError
    with pytest.raises(puremagic.PureError):
        puremagic.from_extension(".xyz_unknown_ext")


def test_magic_extension():
    """Test magic_extension returns list of matches"""
    results = puremagic.magic_extension(".pdf")
    assert len(results) >= 1
    assert results[0].mime_type == "application/pdf"
    assert results[0].extension == ".pdf"
    # Check sorted by confidence descending
    for i in range(len(results) - 1):
        assert results[i].confidence >= results[i + 1].confidence
    # Unknown extension returns empty list
    assert puremagic.magic_extension(".xyz_unknown_ext") == []


def test_from_mime():
    """Test from_mime lookup (#149)"""
    assert puremagic.from_mime("application/pdf") == ".pdf"
    assert puremagic.from_mime("image/jpeg") == ".jpg"
    assert puremagic.from_mime("image/png") == ".png"
    assert puremagic.from_mime("audio/mpeg") == ".mp3"
    assert puremagic.from_mime("text/plain") == ".txt"
    # Case-insensitive and MIME parameters are ignored
    assert puremagic.from_mime("IMAGE/PNG") == ".png"
    assert puremagic.from_mime("text/html; charset=UTF-8") == ".html"
    with pytest.raises(puremagic.PureError):
        puremagic.from_mime("application/x-unknown-mime-type")
    with pytest.raises(puremagic.PureError):
        puremagic.from_mime("")


def test_magic_mime():
    """Test magic_mime returns one entry per extension, best first"""
    results = puremagic.magic_mime("image/jpeg")
    extensions = [r.extension for r in results]
    assert extensions[0] == ".jpg"
    assert ".jpeg" in extensions
    assert len(extensions) == len(set(extensions))
    assert all(r.mime_type == "image/jpeg" for r in results)
    assert puremagic.magic_mime("application/x-unknown-mime-type") == []


def test_cmd_extension_option():
    """Test CLI -e option"""
    from puremagic.main import command_line_entry

    command_line_entry("-e", "pdf")
    command_line_entry("-e", ".jpg")
    command_line_entry("-e", "pdf", "-v")
    command_line_entry("-e", "xyz_unknown_ext_123")


def test_cmd_mime_type_option(capsys):
    """Test CLI -t option"""
    from puremagic.main import command_line_entry

    command_line_entry("-t", "image/jpeg")
    assert capsys.readouterr().out.strip() == ".jpg"
    command_line_entry("--mime-type", "application/pdf")
    assert capsys.readouterr().out.strip() == ".pdf"
    command_line_entry("-t", "image/jpeg", "-v")
    out = capsys.readouterr().out
    assert "Best Match" in out
    assert "Extension: .jpg" in out
    command_line_entry("-t", "application/x-unknown-mime-type")
    assert "Could not find MIME type" in capsys.readouterr().out
    command_line_entry("-t", "application/x-unknown-mime-type", "-v")
    assert "No matches found" in capsys.readouterr().out
    with pytest.raises(SystemExit):
        command_line_entry("-t", "image/jpeg", "-e", "pdf")


def test_fake_file():
    results = puremagic.magic_file(filename=Path(LOCAL_DIR, "resources", "fake_file"))
    assert results[0].confidence == 0.5, results


def test_riff_wav_mime():
    """RIFF scanner returns audio/wav (not audio/wave) for WAV files"""
    mime = puremagic.from_file(os.path.join(AUDIO_DIR, "test.wav"), mime=True)
    assert mime == "audio/wav"


def test_cfbf_doc():
    """CFBF scanner correctly identifies Word .doc"""
    ext = puremagic.from_file(os.path.join(OFFICE_DIR, "test.doc"))
    assert ext == ".doc"
    mime = puremagic.from_file(os.path.join(OFFICE_DIR, "test.doc"), mime=True)
    assert mime == "application/msword"


def test_cfbf_ppt():
    """CFBF scanner correctly identifies PowerPoint .ppt"""
    ext = puremagic.from_file(os.path.join(OFFICE_DIR, "test.ppt"))
    assert ext == ".ppt"
    mime = puremagic.from_file(os.path.join(OFFICE_DIR, "test.ppt"), mime=True)
    assert mime == "application/vnd.ms-powerpoint"


def test_cfbf_msg():
    """CFBF scanner correctly identifies Outlook .msg"""
    ext = puremagic.from_file(os.path.join(OFFICE_DIR, "test.msg"))
    assert ext == ".msg"
    mime = puremagic.from_file(os.path.join(OFFICE_DIR, "test.msg"), mime=True)
    assert mime == "application/vnd.ms-outlook"


def test_bash_shebang_detected():
    """Regression for #150: shell script shebangs identify as .sh, not .txt."""
    bash = puremagic.from_stream(BytesIO(b"#!/bin/bash\necho hi\n"))
    assert bash == ".sh"
    sh = puremagic.from_stream(BytesIO(b"#!/bin/sh\necho hi\n"))
    assert sh == ".sh"
    env_bash = puremagic.from_stream(BytesIO(b"#!/usr/bin/env bash\necho hi\n"))
    assert env_bash == ".sh"
    zsh = puremagic.from_stream(BytesIO(b"#!/bin/zsh\necho hi\n"))
    assert zsh == ".sh"


def test_jpeg_defaults_to_jpg_extension():
    """#164 JPEG data without a filename hint should report the common .jpg extension"""
    with open(os.path.join(IMAGE_DIR, "test.jpg"), "rb") as f:
        data = f.read()
    assert puremagic.from_string(data) == ".jpg"
    assert puremagic.from_stream(BytesIO(data)) == ".jpg"
    assert puremagic.magic_string(data)[0].extension == ".jpg"
    assert puremagic.from_string(data, filename="photo.jpeg") == ".jpeg"
    assert puremagic.from_string(data, mime=True) == "image/jpeg"


def test_html_xls_msg():
    """Mime Detection correctly identifies HTML File with .xls extension and capitalized <HTML tag"""
    mime = puremagic.from_file(os.path.join(OFFICE_DIR, "test_html.xls"), mime=True)
    assert mime == "text/html"
