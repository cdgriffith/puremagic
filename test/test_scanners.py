import os
import tempfile
from pathlib import Path
from zipfile import ZipFile

import puremagic
from test.common import IMAGE_DIR, OFFICE_DIR, SYSTEM_DIR, AUDIO_DIR, VIDEO_DIR
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
    assert results[0].name == "ascii text, with LF line terminators"
    assert results[0].mime_type == "text/plain"
    assert results[0].confidence == 0.9

    crlf_file = OFFICE_DIR / "text_crlf.txt"
    crlf_file.write_bytes(sample_text.replace(b"\n", b"").replace(b"{ending}", b"\r\n"))
    results = puremagic.magic_file(crlf_file)
    assert results[0].extension == ".txt"
    assert results[0].name == "ascii text, with CRLF line terminators"
    assert results[0].mime_type == "text/plain"
    assert results[0].confidence == 0.9

    cr_file = OFFICE_DIR / "text_cr.txt"
    cr_file.write_bytes(sample_text.replace(b"\n", b"").replace(b"{ending}", b"\r"))
    results = puremagic.magic_file(cr_file)
    assert results[0].name == "ascii text, with CR line terminators"
    assert results[0].extension == ".txt"
    assert results[0].mime_type == "text/plain"
    assert results[0].confidence == 0.9


def test_utf16_le_not_mp1():
    # GH #134: UTF-16 LE BOM (FF FE) should not be misidentified as .mp1
    data = b"\xff\xfe" + "a,b,c\n1,2,3\n".encode("utf-16-le")
    result = puremagic.from_string(data)
    assert result != ".mp1", "UTF-16 LE data misidentified as .mp1"
    result_mime = puremagic.from_string(data, mime=True)
    assert result_mime != "audio/mpeg", "UTF-16 LE data misidentified as audio/mpeg"


def test_utf16_le_csv_deep_scan():
    # GH #134: UTF-16 LE CSV file should be detected as CSV via text_scanner deep scan
    utf16_csv = OFFICE_DIR / "test_utf16le.csv"
    results = puremagic.magic_file(utf16_csv)
    assert results[0].extension == ".csv"
    assert results[0].mime_type == "text/csv"
    assert "comma" in results[0].name
    assert results[0].confidence >= 0.9


def test_from_string_nonexistent_filename():
    # GH #137: passing filename for extension hint should not raise FileNotFoundError
    # Use PDF-like bytes so identify_all finds a match via magic numbers,
    # then deep scan is skipped (file doesn't exist) and the match is returned.
    pdf_bytes = b"%PDF-1.4 fake content"
    result = puremagic.from_string(pdf_bytes, filename="nonexistent.pdf")
    assert result == ".pdf"

    # magic_string should also work without crashing
    results = puremagic.magic_string(pdf_bytes, filename="nonexistent.pdf")
    assert any(r.extension == ".pdf" for r in results)


def test_python_scanner():
    # Test the Python scanner with a sample Python file
    py_file = SYSTEM_DIR / "test.py"
    result = python_scanner.main(py_file, None, None)
    magic_result = puremagic.magic_file(py_file)
    assert result is not None
    assert result.extension == ".py"
    assert result.confidence == magic_result[0].confidence
    assert result.name == "Python Script"
    assert result.mime_type == "text/x-python"
    assert result.confidence == 1.0


def test_json_scanner():
    json_file = SYSTEM_DIR / "test.json"
    result = json_scanner.main(json_file, b"{", b"}")
    magic_result = puremagic.magic_file(json_file)
    assert result is not None
    assert result.confidence == magic_result[0].confidence
    assert result.extension == ".json"
    assert result.name == "JSON File"
    assert result.mime_type == "application/json"
    assert result.confidence == 1.0


def test_eml_scanner():
    eml_file = OFFICE_DIR / "test.eml"
    results = puremagic.magic_file(eml_file)
    assert results[0].extension == ".eml"
    assert results[0].name == "RFC 2822 Email Message"
    assert results[0].mime_type == "message/rfc822"
    assert results[0].confidence == 1.0


def test_jpg_without_extension():
    # GH #141: JPEG file without extension should still be identified as image/jpeg
    import struct

    data = b"\xff\xd8\xff\xe0"
    data += struct.pack(">H", 16)
    data += b"JFIF\x00\x01\x01\x00"
    data += struct.pack(">HH", 1, 1)
    data += b"\x00\x00\xff\xd9"

    no_ext_file = IMAGE_DIR / "test_jpeg_no_ext"
    no_ext_file.write_bytes(data)
    try:
        result = puremagic.from_file(no_ext_file, mime=True)
        assert result == "image/jpeg", f"Expected image/jpeg, got {result}"
    finally:
        no_ext_file.unlink()


