import csv

import pytest

import puremagic
from puremagic.scanners.text_scanner import csv_check


@pytest.mark.parametrize(
    "text",
    [
        'product,description\nwidget,"red, green"\n',
        'product,description\nwidget,"red\nand green"\n',
        'product,description\nwidget,"say ""hello, world"""\n',
        'product;description\nwidget;"red; green"\n',
        'product\tdescription\nwidget\t"red\tgreen"\n',
        'product;description\nwidget;"say ""hi; there"""\n',
        'id,name,note\n1,"Smith, J","said ""no, thanks"""\n2,Doe,"plain"\n3,"Lee, K",""""\n',
    ],
)
def test_quoted_csv_is_recognized(tmp_path, text):
    path = tmp_path / "report.csv"
    path.write_text(text, encoding="utf-8")
    assert puremagic.from_file(path, mime=True) == "text/csv"


@pytest.mark.parametrize("text", ["a,b\n1,2,3\n", "hello world\nnothing else\n"])
def test_inconsistent_or_non_csv_text_is_rejected(text):
    assert csv_check("report.csv", text) is None


def test_parser_field_limit_preserves_unquoted_csv_detection():
    limit = csv.field_size_limit(10)
    try:
        result = csv_check("report.csv", "product,description\nwidget,brightly_colored\n")
    finally:
        csv.field_size_limit(limit)
    assert result is not None and result.mime_type == "text/csv"


@pytest.mark.parametrize(
    "text",
    [
        # Many short rows
        "id,name,value\n" + "".join(f"{i},name{i},{i * 3}\n" for i in range(5000)),
        # A few very long rows, like the HTML-as-.xls export in #152
        "\n".join(",".join(f"cell{i}x{j}" for j in range(20000)) for i in range(5)),
    ],
)
def test_sniffer_sample_is_bounded(monkeypatch, text):
    """#152 csv.Sniffer is slow on large input, so only a bounded sample may be passed to it"""
    samples = []
    original_sniff = csv.Sniffer.sniff

    def recording_sniff(self, sample, delimiters=None):
        samples.append(sample)
        return original_sniff(self, sample, delimiters)

    monkeypatch.setattr(csv.Sniffer, "sniff", recording_sniff)
    result = csv_check("data.csv", text)
    assert samples, "csv.Sniffer was not called"
    assert all(len(s) <= 8192 and s.count("\n") < 50 for s in samples)
    assert result is not None and result.mime_type == "text/csv"


def test_uppercase_html_tag_detected(tmp_path):
    """#152 HTML starting with an uppercase <HTML tag is identified as HTML"""
    path = tmp_path / "export.dat"
    path.write_bytes(
        b"<HTML>\n<HEAD><TITLE>t</TITLE></HEAD>\n<BODY><TABLE><TR><TD>a</TD></TR></TABLE></BODY>\n</HTML>\n"
    )
    assert puremagic.from_file(path, mime=True) == "text/html"
