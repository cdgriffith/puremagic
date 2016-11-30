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

from magic_data import magic_array, max_length

__author__ = "Chris Griffith"
__version__ = "1.2"


class PureError(LookupError):
    """Do not have that type of file in our databanks"""


def _identify(data):
    """Attempt to identify 'data' by it's magic numbers"""

    # Capture the length of the data
    # That way we do not try to identify bytes that don't exist
    length = len(data)

    # Iterate through the list of known magic strings
    for magic_row in magic_array:
        start = magic_row[1]

        if start < 0:
            # Check footer instead of header
            if data[start:] == magic_row[0]:
                return magic_row
        else:
            end = magic_row[1] + len(magic_row[0])
            if end > length:
                continue
            if data[start:end] == magic_row[0]:
                return magic_row
    raise PureError("Could not identify file")


def _confidence(row):
    length = len(row[0])
    length += 1 if length >= 3 else .5
    con = 0.9 if length > 10 else float("0.{0}".format(length))
    return con


def _identify_all(data):
    """Attempt to identify 'data' by it's magic numbers"""

    # Capture the length of the data
    # That way we do not try to identify bytes that don't exist
    length = len(data)
    matches = list()
    # Iterate through the items first via the header
    for magic_row in magic_array:
        start = magic_row[1]
        if start < 0:
            # Check footer instead of header
            if data[start:] == magic_row[0]:
                matches.append([magic_row[2], magic_row[3], magic_row[4],
                                _confidence(magic_row)])
        else:
            end = magic_row[1] + len(magic_row[0])
            if end > length:
                continue
            if data[start:end] == magic_row[0]:
                matches.append([magic_row[2], magic_row[3], magic_row[4],
                                _confidence(magic_row)])
    if not matches:
        raise PureError("Could not identify file")
    return matches


def _magic(data, mime):
    """ Discover what type of file it is based on the incoming string """
    if len(data) == 0:
        raise ValueError("Input was empty")
    info = _identify(data)
    if mime:
        return info[3]
    return info[2] if not isinstance(info[2], list) else info[2][0]


def from_file(filename, mime=False):
    """Opens file, attempts to identify content based
    off magic number and will return the file extension.
    If mime is True it will return the mime type instead."""
    with open(filename, "rb") as fin:
        data = fin.read(max_length)
    return _magic(data, mime)


def from_string(string, mime=False):
    """Reads in string, attempts to identify content based
    off magic number and will return the file extension.
    If mime is True it will return the mime type instead."""
    return _magic(string[:max_length], mime)


def magic_file(filename):
    """Returns tuple of (num_of_matches, array_of_matches)
    arranged highest confidence match first."""
    fin = open(filename, "rb")
    data = fin.read()
    fin.close()
    if len(data) == 0:
        raise ValueError("Input was empty")
    try:
        info = _identify_all(data)
    except PureError:
        info = []
    info.sort(key=lambda x: x[3], reverse=True)
    return len(info), info


def magic_string(string):
    """Returns tuple of (num_of_matches, array_of_matches)
    arranged highest confidence match first"""
    if len(string) == 0:
        raise ValueError("Input was empty")
    info = _identify_all(string)
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
