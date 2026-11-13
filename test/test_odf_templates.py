from zipfile import ZipFile

import pytest

import puremagic


@pytest.mark.parametrize("filename_suffix", [None, "", ".zip", ".odt"])
@pytest.mark.parametrize(
    ("media_subtype", "extension"),
    [
        ("text-template", ".ott"),
        ("spreadsheet-template", ".ots"),
        ("presentation-template", ".otp"),
        ("text", ".odt"),
        ("spreadsheet", ".ods"),
        ("presentation", ".odp"),
    ],
)
def test_odf_mimetype_detection(tmp_path, filename_suffix, media_subtype, extension):
    suffix = extension if filename_suffix is None else filename_suffix
    filename = tmp_path / f"document{suffix}"
    mime_type = f"application/vnd.oasis.opendocument.{media_subtype}"
    with ZipFile(filename, "w") as archive:
        # The scanner only needs the package's declared type and content entry.
        archive.writestr("mimetype", mime_type)
        archive.writestr("content.xml", b"<document/>")

    assert puremagic.from_file(filename) == extension
    assert puremagic.from_file(filename, mime=True) == mime_type
    result = puremagic.magic_file(filename)[0]
    assert result.extension == extension
    assert result.mime_type == mime_type
