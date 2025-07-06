#!/usr/bin/env python
"""
puremagic is a pure python module that will identify a file based off it's
magic numbers. It is designed to be minimalistic and inherently cross-platform
compatible, with no imports when used as a module.

© 2013-2025 Chris Griffith - License: MIT (see LICENSE)

Acknowledgements
Gary C. Kessler
    For use of his File Signature Tables, available at:
    https://filesig.search.org/
"""

import json
import os
from binascii import unhexlify
from collections import namedtuple
from itertools import chain
from pathlib import Path

import puremagic

if os.getenv("PUREMAGIC_DEEPSCAN") != "0":
    from puremagic.scanners import zip_scanner, pdf_scanner, text_scanner, json_scanner, python_scanner, sndhdr_scanner

__author__ = "Chris Griffith"
__version__ = "2.0.0b5"
__all__ = [
    "magic_file",
    "magic_string",
    "magic_stream",
    "from_file",
    "from_string",
    "from_stream",
    "ext_from_filename",
    "PureError",
    "PureMagic",
    "PureMagicWithConfidence",
]

here = os.path.abspath(os.path.dirname(__file__))

PureMagic = namedtuple(
    "PureMagic",
    (
        "byte_match",
        "offset",
        "extension",
        "mime_type",
        "name",
    ),
)
PureMagicWithConfidence = namedtuple(
    "PureMagicWithConfidence",
    (
        "byte_match",
        "offset",
        "extension",
        "mime_type",
        "name",
        "confidence",
    ),
)


class PureError(LookupError):
    """Do not have that type of file in our databanks"""


class PureValueError(ValueError):
    """Invalid input"""


def magic_data(
    filename: os.PathLike | str = os.path.join(here, "magic_data.json"),
) -> tuple[list[PureMagic], list[PureMagic], list[PureMagic], dict[bytes, list[PureMagic]]]:
    """Read the magic file"""
    with open(filename, encoding="utf-8") as f:
        data = json.load(f)
    headers = sorted((create_puremagic(x) for x in data["headers"]), key=lambda x: x.byte_match)
    footers = sorted((create_puremagic(x) for x in data["footers"]), key=lambda x: x.byte_match)
    extensions = [create_puremagic(x) for x in data["extension_only"]]
    multi_part_extensions = {}
    for file_match, option_list in data["multi-part"].items():
        multi_part_extensions[unhexlify(file_match.encode("ascii"))] = [create_puremagic(x) for x in option_list]
    return headers, footers, extensions, multi_part_extensions


def create_puremagic(x: list) -> PureMagic:
    return PureMagic(
        byte_match=unhexlify(x[0].encode("ascii")),
        offset=x[1],
        extension=x[2],
        mime_type=x[3],
        name=x[4],
    )


magic_header_array, magic_footer_array, extension_only_array, multi_part_dict = magic_data()


def get_max_lengths() -> tuple[int, int]:
    """The length of the largest magic string + its offset"""
    max_header_length = max([len(x.byte_match) + x.offset for x in magic_header_array])
    max_footer_length = max([len(x.byte_match) + abs(x.offset) for x in magic_footer_array])

    for options in multi_part_dict.values():
        for option in options:
            if option.offset < 0:
                max_footer_length = max(max_footer_length, len(option.byte_match) + abs(option.offset))
            else:
                max_header_length = max(max_header_length, len(option.byte_match) + option.offset)

    return max_header_length, max_footer_length


max_head, max_foot = get_max_lengths()


def determine_confidence(matches, ext=None) -> list[PureMagicWithConfidence]:
    """Rough confidence based on string length and file extension"""
    results = []
    for match in matches:
        con = 0.8 if len(match.byte_match) >= 9 else float(f"0.{len(match.byte_match)}")
        if con >= 0.1 and ext and ext == match.extension:
            con = 0.9
        results.append(PureMagicWithConfidence(confidence=con, **match._asdict()))

    if not results and ext:
        results = [
            PureMagicWithConfidence(confidence=0.1, **magic_row._asdict())
            for magic_row in extension_only_array
            if ext == magic_row.extension
        ]

    return sorted(results, key=lambda x: (x.confidence, len(x.byte_match)), reverse=True)


