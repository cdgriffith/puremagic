import puremagic
from test.common import OFFICE_DIR, SYSTEM_DIR, AUDIO_DIR
from puremagic.scanners import python_scanner, json_scanner, sndhdr_scanner

sample_text = b"""Lorem ipsum dolor sit amet, consectetur adipiscing elit,{ending}
sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.{ending}
{ending}
Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.{ending}
Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur.{ending}
Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.{ending}
"""


def test_text_scanner():
    # Test the text scanner with a sample text file
    lr_file = OFFICE_DIR / "text_lf.txt"
    lr_file.write_bytes(sample_text.replace(b"\n", b"").replace(b"{ending}", b"\n"))
    results = puremagic.magic_file(lr_file)
    assert results[0].extension == ".txt"
    assert results[0].name == "ASCII text, with LF line terminators"
    assert results[0].mime_type == "text/plain"
    assert results[0].confidence == 0.9

    crlf_file = OFFICE_DIR / "text_crlf.txt"
    crlf_file.write_bytes(sample_text.replace(b"\n", b"").replace(b"{ending}", b"\r\n"))
    results = puremagic.magic_file(crlf_file)
    assert results[0].extension == ".txt"
    assert results[0].name == "ASCII text, with CRLF line terminators"
    assert results[0].mime_type == "text/plain"
    assert results[0].confidence == 0.9

    cr_file = OFFICE_DIR / "text_cr.txt"
    cr_file.write_bytes(sample_text.replace(b"\n", b"").replace(b"{ending}", b"\r"))
    results = puremagic.magic_file(cr_file)
    assert results[0].extension == ".txt"
    assert results[0].name == "ASCII text, with CR line terminators"
    assert results[0].mime_type == "text/plain"
    assert results[0].confidence == 0.9


def test_python_scanner():
    # Test the Python scanner with a sample Python file
    py_file = SYSTEM_DIR / "test.py"
    result = python_scanner.main(py_file)
    magic_result = puremagic.magic_file(py_file)
    assert result.confidence == magic_result[0].confidence
    assert result.extension == ".py"
    assert result.name == "Python Script"
    assert result.mime_type == "text/x-python"
    assert result.confidence == 1.0


def test_json_scanner():
    json_file = SYSTEM_DIR / "test.json"
    result = json_scanner.main(json_file, b"{", b"}")
    magic_result = puremagic.magic_file(json_file)
    assert result.confidence == magic_result[0].confidence
    assert result.extension == ".json"
    assert result.name == "JSON File"
    assert result.mime_type == "application/json"
    assert result.confidence == 1.0


def test_sndhdr_scanner():
    # Test the sndhdr scanner with WAV file
    wav_file = AUDIO_DIR / "test.wav"
    with open(wav_file, "rb") as f:
        head = f.read(512)
    result = sndhdr_scanner.test_wav(head)
    puremagic.magic_file(wav_file)
    assert result is not None
    assert result.extension == ".wav"
    assert result.name == "WAVE Audio File"
    assert result.mime_type == "audio/x-wav"
    assert result.confidence == 1.0

    # Test the sndhdr scanner with AIFF file
    aif_file = AUDIO_DIR / "test.aif"
    with open(aif_file, "rb") as f:
        head = f.read(512)
    result = sndhdr_scanner.test_aifc(head)
    puremagic.magic_file(aif_file)
    assert result is not None
    assert result.extension == ".aif"
    assert result.name == "Audio Interchange File Format"
    assert result.mime_type == "audio/x-aiff"
    assert result.confidence == 1.0

    # Test the main function with both files
    with open(wav_file, "rb") as f:
        wav_head = f.read(512)
    result = sndhdr_scanner.main(wav_file, wav_head, b"")
    assert result is not None
    assert result.extension == ".wav"

    with open(aif_file, "rb") as f:
        aif_head = f.read(512)
    result = sndhdr_scanner.main(aif_file, aif_head, b"")
    assert result is not None
    assert result.extension == ".aif"

    # Test the sndhdr scanner with sndr file
    sndr_file = AUDIO_DIR / "test.sndr"
    with open(sndr_file, "rb") as f:
        head = f.read(512)
    result = sndhdr_scanner.test_sndr(head)
    puremagic.magic_file(aif_file)
    assert result is not None
    assert result.extension == ".sndr"
    assert result.name == "Macintosh SNDR Resource"
    assert result.mime_type == "audio/x-sndr"
    assert result.confidence == 0.1