def test_sndhdr_scanner():
    # Test the sndhdr scanner with sndr file
    sndr_file = AUDIO_DIR / "test.sndr"
    with open(sndr_file, "rb") as f:
        head = f.read(512)
    result = sndhdr_scanner.main(None, head, None)
    puremagic.magic_file(sndr_file)
    assert result is not None
    assert result.extension == ".sndr"
    assert result.name.startswith("Macintosh SNDR Resource")
    assert result.mime_type == "audio/x-sndr"
    assert result.confidence == 0.1


def test_ooxml_content_type_detection():
    # GH #146: All OOXML files should be detected with correct extension and MIME type
    expected = {
        "test.docx": (".docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        "test.docm": (".docm", "application/vnd.ms-word.document.macroEnabled.12"),
        "test.dotx": (".dotx", "application/vnd.openxmlformats-officedocument.wordprocessingml.template"),
        "test.dotm": (".dotm", "application/vnd.ms-word.template.macroEnabled.12"),
        "test.xlsx": (".xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        "test.xlsm": (".xlsm", "application/vnd.ms-excel.sheet.macroEnabled.12"),
        "test.xlsb": (".xlsb", "application/vnd.ms-excel.sheet.binary.macroEnabled.12"),
        "test.xltx": (".xltx", "application/vnd.openxmlformats-officedocument.spreadsheetml.template"),
        "test.xltm": (".xltm", "application/vnd.ms-excel.template.macroEnabled.12"),
        "test.pptx": (".pptx", "application/vnd.openxmlformats-officedocument.presentationml.presentation"),
        "test.pptm": (".pptm", "application/vnd.ms-powerpoint.presentation.macroEnabled.12"),
        "test.potx": (".potx", "application/vnd.openxmlformats-officedocument.presentationml.template"),
        "test.potm": (".potm", "application/vnd.ms-powerpoint.template.macroEnabled.12"),
    }
    for filename, (exp_ext, exp_mime) in expected.items():
        filepath = os.path.join(OFFICE_DIR, filename)
        ext = puremagic.from_file(filepath)
        mime = puremagic.from_file(filepath, mime=True)
        assert ext == exp_ext, f"{filename}: expected ext {exp_ext}, got {ext}"
        assert mime == exp_mime, f"{filename}: expected mime {exp_mime}, got {mime}"


def test_ooxml_without_app_xml():
    # GH #146: OOXML files without docProps/app.xml should still be detected
    # (e.g., Google Docs exports)
    content_types = b"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Override PartName="/word/document.xml"
  ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>"""

    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
        with ZipFile(f, "w") as zf:
            zf.writestr("[Content_Types].xml", content_types)
            zf.writestr("word/document.xml", "<w:document/>")
        tmppath = f.name

    try:
        ext = puremagic.from_file(tmppath)
        assert ext == ".docx"
        mime = puremagic.from_file(tmppath, mime=True)
        assert mime == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    finally:
        os.unlink(tmppath)


def test_ooxml_libreoffice_application():
    # GH #146: OOXML files with non-Microsoft Application tag should still be detected
    content_types = b"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Override PartName="/xl/workbook.xml"
  ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
</Types>"""

    app_xml = b"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">
<Application>LibreOffice/24.8.5.2</Application>
</Properties>"""

    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        with ZipFile(f, "w") as zf:
            zf.writestr("[Content_Types].xml", content_types)
            zf.writestr("docProps/app.xml", app_xml)
            zf.writestr("xl/workbook.xml", "<workbook/>")
        tmppath = f.name

    try:
        ext = puremagic.from_file(tmppath)
        assert ext == ".xlsx"
        mime = puremagic.from_file(tmppath, mime=True)
        assert mime == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    finally:
        os.unlink(tmppath)


def _make_ogg_bos_page(codec_id: bytes) -> bytes:
    """Build a minimal Ogg beginning-of-stream page with the given codec ID payload."""
    # OggS capture pattern + version 0 + BOS header type
    header = b"OggS\x00\x02"
    # granule(8) + serial(4) + page_seq(4) + crc(4) = 20 bytes
    header += b"\x00" * 20
    # 1 segment, segment size = len(codec_id)
    header += bytes([1, len(codec_id)])
    return header + codec_id


def test_ogg_opus_scanner():
    opus_file = AUDIO_DIR / "test.opus"
    results = puremagic.magic_file(opus_file)
    assert results[0].extension == ".opus"
    assert results[0].mime_type == "audio/ogg"
    assert results[0].name == "Ogg Opus Audio"


def test_ogg_vorbis_scanner():
    ogg_file = AUDIO_DIR / "test.ogg"
    results = puremagic.magic_file(ogg_file)
    assert results[0].extension == ".ogg"
    assert results[0].mime_type == "audio/ogg"
    assert results[0].name == "Ogg Vorbis Audio"


def test_ogg_theora_scanner():
    ogv_file = VIDEO_DIR / "test.ogv"
    results = puremagic.magic_file(ogv_file)
    assert results[0].extension == ".ogv"
    assert results[0].mime_type == "video/ogg"
    assert results[0].name == "Ogg Theora Video"


def test_ogg_flac_scanner():
    oga_file = AUDIO_DIR / "test.oga"
    results = puremagic.magic_file(oga_file)
    assert results[0].extension == ".oga"
    assert results[0].mime_type == "audio/ogg"
    assert results[0].name == "Ogg FLAC Audio"


def test_ogg_scanner_direct():
    from puremagic.scanners import ogg_scanner

    # Test all codecs via real files
    for path, expected_ext in [
        (AUDIO_DIR / "test.opus", ".opus"),
        (AUDIO_DIR / "test.ogg", ".ogg"),
        (VIDEO_DIR / "test.ogv", ".ogv"),
        (AUDIO_DIR / "test.oga", ".oga"),
    ]:
        with open(path, "rb") as f:
            head = f.read(256)
        result = ogg_scanner.main(path, head, b"")
        assert result is not None, f"{path}: expected {expected_ext}, got None"
        assert result.extension == expected_ext, f"{path}: expected {expected_ext}, got {result.extension}"
        assert result.confidence == 0.9


def test_ogg_scanner_synthetic_codecs():
    """Test codec detection for formats without real test files (Speex, Annodex, OGM)."""
    from puremagic.scanners import ogg_scanner

    cases = [
        (b"Speex   ", ".spx", "Ogg Speex Audio", "audio/ogg"),
        (b"fishead\x00", ".ogv", "Ogg Annodex", "video/ogg"),
        (b"\x01video\x00\x00\x00", ".ogm", "OGM Video", "video/x-ogm+ogg"),
    ]
    for codec_id, expected_ext, expected_name, expected_mime in cases:
        head = _make_ogg_bos_page(codec_id)
        result = ogg_scanner.main(Path("fake.ogg"), head, b"")
        assert result is not None, f"codec {codec_id!r}: expected {expected_ext}, got None"
        assert result.extension == expected_ext
        assert result.name == expected_name
        assert result.mime_type == expected_mime
        assert result.confidence == 0.9


def test_ogg_scanner_rejects_non_ogg():
    from puremagic.scanners import ogg_scanner

    assert ogg_scanner.main(Path("fake.ogg"), b"not ogg data at all", b"") is None
    assert ogg_scanner.main(Path("fake.ogg"), b"", b"") is None
    # Valid OggS but wrong version
    assert ogg_scanner.main(Path("fake.ogg"), b"OggS\x01\x02" + b"\x00" * 50, b"") is None
    # Valid OggS but not BOS page
    assert ogg_scanner.main(Path("fake.ogg"), b"OggS\x00\x00" + b"\x00" * 50, b"") is None
    # Valid BOS page but unknown codec
    head = _make_ogg_bos_page(b"UnknownCodecXYZ")
    assert ogg_scanner.main(Path("fake.ogg"), head, b"") is None


def test_asf_wmv_scanner():
    wmv_file = VIDEO_DIR / "test.wmv"
    results = puremagic.magic_file(wmv_file)
    assert results[0].extension == ".wmv"
    assert results[0].mime_type == "video/x-ms-wmv"
    assert results[0].name == "Windows Media Video"


def test_asf_wma_scanner():
    wma_file = AUDIO_DIR / "test.wma"
    results = puremagic.magic_file(wma_file)
    assert results[0].extension == ".wma"
    assert results[0].mime_type == "audio/x-ms-wma"
    assert results[0].name == "Windows Media Audio"


def test_asf_scanner_direct():
    from puremagic.scanners import asf_scanner

    # WMV (has video)
    wmv_file = VIDEO_DIR / "test.wmv"
    with open(wmv_file, "rb") as f:
        head = f.read(256)
    result = asf_scanner.main(wmv_file, head, b"")
    assert result is not None
    assert result.extension == ".wmv"
    assert result.mime_type == "video/x-ms-wmv"

    # WMA (audio only)
    wma_file = AUDIO_DIR / "test.wma"
    with open(wma_file, "rb") as f:
        head = f.read(256)
    result = asf_scanner.main(wma_file, head, b"")
    assert result is not None
    assert result.extension == ".wma"
    assert result.mime_type == "audio/x-ms-wma"


def test_asf_scanner_generic_fallback():
    """ASF with no recognized stream types should return .asf."""
    import struct
    from puremagic.scanners import asf_scanner

    # Build minimal ASF header: GUID(16) + size(8) + count(4) + reserved(2) = 30 bytes
    # With 0 sub-objects so no streams are found
    header_guid = asf_scanner.match_bytes
    header_size = struct.pack("<Q", 30)
    obj_count = struct.pack("<I", 0)
    reserved = b"\x01\x02"
    data = header_guid + header_size + obj_count + reserved
    result = asf_scanner.main(Path("fake.asf"), data, b"")
    assert result is not None
    assert result.extension == ".asf"
    assert result.mime_type == "video/x-ms-asf"
    assert result.name == "Advanced Systems Format"


def test_asf_scanner_rejects_non_asf():
    from puremagic.scanners import asf_scanner

    assert asf_scanner.main(Path("fake.wmv"), b"not asf data", b"") is None
    assert asf_scanner.main(Path("fake.wmv"), b"", b"") is None


def test_ebml_matroska_scanner():
    mkv_file = VIDEO_DIR / "test.mkv"
    results = puremagic.magic_file(mkv_file)
    assert results[0].extension == ".mkv"
    assert results[0].mime_type == "video/x-matroska"
    assert results[0].name == "Matroska Video"


def test_ebml_webm_scanner():
    webm_file = VIDEO_DIR / "test.webm"
    results = puremagic.magic_file(webm_file)
    assert results[0].extension == ".webm"
    assert results[0].mime_type == "video/webm"
    assert results[0].name == "WebM Video"


def test_ebml_scanner_direct():
    # Test the scanner directly with raw head bytes
    from puremagic.scanners import ebml_scanner

    mkv_file = VIDEO_DIR / "test.mkv"
    with open(mkv_file, "rb") as f:
        head = f.read(64)
    result = ebml_scanner.main(mkv_file, head, b"")
    assert result is not None
    assert result.extension == ".mkv"
    assert result.mime_type == "video/x-matroska"

    webm_file = VIDEO_DIR / "test.webm"
    with open(webm_file, "rb") as f:
        head = f.read(64)
    result = ebml_scanner.main(webm_file, head, b"")
    assert result is not None
    assert result.extension == ".webm"
    assert result.mime_type == "video/webm"


def test_ebml_scanner_rejects_non_ebml():
    from puremagic.scanners import ebml_scanner

    assert ebml_scanner.main(Path("fake.mkv"), b"not an ebml file", b"") is None
    assert ebml_scanner.main(Path("fake.mkv"), b"\x1a\x45\xdf\xa3" + b"\x00" * 60, b"") is None
    assert ebml_scanner.main(Path("fake.mkv"), b"", b"") is None


# ── Bug fix tests ─────────────────────────────────────────────────────


def test_text_scanner_null_bytes_are_binary():
    """Text scanner should treat files with NUL bytes as binary data, not text."""
    bin_file = SYSTEM_DIR / "test_nulls.bin"
    bin_file.write_bytes(b"Hello\x00World\x00" + b"\x00" * 100)
    try:
        results = puremagic.magic_file(bin_file)
        assert results[0].mime_type == "application/octet-stream"
        assert results[0].extension != ".txt"
    finally:
        bin_file.unlink()


# ── Easy tier coverage tests ──────────────────────────────────────────


def test_ogg_scanner_truncated_head():
    """ogg_scanner line 32: payload_start >= len(head)."""
    from puremagic.scanners import ogg_scanner

    # Valid OggS BOS header with seg_count=200 → payload_start=227, but head is only 50 bytes
    head = bytearray(50)
    head[0:4] = b"OggS"
    head[4] = 0  # version
    head[5] = 0x02  # BOS flag
    head[26] = 200  # seg_count → payload at offset 227
    assert ogg_scanner.main(Path("fake.ogg"), bytes(head), b"") is None


def test_json_scanner_array():
    """json_scanner: valid JSON array file."""
    json_file = SYSTEM_DIR / "test_array.json"
    json_file.write_bytes(b"[1, 2, 3]")
    try:
        result = json_scanner.main(json_file, b"[1, 2, 3]", b"[1, 2, 3]")
        assert result is not None
        assert result.extension == ".json"
    finally:
        json_file.unlink()


def test_json_scanner_malformed():
    """json_scanner lines 17-18: passes structural check but fails json.load()."""
    json_file = SYSTEM_DIR / "test_bad.json"
    json_file.write_bytes(b"{invalid json content}")
    try:
        result = json_scanner.main(json_file, b"{invalid json content}", b"{invalid json content}")
        assert result is None
    finally:
        json_file.unlink()


def test_sndhdr_hcom_detection():
    """sndhdr_scanner line 25: HCOM format detected via FSSD+HCOM markers."""
    from puremagic.scanners import sndhdr_scanner

    head = bytearray(133)
    head[65:69] = b"FSSD"
    head[128:132] = b"HCOM"
    result = sndhdr_scanner.main(None, bytes(head), None)
    assert result is not None
    assert result.extension == ".hcom"
    assert result.mime_type == "audio/x-hcom"
    assert result.confidence == 1.0


def test_sndhdr_short_head():
    """sndhdr_scanner lines 44-45: head too short for struct.unpack."""
    from puremagic.scanners import sndhdr_scanner

    # 2 bytes is too short for get_short_le(head[2:4])
    result = sndhdr_scanner.main(None, b"\x00\x00", None)
    # Should not crash — except catches IndexError, then test_hcom also fails (head too short)
    # test_hcom will raise IndexError on head[65:69] check but that returns None since slicing doesn't raise
    assert result is None


def test_asf_scanner_wrong_magic_30_bytes():
    """asf_scanner line 18: 30+ bytes but wrong magic."""
    from puremagic.scanners import asf_scanner

    assert asf_scanner.main(Path("fake.asf"), b"\x00" * 30, b"") is None


def test_asf_scanner_file_io_error():
    """asf_scanner lines 28-29: OSError when header_size > len(head) and file doesn't exist."""
    import struct
    from puremagic.scanners import asf_scanner

    # Valid ASF magic + header_size=99999 (much larger than head) + obj_count=0
    head = asf_scanner.match_bytes
    head += struct.pack("<Q", 99999)  # header_size
    head += struct.pack("<I", 0)  # obj_count
    head += b"\x01\x02"  # reserved
    assert asf_scanner.main(Path("/nonexistent/path/fake.asf"), head, b"") is None


def test_asf_scanner_truncated_object():
    """asf_scanner line 39: break when offset + 24 > len(data)."""
    import struct
    from puremagic.scanners import asf_scanner

    # Valid header with obj_count=1 but no actual object data after the header
    head = asf_scanner.match_bytes  # 16 bytes
    head += struct.pack("<Q", 30)  # header_size = 30 (fits in head)
    head += struct.pack("<I", 1)  # obj_count = 1 (but no object data follows)
    head += b"\x01\x02"  # reserved
    # Total = 30 bytes, offset starts at 30, but offset+24=54 > 30 → break
    result = asf_scanner.main(Path("fake.asf"), head, b"")
    assert result is not None
    assert result.extension == ".asf"  # Falls through to generic ASF


def test_asf_scanner_bad_object_size():
    """asf_scanner line 43: break when obj_size < 24."""
    import struct
    from puremagic.scanners import asf_scanner

    header_body = struct.pack("<I", 1) + b"\x01\x02"  # obj_count=1, reserved
    # Object with GUID(16 bytes of 0xFF) + size=0 (invalid)
    obj = b"\xff" * 16 + struct.pack("<Q", 0)
    data = asf_scanner.match_bytes + struct.pack("<Q", 30 + len(obj)) + header_body + obj
    result = asf_scanner.main(Path("fake.asf"), data, b"")
    assert result is not None
    assert result.extension == ".asf"  # Falls through to generic ASF


# ── Medium tier: python_scanner coverage ──────────────────────────────


def test_python_scanner_large_file():
    """python_scanner line 43: files > 1MB return None."""
    large_file = SYSTEM_DIR / "test_large.py"
    large_file.write_bytes(b"import os\n" * 200_000)  # ~2MB
    try:
        result = python_scanner.main(large_file, None, None)
        assert result is None
    finally:
        large_file.unlink()


def test_python_scanner_no_constructs():
    """python_scanner lines 31-37, 54-55: non-.py file that parses as Python but lacks constructs."""
    # This file parses as valid Python (just assignments) but has no imports/defs/control flow
    no_constructs = SYSTEM_DIR / "test_noconstructs.txt"
    no_constructs.write_bytes(b"a = 1\nb = 2\nc = 3\nd = 4\ne = 5\nf = 6\ng = 7\n" * 20)
    try:
        result = python_scanner.main(no_constructs, None, None)
        assert result is None
    finally:
        no_constructs.unlink()


def test_python_scanner_few_constructs():
    """python_scanner lines 34-37: non-.py with some constructs but below threshold of 4."""
    few_file = SYSTEM_DIR / "test_few.txt"
    # Only 2 imports + padding to exceed 100 byte minimum — below threshold of 4 constructs
    few_file.write_bytes(b"import os\nimport sys\nx = 1\ny = 2\n" + b"z = 0\n" * 30)
    try:
        result = python_scanner.main(few_file, None, None)
        assert result is None
    finally:
        few_file.unlink()


# ── Medium tier: main.py coverage ─────────────────────────────────────


def test_deepscan_disabled_magic_file(monkeypatch):
    """main.py line 351: magic_file returns without deep scan when PUREMAGIC_DEEPSCAN=0."""
    monkeypatch.setenv("PUREMAGIC_DEEPSCAN", "0")
    # Force reimport so the env var takes effect at module level
    # But scanners are imported at module load time; the env check is in run_deep_scan/single_deep_scan
    results = puremagic.magic_file(OFFICE_DIR / "test.docx")
    # Without deep scan, all OOXML formats share the same PK magic bytes
    assert len(results) > 1  # Multiple matches, not narrowed by scanner


def test_deepscan_disabled_magic_stream(monkeypatch):
    """main.py line 395: magic_stream returns without deep scan when PUREMAGIC_DEEPSCAN=0."""
    monkeypatch.setenv("PUREMAGIC_DEEPSCAN", "0")
    with open(OFFICE_DIR / "test.docx", "rb") as f:
        results = puremagic.magic_stream(f, filename=OFFICE_DIR / "test.docx")
    assert len(results) > 1


def test_single_deep_scan_disabled(monkeypatch):
    """main.py line 451: single_deep_scan returns None when PUREMAGIC_DEEPSCAN=0."""
    monkeypatch.setenv("PUREMAGIC_DEEPSCAN", "0")
    result = puremagic.main.single_deep_scan(b"PK\x03\x04", Path("fake.zip"), head=b"\x00", foot=b"\x00")
    assert result is None


def test_single_deep_scan_none_head():
    """main.py line 453: single_deep_scan returns None when head is None."""
    result = puremagic.main.single_deep_scan(b"PK\x03\x04", Path("fake.zip"), head=None, foot=b"\x00")
    assert result is None
    result = puremagic.main.single_deep_scan(b"PK\x03\x04", Path("fake.zip"), head=b"\x00", foot=None)
    assert result is None


def test_catch_all_deep_scan_disabled(monkeypatch):
    """main.py line 498: catch_all_deep_scan returns None when PUREMAGIC_DEEPSCAN=0."""
    monkeypatch.setenv("PUREMAGIC_DEEPSCAN", "0")
    result = puremagic.main.catch_all_deep_scan(Path("fake.txt"), head=b"\x00", foot=b"\x00")
    assert result is None


def test_catch_all_deep_scan_none_head():
    """main.py line 500: catch_all_deep_scan returns None when head is None."""
    result = puremagic.main.catch_all_deep_scan(Path("fake.txt"), head=None, foot=b"\x00")
    assert result is None


def test_file_details_non_regular_file():
    """main.py line 235: file_details raises PureError for directories."""
    import pytest

    with pytest.raises(puremagic.main.PureError, match="Not a regular file"):
        puremagic.main.file_details(SYSTEM_DIR)


def test_magic_file_no_matches():
    """main.py lines 346-347: identify_all raises PureError, caught and info set to []."""
    # File with random bytes that don't match any magic signature
    random_file = SYSTEM_DIR / "test_random.bin"
    random_file.write_bytes(bytes(range(256)) * 4)
    try:
        results = puremagic.magic_file(random_file)
        # Should not raise — either returns results from deep scan or empty-ish list
        assert isinstance(results, list)
    finally:
        random_file.unlink()


def test_run_deep_scan_no_matches_raises(monkeypatch):
    """main.py lines 546-547: run_deep_scan raises PureError when no matches and raise_on_none=True."""
    import pytest
    from puremagic.scanners import text_scanner

    random_file = SYSTEM_DIR / "test_unrecognizable.bin"
    random_file.write_bytes(b"\x00" * 100)
    # Patch catch-all text scanner to return None so we reach the raise
    monkeypatch.setattr(text_scanner, "main", lambda *a, **kw: None)
    try:
        with pytest.raises(puremagic.main.PureError, match="Could not identify file"):
            puremagic.main.run_deep_scan([], random_file, b"\x00" * 40, b"\x00" * 40, raise_on_none=True)
    finally:
        random_file.unlink()


# ── Medium tier: hdf5_scanner coverage ────────────────────────────────


def test_hdf5_scanner_no_subtype():
    """hdf5_scanner lines 46-61: valid HDF5 magic but no matching subtype → None."""
    from puremagic.scanners import hdf5_scanner

    hdf5_file = SYSTEM_DIR / "test_generic.hdf5"
    hdf5_file.write_bytes(b"\x89HDF\r\n\x1a\n" + b"\x00" * 1024)
    try:
        result = hdf5_scanner.main(hdf5_file, b"\x89HDF\r\n\x1a\n" + b"\x00" * 100, b"")
        assert result is None
    finally:
        hdf5_file.unlink()


def test_hdf5_scanner_anndata_match():
    """hdf5_scanner lines 53-58: HDF5 with AnnData signatures → .h5ad."""
    from puremagic.scanners import hdf5_scanner

    # Create file with HDF5 magic + group paths that look like AnnData
    content = b"\x89HDF\r\n\x1a\n" + b"\x00" * 100 + b"/obs" + b"\x00" * 100 + b"/var" + b"\x00" * 100
    hdf5_file = SYSTEM_DIR / "test_anndata.h5ad"
    hdf5_file.write_bytes(content)
    try:
        result = hdf5_scanner.main(hdf5_file, content[:20], b"")
        assert result is not None
        assert result.extension == ".h5ad"
        assert result.name == "AnnData"
        assert result.confidence == 0.9
    finally:
        hdf5_file.unlink()


# ── Medium tier: cfbf_scanner coverage ────────────────────────────────


def test_cfbf_extract_stream_names_incomplete_entry():
    """cfbf_scanner line 60: break on incomplete trailing entry."""
    from puremagic.scanners.cfbf_scanner import _extract_stream_names

    # One valid 128-byte entry + 50 bytes of trailing garbage
    entry = bytearray(128)
    name = "TestStream".encode("utf-16-le") + b"\x00\x00"
    entry[: len(name)] = name
    import struct

    struct.pack_into("<H", entry, 64, len(name))
    entry[66] = 2  # obj_type = stream
    dir_data = bytes(entry) + b"\x00" * 50  # trailing incomplete entry
    names = _extract_stream_names(dir_data)
    assert "TestStream" in names


def test_cfbf_extract_stream_names_invalid_obj_type():
    """cfbf_scanner line 67: skip entries with invalid obj_type."""
    from puremagic.scanners.cfbf_scanner import _extract_stream_names

    import struct

    entry = bytearray(128)
    name = "SomeStream".encode("utf-16-le") + b"\x00\x00"
    entry[: len(name)] = name
    struct.pack_into("<H", entry, 64, len(name))
    entry[66] = 3  # invalid obj_type
    names = _extract_stream_names(bytes(entry))
    assert len(names) == 0


def test_cfbf_extract_root_clsid():
    """cfbf_scanner lines 76-82: extract CLSID from root entry."""
    from puremagic.scanners.cfbf_scanner import _extract_root_clsid

    # Entry with obj_type=5 (root) and CLSID at bytes 80-96
    entry = bytearray(128)
    entry[66] = 5  # root storage
    clsid = b"\x3a\x8f\xb7\x74\xc8\xc8\xd1\x11\xbe\x11\x00\xc0\x4f\xb6\xfa\xf1"
    entry[80:96] = clsid
    result = _extract_root_clsid(bytes(entry))
    assert result == clsid


def test_cfbf_extract_root_clsid_no_root():
    """cfbf_scanner line 82: no root entry → None."""
    from puremagic.scanners.cfbf_scanner import _extract_root_clsid

    # Entry with obj_type=2 (stream, not root)
    entry = bytearray(128)
    entry[66] = 2
    assert _extract_root_clsid(bytes(entry)) is None


def test_cfbf_extract_root_clsid_short_entry():
    """cfbf_scanner line 78: entry < 96 bytes → break."""
    from puremagic.scanners.cfbf_scanner import _extract_root_clsid

    assert _extract_root_clsid(b"\x00" * 50) is None


def test_cfbf_identify_format_msi():
    """cfbf_scanner lines 99-101: multi-stream MSI match."""
    from puremagic.scanners.cfbf_scanner import _identify_format

    stream_names = {"_StringPool", "_StringData", "SomeOtherStream"}
    # dir_data with no root entry (obj_type=2)
    entry = bytearray(128)
    entry[66] = 2
    result = _identify_format(stream_names, bytes(entry))
    assert result is not None
    assert result.extension == ".msi"
    assert result.mime_type == "application/x-msi"


def test_cfbf_identify_format_mpp():
    """cfbf_scanner lines 104-108: CLSID MPP match."""
    from puremagic.scanners.cfbf_scanner import _identify_format

    # No matching stream names, but root CLSID matches Project
    entry = bytearray(128)
    entry[66] = 5  # root storage
    entry[80:96] = b"\x3a\x8f\xb7\x74\xc8\xc8\xd1\x11\xbe\x11\x00\xc0\x4f\xb6\xfa\xf1"
    result = _identify_format(set(), bytes(entry))
    assert result is not None
    assert result.extension == ".mpp"
    assert result.mime_type == "application/vnd.ms-project"


def test_cfbf_identify_format_no_match():
    """cfbf_scanner line 110: no match → None."""
    from puremagic.scanners.cfbf_scanner import _identify_format

    entry = bytearray(128)
    entry[66] = 2  # stream, not root
    result = _identify_format({"SomeRandomStream"}, bytes(entry))
    assert result is None


def test_cfbf_main_short_head():
    """cfbf_scanner line 115: head < 76 bytes → None."""
    from puremagic.scanners import cfbf_scanner

    assert cfbf_scanner.main(Path("fake.doc"), b"\xd0\xcf\x11\xe0" + b"\x00" * 30, b"") is None


def test_cfbf_main_wrong_magic():
    """cfbf_scanner lines 119-120: neither full nor short magic → None."""
    from puremagic.scanners import cfbf_scanner

    assert cfbf_scanner.main(Path("fake.doc"), b"\x00" * 76, b"") is None


def test_cfbf_main_bad_sector_shift():
    """cfbf_scanner line 125: sector_shift not 9 or 12 → None."""
    import struct
    from puremagic.scanners import cfbf_scanner

    head = bytearray(76)
    head[0:8] = cfbf_scanner.match_bytes
    struct.pack_into("<H", head, 30, 10)  # invalid sector_shift
    assert cfbf_scanner.main(Path("fake.doc"), bytes(head), b"") is None


def test_cfbf_main_negative_dir_secid():
    """cfbf_scanner line 130: first_dir_secid < 0 → None."""
    import struct
    from puremagic.scanners import cfbf_scanner

    head = bytearray(76)
    head[0:8] = cfbf_scanner.match_bytes
    struct.pack_into("<H", head, 30, 9)  # valid sector_shift
    struct.pack_into("<i", head, 48, -1)  # negative secid
    assert cfbf_scanner.main(Path("fake.doc"), bytes(head), b"") is None


def test_cfbf_main_file_read_error():
    """cfbf_scanner lines 139-140: OSError reading directory sector."""
    import struct
    from puremagic.scanners import cfbf_scanner

    head = bytearray(76)
    head[0:8] = cfbf_scanner.match_bytes
    struct.pack_into("<H", head, 30, 9)  # sector_shift=9 → sector_size=512
    struct.pack_into("<i", head, 48, 0)  # dir at sector 0 → offset 512
    assert cfbf_scanner.main(Path("/nonexistent/path.doc"), bytes(head), b"") is None


def test_cfbf_main_empty_dir_data():
    """cfbf_scanner line 143: empty dir_data → None."""
    import struct
    from puremagic.scanners import cfbf_scanner

    # Create a tiny file with valid CFBF header but too small to contain directory sector
    head = bytearray(76)
    head[0:8] = cfbf_scanner.match_bytes
    struct.pack_into("<H", head, 30, 9)  # sector_shift=9 → sector_size=512
    struct.pack_into("<i", head, 48, 100)  # dir at sector 100 → offset 51712 (way past end)

    tiny_file = SYSTEM_DIR / "test_tiny.cfbf"
    tiny_file.write_bytes(bytes(head))
    try:
        result = cfbf_scanner.main(tiny_file, bytes(head), b"")
        assert result is None
    finally:
        tiny_file.unlink()