def identify_all(header: bytes, footer: bytes, ext=None) -> list[PureMagicWithConfidence]:
    """Attempt to identify 'data' by its magic numbers"""

    # Capture the length of the data
    # That way we do not try to identify bytes that don't exist
    matches = []
    for magic_row in magic_header_array:
        start = magic_row.offset
        end = magic_row.offset + len(magic_row.byte_match)
        if end > len(header):
            continue
        if header[start:end] == magic_row.byte_match:
            matches.append(magic_row)

    for magic_row in magic_footer_array:
        start = magic_row.offset
        end = magic_row.offset + len(magic_row.byte_match)
        match_area = footer[start:end] if end != 0 else footer[start:]
        if match_area == magic_row.byte_match:
            matches.append(magic_row)

    new_matches = set()
    for matched in matches:
        if matched.byte_match in multi_part_dict:
            for magic_row in multi_part_dict[matched.byte_match]:
                start = magic_row.offset
                end = magic_row.offset + len(magic_row.byte_match)
                if magic_row.offset < 0:
                    match_area = footer[start:end] if end != 0 else footer[start:]
                    if match_area == magic_row.byte_match:
                        new_matches.add(
                            PureMagic(
                                byte_match=matched.byte_match + magic_row.byte_match,
                                offset=magic_row.offset,
                                extension=magic_row.extension,
                                mime_type=magic_row.mime_type,
                                name=magic_row.name,
                            )
                        )
                else:
                    if end > len(header):
                        continue
                    if header[start:end] == magic_row.byte_match:
                        new_matches.add(
                            PureMagic(
                                byte_match=header[matched.offset : end],
                                offset=magic_row.offset,
                                extension=magic_row.extension,
                                mime_type=magic_row.mime_type,
                                name=magic_row.name,
                            )
                        )

    matches.extend(list(new_matches))
    return determine_confidence(matches, ext)


def perform_magic(header: bytes, footer: bytes, mime: bool, ext=None, filename=None) -> str:
    """Discover what type of file it is based on the incoming string"""
    if not header:
        raise PureValueError("Input was empty")
    infos = identify_all(header, footer, ext)
    if filename and os.getenv("PUREMAGIC_DEEPSCAN") != "0":
        results = run_deep_scan(infos, filename, header, footer, raise_on_none=True)
        if results:
            if results[0].extension == "":
                raise PureError("Could not identify file")
            if mime:
                return results[0].mime_type
            return results[0].extension
    if not infos:
        raise PureError("Could not identify file")
    info = infos[0]
    if mime:
        return info.mime_type
    return info.extension if not isinstance(info.extension, list) else info[0].extension


def file_details(filename: os.PathLike | str) -> tuple[bytes, bytes]:
    """Grab the start and end of the file"""
    if not os.path.isfile(filename):
        raise PureError("Not a regular file")
    with open(filename, "rb") as fin:
        head = fin.read(max_head)
        try:
            fin.seek(-max_foot, os.SEEK_END)
        except OSError:
            fin.seek(0)
        foot = fin.read()
    return head, foot


def string_details(string):
    """Grab the start and end of the string"""
    return string[:max_head], string[-max_foot:]


def stream_details(stream):
    """Grab the start and end of the stream"""
    head = stream.read(max_head)
    try:
        stream.seek(-max_foot, os.SEEK_END)
    except (OSError, ValueError):  # fsspec throws ValueError
        # File is smaller than the max_foot size, jump to beginning
        stream.seek(0)
    foot = stream.read()
    stream.seek(0)
    return head, foot


def ext_from_filename(filename: os.PathLike | str) -> str:
    """Scan a filename for its extension.

    :param filename: string of the filename
    :return: the extension off the end (empty string if it can't find one)
    """
    try:
        base, ext = str(filename).lower().rsplit(".", 1)
    except ValueError:
        return ""
    ext = f".{ext}"
    all_exts = [x.extension for x in chain(magic_header_array, magic_footer_array)]

    if base[-4:].startswith("."):
        # For double extensions like .tar.gz
        long_ext = base[-4:] + ext
        if long_ext in all_exts:
            return long_ext
    return ext


