#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
puremagic is a pure python module that will identify a file based off it's
magic numbers. It is designed to be minimalistic and inherently cross platform
compatible, with no imports when used as a module.

© 2013-2018 Chris Griffith - License: MIT (see LICENSE)

Acknowledgements
Gary C. Kessler
    For use of his File Signature Tables, available at:
    http://www.garykessler.net/library/file_sigs.html
"""
import os
import json
import binascii
from itertools import chain

__author__ = "Chris Griffith"
__version__ = "1.4"
__all__ = ['magic_file', 'magic_string', 'from_file', 'from_string',
           'ext_from_filename', 'PureError', 'magic_footer_array',
           'magic_header_array']

here = os.path.abspath(os.path.dirname(__file__))


class PureError(LookupError):
    """Do not have that type of file in our databanks"""


def _magic_data(filename=os.path.join(here, 'magic_data.json')):
    """ Read the magic file"""
    with open(filename) as f:
        data = json.load(f)
    for x in data['headers']:
        x[0] = binascii.unhexlify(x[0].encode('ascii'))
    for x in data['footers']:
        x[0] = binascii.unhexlify(x[0].encode('ascii'))
    return data['headers'], data['footers']


magic_header_array, magic_footer_array = _magic_data()


def _max_lengths():
    """ The length of the largest magic string + its offset"""
    max_header_length = max([len(x[0]) + x[1] for x in magic_header_array])
    max_footer_length = max([len(x[0]) + abs(x[1])
                             for x in magic_footer_array])
    return max_header_length, max_footer_length


def _confidence(matches, ext=None):
    """ Rough confidence based on string length and file extension"""
    results = []
    for match in matches:
        con = (0.8 if len(match[0]) > 9 else
               float("0.{0}".format(len(match[0]))))
        if ext == match[0]:
            con = 0.9
        results.append(match + [con])
    return sorted(results, key=lambda x: x[3], reverse=True)


def _identify_all(header, footer, ext=None):
    """ Attempt to identify 'data' by its magic numbers"""

    # Capture the length of the data
    # That way we do not try to identify bytes that don't exist
    matches = list()
    for magic_row in magic_header_array:
        start = magic_row[1]
        end = magic_row[1] + len(magic_row[0])
        if end > len(header):
            continue
        if header[start:end] == magic_row[0]:
            matches.append([magic_row[2], magic_row[3], magic_row[4]])

    for magic_row in magic_footer_array:
        start = magic_row[1]
        if footer[start:] == magic_row[0]:
            matches.append([magic_row[2], magic_row[3], magic_row[4]])
    if not matches:
        raise PureError("Could not identify file")

    return _confidence(matches, ext)


def _magic(header, footer, mime, ext=None):
    """ Discover what type of file it is based on the incoming string """
    if not header:
        raise ValueError("Input was empty")
    info = _identify_all(header, footer, ext)[0]
    if mime:
        return info[1]
    return info[0] if not isinstance(info[0], list) else info[0][0]


def _file_details(filename):
    """ Grab the start and end of the file"""
    max_head, max_foot = _max_lengths()
    with open(filename, "rb") as fin:
        head = fin.read(max_head)
        try:
            fin.seek(-max_foot, os.SEEK_END)
        except IOError:
            fin.seek(0)
        foot = fin.read()
    return head, foot


def _string_details(string):
    """ Grab the start and end of the string"""
    max_head, max_foot = _max_lengths()
    return string[:max_head], string[-max_foot:]


def ext_from_filename(filename):
    """ Scan a filename for it's extension.

    :param filename: string of the filename
    :return: the extension off the end (empty string if it can't find one)
    """
    try:
        base, ext = filename.lower().rsplit(".", 1)
    except ValueError:
        return ''
    ext = ".{0}".format(ext)
    all_exts = [x[2] for x in chain(magic_header_array, magic_footer_array)]

    if base[-4:].startswith("."):
        # For double extensions like like .tar.gz
        long_ext = base[-4:] + ext
        if long_ext in all_exts:
            return long_ext
    return ext


def from_file(filename, mime=False):
    """ Opens file, attempts to identify content based
    off magic number and will return the file extension.
    If mime is True it will return the mime type instead.

    :param filename: path to file
    :param mime: Return mime, not extension
    :return: guessed extension or mime
    """

    head, foot = _file_details(filename)
    return _magic(head, foot, mime, ext_from_filename(filename))


def from_string(string, mime=False, filename=None):
    """ Reads in string, attempts to identify content based
    off magic number and will return the file extension.
    If mime is True it will return the mime type instead.
    If filename is provided it will be used in the computation.

    :param string: string representation to check
    :param mime: Return mime, not extension
    :param filename: original filename
    :return: guessed extension or mime
    """
    head, foot = _string_details(string)
    ext = ext_from_filename(filename) if filename else None
    return _magic(head, foot, mime, ext)


def magic_file(filename):
    """ Returns tuple of (num_of_matches, array_of_matches)
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
    info.sort(key=lambda x: x[3], reverse=True)
    return info


def magic_string(string, filename=None):
    """ Returns tuple of (num_of_matches, array_of_matches)
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
    info.sort(key=lambda x: x[3], reverse=True)
    return info


def command_line_entry(*args):
    from argparse import ArgumentParser
    import sys
    desc = "puremagic is a pure python file identification module. \
    It looks for matching magic numbers in the file to locate the file type. "
    parser = ArgumentParser(description=desc)
    parser.add_argument("-m",
                        "--mime",
                        action="store_true",
                        dest="mime",
                        help="Return the mime type instead of file type")
    parser.add_argument('files', nargs="+")
    args = parser.parse_args(args if args else sys.argv[1:])

    for fn in args.files:
        if not os.path.exists(fn):
            print("File '{0}' does not exist!".format(fn))
            continue
        try:
            print("'{0}' : {1}".format(fn, from_file(fn, args.mime)))
        except PureError:
            print("'{0}' : could not be Identified".format(fn))


if __name__ == '__main__':
    command_line_entry()
