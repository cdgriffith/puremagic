import pytest

import puremagic


def ftyp(major, compatible):
    payload = major + bytes(4) + b"".join(compatible)
    return (8 + len(payload)).to_bytes(4, "big") + b"ftyp" + payload


@pytest.mark.parametrize(
    ("major", "compatible", "expected"),
    [
        (b"heic", [b"mif1"], "image/heif"),
        (b"heic", [b"mif1", b"heic"], "image/heif"),
        (b"heic", [b"mif1", b"heic", b"miaf"], "image/heif"),
        (b"avif", [b"avif"], "image/avif"),
        (b"avif", [b"avif", b"mif1"], "image/avif"),
        (b"avif", [b"avif", b"mif1", b"miaf"], "image/avif"),
        (b"avif", [b"avif", b"mif1", b"miaf", b"MA1B"], "image/avif"),
    ],
)
def test_image_brand_is_independent_of_ftyp_size(major, compatible, expected):
    assert puremagic.from_string(ftyp(major, compatible), mime=True) == expected


@pytest.mark.parametrize(
    ("major", "expected"),
    [
        (b"isom", "video/mp4"),
        (b"mp41", "video/mp4"),
        (b"mp42", "video/mp4"),
        (b"qt  ", "video/quicktime"),
        (b"3gp6", "video/3gpp"),
    ],
)
@pytest.mark.parametrize("compatible_count", [1, 2, 3])
def test_existing_media_brands_are_recognized(major, expected, compatible_count):
    assert puremagic.from_string(ftyp(major, [major] * compatible_count), mime=True) == expected