def from_file(filename: os.PathLike | str, mime: bool = False) -> str:
    """Opens file, attempts to identify content based
    off magic number and will return the file extension.
    If mime is True it will return the mime type instead.

    :param filename: path to file
    :param mime: Return mime, not extension
    :return: guessed extension or mime
    """

    head, foot = file_details(filename)
    return perform_magic(head, foot, mime, ext_from_filename(filename), filename=filename)


def from_string(string: str | bytes, mime: bool = False, filename: os.PathLike | str | None = None) -> str:
    """Reads in string, attempts to identify content based
    off magic number and will return the file extension.
    If mime is True it will return the mime type instead.
    If filename is provided it will be used in the computation.

    :param string: string representation to check
    :param mime: Return mime, not extension
    :param filename: original filename
    :return: guessed extension or mime
    """
    if isinstance(string, str):
        string = string.encode("utf-8")
    head, foot = string_details(string)
    ext = ext_from_filename(filename) if filename else None
    return perform_magic(head, foot, mime, ext)


def from_stream(stream, mime: bool = False, filename: os.PathLike | str | None = None) -> str:
    """Reads in stream, attempts to identify content based
    off magic number and will return the file extension.
    If mime is True it will return the mime type instead.
    If filename is provided it will be used in the computation.

    :param stream: stream representation to check
    :param mime: Return mime, not extension
    :param filename: original filename
    :return: guessed extension or mime
    """
    head, foot = stream_details(stream)
    ext = ext_from_filename(filename) if filename else None
    return perform_magic(head, foot, mime, ext)


def magic_file(filename: os.PathLike | str) -> list[PureMagicWithConfidence]:
    """
    Returns list of (num_of_matches, array_of_matches)
    arranged by highest confidence match first.

    :param filename: path to file
    :return: list of possible matches, highest confidence first
    """
    head, foot = file_details(filename)
    if not head:
        raise PureValueError("Input was empty")
    try:
        info = identify_all(head, foot, ext_from_filename(filename))
    except PureError:
        info = []
    info.sort(key=lambda x: x.confidence, reverse=True)
    if os.getenv("PUREMAGIC_DEEPSCAN") != "0":
        return run_deep_scan(info, filename, head, foot, raise_on_none=False)
    return info


def magic_string(string, filename: os.PathLike | str | None = None) -> list[PureMagicWithConfidence]:
    """
    Returns tuple of (num_of_matches, array_of_matches)
    arranged by highest confidence match first
    If filename is provided it will be used in the computation.

    :param string: string representation to check
    :param filename: original filename
    :return: list of possible matches, highest confidence first
    """
    if not string:
        raise PureValueError("Input was empty")
    head, foot = string_details(string)
    ext = ext_from_filename(filename) if filename else None
    info = identify_all(head, foot, ext)
    info.sort(key=lambda x: x.confidence, reverse=True)
    return info


def magic_stream(
    stream,
    filename: os.PathLike | None = None,
) -> list[PureMagicWithConfidence]:
    """Returns tuple of (num_of_matches, array_of_matches)
    arranged by highest confidence match first
    If filename is provided it will be used in the computation.

    :param stream: stream representation to check
    :param filename: original filename
    :return: list of possible matches, highest confidence first
    """
    head, foot = stream_details(stream)
    if not head:
        raise PureValueError("Input was empty")
    ext = ext_from_filename(filename) if filename else None
    info = identify_all(head, foot, ext)
    info.sort(key=lambda x: x.confidence, reverse=True)
    return info


