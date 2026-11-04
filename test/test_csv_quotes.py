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
