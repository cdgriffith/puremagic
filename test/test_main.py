# -*- coding: utf-8 -*-
from pathlib import Path
from sys import version_info
from warnings import filterwarnings

import pytest

from puremagic.main import what

filterwarnings("ignore", message="'imghdr' is deprecated")
try:  # imghdr was removed from the standard library in Python 3.13
    from imghdr import what as imghdr_what
except ModuleNotFoundError:
    imghdr_what = None  # type: ignore[assignment]

file_tests = ["bmp", "gif", "jpg", "png", "tif", "webp"]

here = Path(__file__).resolve().parent


@pytest.mark.skipif(imghdr_what is None, reason="imghdr was removed from the standard library in Python 3.13")
@pytest.mark.parametrize("file", file_tests)
def test_what_from_file(file, h=None):
    """Run each test with a path string and a pathlib.Path."""
    file = str(here / f"resources/images/test.{file}")
    assert what(file, h) == imghdr_what(file, h)
    file = Path(file).resolve()
    assert what(file, h) == imghdr_what(file, h)


@pytest.mark.skipif(imghdr_what is None, reason="imghdr was removed from the standard library in Python 3.13")
def test_what_from_file_none():
    file = str(here / "resources/fake_file")
    assert what(file) == imghdr_what(file) is None
    file = Path(file).resolve()
    assert what(file, None) == imghdr_what(file, None) is None


@pytest.mark.skipif(imghdr_what is None, reason="imghdr was removed from the standard library in Python 3.13")
def test_what_from_string_no_str(h="string"):
    """what() should raise a TypeError if h is a string."""
    with pytest.raises(TypeError):
        imghdr_what(None, h)
    with pytest.raises(TypeError) as excinfo:
        what(None, h)
    assert str(excinfo.value) == "h must be bytes, not str.  Consider using bytes.fromhex(h)"


string_tests = [
    ("bmp", "424d"),
    ("bmp", "424d787878785c3030305c303030"),
    ("bmp", b"BM"),
    ("exr", "762f3101"),
    ("exr", b"\x76\x2f\x31\x01"),
    ("exr", b"v/1\x01"),
    ("gif", "474946383761"),
    ("gif", "474946383961"),
    ("gif", b"GIF87a"),
    ("gif", b"GIF89a"),
    ("pbm", b"P1 "),
    ("pbm", b"P1\n"),
    ("pbm", b"P1\r"),
    ("pbm", b"P1\t"),
    ("pbm", b"P4 "),
    ("pbm", b"P4\n"),
    ("pbm", b"P4\r"),
    ("pbm", b"P4\t"),
    ("pgm", b"P2 "),
    ("pgm", b"P2\n"),
    ("pgm", b"P2\r"),
    ("pgm", b"P2\t"),
    ("pgm", b"P5 "),
    ("pgm", b"P5\n"),
    ("pgm", b"P5\r"),
    ("pgm", b"P5\t"),
    ("png", "89504e470d0a1a0a"),
    ("png", b"\211PNG\r\n\032\n"),
    ("png", b"\x89PNG\r\n\x1a\n"),
    ("ppm", b"P3 "),
    ("ppm", b"P3\n"),
    ("ppm", b"P3\r"),
    ("ppm", b"P3\t"),
    ("ppm", b"P6 "),
    ("ppm", b"P6\n"),
    ("ppm", b"P6\r"),
    ("ppm", b"P6\t"),
    ("rast", "59A66A95"),
    ("rast", b"\x59\xa6\x6a\x95"),
    ("rgb", "01da"),
    ("rgb", b"\x01\xda"),
    ("tiff", "49492a00"),
    ("tiff", "4d4d002a"),
    ("tiff", "4d4d002b"),
    ("tiff", b"II*\x00"),  # bytes.fromhex('49492a00')
    ("tiff", b"MM\x00*"),  # bytes.fromhex('4d4d002a')
    ("tiff", b"MM\x00+"),  # bytes.fromhex('4d4d002b')
    ("webp", b"RIFF____WEBP"),
    ("xbm", b"#define "),
    (None, "decafbad"),
    (None, b"decafbad"),
]


@pytest.mark.skipif(imghdr_what is None, reason="imghdr was removed from the standard library in Python 3.13")
@pytest.mark.parametrize("expected, h", string_tests)
def test_what_from_string(expected, h):
    if isinstance(h, str):  # In imgdir.what() h must be bytes, not str.
        h = bytes.fromhex(h)  # ex. "474946383761" --> b"GIF87a"
    assert imghdr_what(None, h) == what(None, h) == expected


@pytest.mark.skipif(imghdr_what is None, reason="imghdr was removed from the standard library in Python 3.13")
@pytest.mark.parametrize(
    "expected, h",
    [
        ("jpeg", "ffd8ffdb"),
        ("jpeg", b"\xff\xd8\xff\xdb"),
    ],
)
def test_what_from_string_py311(expected, h):
    """
    These tests fail with imghdr on Python < 3.11.
    """
    if isinstance(h, str):  # In imgdir.what() h must be bytes, not str.
        h = bytes.fromhex(h)
    assert what(None, h) == expected
    if version_info < (3, 11):  # TODO: Document these imghdr fails
        expected = None
    assert imghdr_what(None, h) == expected


@pytest.mark.skipif(imghdr_what is None, reason="imghdr was removed from the standard library in Python 3.13")
@pytest.mark.parametrize(
    "expected, h",
    [
        ("jpeg", b"______Exif"),
        ("jpeg", b"______Exif"),
        ("jpeg", b"______JFIF"),
        ("jpeg", b"______JFIF"),
        ("tiff", "4949"),
        ("tiff", "49495c7832615c783030"),
        ("tiff", "4d4d"),
        ("tiff", "4d4d5c7830305c783261"),
        ("tiff", b"II"),  # bytes.fromhex('4949')
        ("tiff", b"II\\x2a\\x00"),  # bytes.fromhex('49495c7832615c783030')
        ("tiff", b"MM"),  # bytes.fromhex('4d4d')
        ("tiff", b"MM\\x00\\x2a"),  # bytes.fromhex('4d4d5c7830305c783261')
    ],
)
@pytest.mark.parametrize("imghdr_strict", [True, False])
def test_what_from_string_imghdr_strict(expected, h, imghdr_strict):
    """
    These tests pass with imghdr but fail with puremagic.
    """
    if isinstance(h, str):  # In imgdir.what() h must be bytes, not str.
        h = bytes.fromhex(h)
    assert imghdr_what(None, h) == expected
    assert what(None, h, imghdr_strict) == (expected if imghdr_strict else None)