def single_deep_scan(
    bytes_match: bytes | bytearray | None,
    filename: os.PathLike | str,
    head=None,
    foot=None,
    confidence=0,
):
    if os.getenv("PUREMAGIC_DEEPSCAN") == "0":
        return None
    if not isinstance(filename, os.PathLike):
        filename = Path(filename)
    match bytes_match:
        case zip_scanner.match_bytes:
            return zip_scanner.main(filename, head, foot)
        case pdf_scanner.match_bytes:
            return pdf_scanner.main(filename, head, foot)
        case sndhdr_scanner.hcom_match_bytes | sndhdr_scanner.fssd_match_bytes | sndhdr_scanner.sndr_match_bytes:
            # sndr is a loose confidence and other results may be better
            result = sndhdr_scanner.main(filename, head, foot)
            if result and result.confidence > confidence:
                return result

    # The first match wins
    for scanner in (pdf_scanner, python_scanner, json_scanner):
        result = scanner.main(filename, head, foot)
        if result:
            return result
    return None


def catch_all_deep_scan(
    filename: os.PathLike | str,
    head=None,
    foot=None,
):
    if os.getenv("PUREMAGIC_DEEPSCAN") == "0":
        return None
    if not isinstance(filename, os.PathLike):
        filename = Path(filename)
    return text_scanner.main(filename, head, foot)


def run_deep_scan(
    matches: list[PureMagicWithConfidence],
    filename: os.PathLike | str,
    head=None,
    foot=None,
    raise_on_none=True,
):
    if not matches or matches[0].byte_match == b"":
        try:
            result = single_deep_scan(None, filename, head, foot)
        except Exception:
            pass
        else:
            if result:
                return [
                    PureMagicWithConfidence(
                        confidence=result.confidence,
                        byte_match=None,
                        offset=None,
                        extension=result.extension,
                        mime_type=result.mime_type,
                        name=result.name,
                    )
                ]
        try:
            result = catch_all_deep_scan(filename, head, foot)
        except Exception:
            raise
        else:
            if result:
                return [result]
        if raise_on_none:
            raise PureError("Could not identify file")

    for pure_magic_match in matches:
        # noinspection PyBroadException
        try:
            result = single_deep_scan(pure_magic_match.byte_match, filename, head, foot, pure_magic_match.confidence)
        except Exception:
            continue
        if result:
            return [
                PureMagicWithConfidence(
                    confidence=result.confidence,
                    byte_match=pure_magic_match.byte_match,
                    offset=pure_magic_match.offset,
                    extension=result.extension,
                    mime_type=result.mime_type,
                    name=result.name,
                )
            ]
    return matches


def command_line_entry(*args):
    import sys  # noqa: PLC0415
    from argparse import ArgumentParser  # noqa: PLC0415

    parser = ArgumentParser(
        description=(
            """puremagic is a pure python file identification module.
            It looks for matching magic numbers in the file to locate the file type."""
        ),
    )
    parser.add_argument(
        "-m",
        "--mime",
        action="store_true",
        dest="mime",
        help="Return the mime type instead of file type",
    )
    parser.add_argument("-v", "--verbose", action="store_true", dest="verbose", help="Print verbose output")
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--version", action="version", version=puremagic.__version__)
    args = parser.parse_args(args if args else sys.argv[1:])

    for fn in args.files:
        if not fn.exists():
            print(f"File '{fn}' does not exist!")
            continue
        if fn.is_dir():
            for file in fn.iterdir():
                if not file.is_file():
                    continue
                try:
                    print(f"'{file}' : {from_file(file, args.mime)}")
                except (PureError, PureValueError):
                    print(f"'{file}' : could not be Identified")
                    continue
        else:
            try:
                print(f"'{fn}' : {from_file(fn, args.mime)}")
            except (PureError, PureValueError):
                print(f"'{fn}' : could not be Identified")
                continue
        if args.verbose:
            matches = magic_file(fn)
            print(f"Total Possible Matches: {len(matches)}")
            for i, result in enumerate(matches):
                if i == 0:
                    print("\n\tBest Match")
                else:
                    print(f"\tAlternative Match #{i}")
                print(f"\tName: {result.name}")
                print(f"\tConfidence: {int(result.confidence * 100)}%")
                print(f"\tExtension: {result.extension}")
                print(f"\tMime Type: {result.mime_type}")
                print(f"\tByte Match: {result.byte_match}")
                print(f"\tOffset: {result.offset}\n")


if __name__ == "__main__":  # pragma: no cover
    command_line_entry()
