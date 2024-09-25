#!/usr/bin/env python
"""
puremagic is a pure python module that will identify a file based off it's
magic numbers. It is designed to be minimalistic and inherently cross platform
compatible, with no imports when used as a module.

© 2013-2024 Chris Griffith - License: MIT (see LICENSE)

Acknowledgements
Gary C. Kessler
    For use of his File Signature Tables, available at:
    http://www.garykessler.net/library/file_sigs.html
"""

from __future__ import annotations

import json
import os
from binascii import unhexlify
from collections import namedtuple
from itertools import chain

__author__ = "Chris Griffith"
__version__ = "1.28"
__all__ = [
    "magic_file",
    "magic_string",
    "magic_stream",
    "from_file",
    "from_string",
    "from_stream",
    "ext_from_filename",
    "PureError",
    "magic_footer_array",
    "magic_header_array",
    "multi_part_dict",
    "what",
    "PureMagic",
    "PureMagicWithConfidence",
]

# Convert puremagic extensions to imghdr extensions
imghdr_exts = {"dib": "bmp", "jfif": "jpeg", "jpg": "jpeg", "rst": "rast", "sun": "rast", "tif": "tiff"}

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


def _magic_data(
    filename: os.PathLike | str = os.path.join(here, "magic_data.json"),
) -> tuple[list[PureMagic], list[PureMagic], list[PureMagic], dict[bytes, list[PureMagic]]]:
    """Read the magic file"""
    with open(filename, encoding="utf-8") as f:
        data = json.load(f)
    headers = sorted((_create_puremagic(x) for x in data["headers"]), key=lambda x: x.byte_match)
    footers = sorted((_create_puremagic(x) for x in data["footers"]), key=lambda x: x.byte_match)
    extensions = [_create_puremagic(x) for x in data["extension_only"]]
    multi_part_extensions = {}
    for file_match, option_list in data["multi-part"].items():
        multi_part_extensions[unhexlify(file_match.encode("ascii"))] = [_create_puremagic(x) for x in option_list]
    return headers, footers, extensions, multi_part_extensions


def _create_puremagic(x: list) -> PureMagic:
    return PureMagic(
        byte_match=unhexlify(x[0].encode("ascii")),
        offset=x[1],
        extension=x[2],
        mime_type=x[3],
        name=x[4],
    )


magic_header_array, magic_footer_array, extension_only_array, multi_part_dict = _magic_data()


def _max_lengths() -> tuple[int, int]:
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


max_head, max_foot = _max_lengths()


def _confidence(matches, ext=None) -> list[PureMagicWithConfidence]:
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

    if not results:
        raise PureError("Could not identify file")

    return sorted(results, key=lambda x: (x.confidence, len(x.byte_match)), reverse=True)


def _identify_all(header: bytes, footer: bytes, ext=None) -> list[PureMagicWithConfidence]:
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
    return _confidence(matches, ext)


def _magic(header: bytes, footer: bytes, mime: bool, ext=None) -> str:
    """Discover what type of file it is based on the incoming string"""
    if not header:
        raise ValueError("Input was empty")
    info = _identify_all(header, footer, ext)[0]
    if mime:
        return info.mime_type
    return info.extension if not isinstance(info.extension, list) else info[0].extension


def _file_details(filename: os.PathLike | str) -> tuple[bytes, bytes]:
    """Grab the start and end of the file"""
    with open(filename, "rb") as fin:
        head = fin.read(max_head)
        try:
            fin.seek(-max_foot, os.SEEK_END)
        except OSError:
            fin.seek(0)
        foot = fin.read()
    return head, foot


def _string_details(string):
    """Grab the start and end of the string"""
    return string[:max_head], string[-max_foot:]


def _stream_details(stream):
    """Grab the start and end of the stream"""
    head = stream.read(max_head)
    try:
        stream.seek(-max_foot, os.SEEK_END)
    except OSError:
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
        # For double extensions like like .tar.gz
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

    head, foot = _file_details(filename)
    return _magic(head, foot, mime, ext_from_filename(filename))


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
    head, foot = _string_details(string)
    ext = ext_from_filename(filename) if filename else None
    return _magic(head, foot, mime, ext)


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
    head, foot = _stream_details(stream)
    ext = ext_from_filename(filename) if filename else None
    return _magic(head, foot, mime, ext)


def magic_file(filename: os.PathLike | str) -> list[PureMagicWithConfidence]:
    """
    Returns list of (num_of_matches, array_of_matches)
    arranged highest confidence match first.

    :param filename: path to file
    :return: list of possible matches, highest confidence first
    """
    head, foot = _file_details(filename)
    if not head:
        raise ValueError("Input was empty")
    try:
        info = _identify_all(head, foot, ext_from_filename(filename))
    except PureError:
        info = []
    info.sort(key=lambda x: x.confidence, reverse=True)
    return info


