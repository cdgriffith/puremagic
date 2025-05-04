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


def test_text_scanner():
    # Test the text scanner with a sample text file
    results = puremagic.magic_file(OFFICE_DIR / "text_lf.txt")
    assert results[0].extension == ".txt"
    assert results[0].name == "ASCII text, with LF line terminators"
    assert results[0].mime_type == "text/plain"
    assert results[0].confidence == 0.9

    results = puremagic.magic_file(OFFICE_DIR / "text_crlf.txt")
    assert results[0].extension == ".txt"
    assert results[0].name == "ASCII text, with CRLF line terminators"
    assert results[0].mime_type == "text/plain"
    assert results[0].confidence == 0.9

    results = puremagic.magic_file(OFFICE_DIR / "text_cr.txt")
    assert results[0].extension == ".txt"
    assert results[0].name == "ASCII text, with CR line terminators"
    assert results[0].mime_type == "text/plain"
    assert results[0].confidence == 0.9
