#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
puremagic is a pure python module that will identify a file based off it's
magic numbers. It is designed to be minimalistic and inherently cross platform
compatible, with no imports when used as a module. 

© 2013-2016 Chris Griffith - License: MIT (see LICENSE)

Acknowledgements
Gary C. Kessler
    For use of his File Signature Tables, available at:
    http://www.garykessler.net/library/file_sigs.html
"""
import os

from magic_data import *

__author__ = "Chris Griffith"
__version__ = "1.2"


class PureError(LookupError):
    """Do not have that type of file in our databanks"""


def _confidence(row):
    length = len(row[0])
    length += 1 if length >= 3 else 0
    con = 0.9 if length > 10 else float("0.{0}".format(length))
    return con


def _identify_all(header, footer):
    """Attempt to identify 'data' by it's magic numbers"""

    # Capture the length of the data
    # That way we do not try to identify bytes that don't exist
    matches = list()
    for magic_row in magic_array:
        start = magic_row[1]
        end = magic_row[1] + len(magic_row[0])
        if end > len(header):
            continue
        if header[start:end] == magic_row[0]:
            matches.append([magic_row[2], magic_row[3], magic_row[4],
                            _confidence(magic_row)])

    for magic_row in magic_footer_array:
        start = magic_row[1]
        if footer[start:] == magic_row[0]:
            matches.append([magic_row[2], magic_row[3], magic_row[4],
                            _confidence(magic_row)])
    if not matches:
        raise PureError("Could not identify file")
    return sorted(matches, key=lambda x: x[3], reverse=True)


def _magic(header, footer, mime):
    """ Discover what type of file it is based on the incoming string """
    if len(header) == 0:
        raise ValueError("Input was empty")
    info = _identify_all(header, footer)[0]
    if mime:
        return info[1]
    return info[0] if not isinstance(info[0], list) else info[0][0]


def _file_details(filename):
    with open(filename, "rb") as fin:
        head = fin.read(max_length)
        try:
            fin.seek(-max_footer_length, os.SEEK_END)
        except IOError:
            fin.seek(0)
        foot = fin.read()
    return head, foot


def _string_details(string):
    return string[:max_length], string[-max_footer_length:]


def from_file(filename, mime=False):
    """Opens file, attempts to identify content based
    off magic number and will return the file extension.
    If mime is True it will return the mime type instead."""

    head, foot = _file_details(filename)
    return _magic(head, foot, mime)


def from_string(string, mime=False):
    """Reads in string, attempts to identify content based
    off magic number and will return the file extension.
    If mime is True it will return the mime type instead."""
    head, foot = _string_details(string)
    return _magic(head, foot, mime)


def magic_file(filename):
    """Returns tuple of (num_of_matches, array_of_matches)
    arranged highest confidence match first."""
    head, foot = _file_details(filename)
    if len(head) == 0:
        raise ValueError("Input was empty")
    try:
        info = _identify_all(head, foot)
    except PureError:
        info = []
    info.sort(key=lambda x: x[3], reverse=True)
    return len(info), info


def magic_string(string):
    """Returns tuple of (num_of_matches, array_of_matches)
    arranged highest confidence match first"""
    if len(string) == 0:
        raise ValueError("Input was empty")
    head, foot = _string_details(string)
    info = _identify_all(head, foot)
    info.sort(key=lambda x: x[3], reverse=True)
    return len(info), info


def _main():
    from optparse import OptionParser
    usage = "usage: %prog [options] filename <filename2>..."
    desc = "puremagic is a pure python file identification module. \
    It looks for matching magic numbers in the file to locate the file type. "
    parser = OptionParser(usage=usage, version=__version__, description=desc)
    parser.add_option("-m",
                      "--mime",
                      action="store_true",
                      dest="mime",
                      help="Return the mime type instead of file type")
    (options, args) = parser.parse_args()

    if len(args) < 1:
        parser.error("please specific a filename")
        return

    for fn in args:
        if not os.path.exists(fn):
            print("File '{0}' does not exist!".format(fn))
            print("Please check the location and filename and try again.")
            continue
        try:
            print("'{0}' : {1}".format(fn, from_file(fn, options.mime)))
        except PureError:
            print("'{0}' : could not be Identified".format(fn))


if __name__ == '__main__':
    _main()