def magic_string(string, filename: os.PathLike | str | None = None) -> list[PureMagicWithConfidence]:
    """
    Returns tuple of (num_of_matches, array_of_matches)
    arranged highest confidence match first
    If filename is provided it will be used in the computation.

    :param string: string representation to check
    :param filename: original filename
    :return: list of possible matches, highest confidence first
    """
    if not string:
        raise ValueError("Input was empty")
    head, foot = _string_details(string)
    ext = ext_from_filename(filename) if filename else None
    info = _identify_all(head, foot, ext)
    info.sort(key=lambda x: x.confidence, reverse=True)
    return info


def magic_stream(stream, filename: os.PathLike | str | None = None) -> list[PureMagicWithConfidence]:
    """Returns tuple of (num_of_matches, array_of_matches)
    arranged highest confidence match first
    If filename is provided it will be used in the computation.

    :param stream: stream representation to check
    :param filename: original filename
    :return: list of possible matches, highest confidence first
    """
    head, foot = _stream_details(stream)
    if not head:
        raise ValueError("Input was empty")
    ext = ext_from_filename(filename) if filename else None
    info = _identify_all(head, foot, ext)
    info.sort(key=lambda x: x.confidence, reverse=True)
    return info


def command_line_entry(*args):
    import sys
    from argparse import ArgumentParser

    parser = ArgumentParser(
        description=(
            "puremagic is a pure python file identification module."
            "It looks for matching magic numbers in the file to locate the file type. "
        )
    )
    parser.add_argument(
        "-m",
        "--mime",
        action="store_true",
        dest="mime",
        help="Return the mime type instead of file type",
    )
    parser.add_argument("-v", "--v", action="store_true", dest="verbose", help="Print verbose output")
    parser.add_argument("files", nargs="+")
    args = parser.parse_args(args if args else sys.argv[1:])

    for fn in args.files:
        if not os.path.exists(fn):
            print(f"File '{fn}' does not exist!")
            continue
        try:
            print(f"'{fn}' : {from_file(fn, args.mime)}")
        except PureError:
            print(f"'{fn}' : could not be Identified")
            continue
        if args.verbose:
            matches = magic_file(fn)
            print(f"Total Possible Matches: {len(matches)}")
            for i, result in enumerate(matches):
                if i == 0:
                    print("\n\tBest Match")
                else:
                    print(f"\tAlertnative Match #{i}")
                print(f"\tName: {result.name}")
                print(f"\tConfidence: {int(result.confidence * 100)}%")
                print(f"\tExtension: {result.extension}")
                print(f"\tMime Type: {result.mime_type}")
                print(f"\tByte Match: {result.byte_match}")
                print(f"\tOffset: {result.offset}\n")


imghdr_bug_for_bug = {  # Special cases where imghdr is probably incorrect.
    b"______Exif": "jpeg",
    b"______JFIF": "jpeg",
    b"II": "tiff",
    b"II\\x2a\\x00": "tiff",
    b"MM": "tiff",
    b"MM\\x00\\x2a": "tiff",
}


def what(file: os.PathLike | str | None, h: bytes | None = None, imghdr_strict: bool = True) -> str | None:
    """A drop-in replacement for `imghdr.what()` which was removed from the standard
    library in Python 3.13.

    Usage:
    ```python
    # Replace...
    from imghdr import what
    # with...
    from puremagic import what
    # ---
    # Or replace...
    import imghdr
    ext = imghdr.what(...)
    # with...
    import puremagic
    ext = puremagic.what(...)
    ```
    imghdr documentation: https://docs.python.org/3.12/library/imghdr.html
    imghdr source code: https://github.com/python/cpython/blob/3.12/Lib/imghdr.py

    imghdr_strict enables bug-for-bug compatibility between imghdr.what() and puremagic.what() when the imghdr returns
    a match but puremagic returns None.  We believe that imghdr is delivering a "false positive" in each of these
    scenerios but we want puremagic.what()'s default behavior to match imghdr.what()'s false positives so we do not
    break existing applications.

    If imghdr_strict is True (the default) then a lookup will be done to deliver a matching result on all known false
    positives.  If imghdr_strict is False then puremagic's algorithms will determine the image type.  True is more
    compatible while False is more correct.

    NOTE: This compatibility effort only deals false positives and we are not interested to track the opposite
    situation where puremagic's deliver a match while imghdr would have returned None.  Also, puremagic.what() can
    recognize many more file types than the twelve image file types that imghdr focused on.
    """
    if isinstance(h, str):
        raise TypeError("h must be bytes, not str.  Consider using bytes.fromhex(h)")
    if h and imghdr_strict:
        ext = imghdr_bug_for_bug.get(h)
        if ext:
            return ext
    try:
        ext = (from_string(h) if h else from_file(file or "")).lstrip(".")
    except PureError:
        return None  # imghdr.what() returns None if it cannot find a match.
    return imghdr_exts.get(ext, ext)


if __name__ == "__main__":  # pragma: no cover
    command_line_entry()
