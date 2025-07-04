import puremagic
from test.common import OFFICE_DIR, SYSTEM_DIR
from puremagic.scanners import python_scanner, json_scanner

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
