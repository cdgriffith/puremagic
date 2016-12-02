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
import json
import binascii
from itertools import chain

__author__ = "Chris Griffith"
__version__ = "1.2"

here = os.path.abspath(os.path.dirname(__file__))


class PureError(LookupError):
    """Do not have that type of file in our databanks"""


def _magic_data(filename=os.path.join(here, 'magic_data.json')):
    with open(filename) as f:
        data = json.load(f)
    for x in data['headers']:
        x[0] = binascii.unhexlify(x[0].encode('ascii'))
    for x in data['footers']:
        x[0] = binascii.unhexlify(x[0].encode('ascii'))
    return data['headers'], data['footers']

magic_header_array, magic_footer_array = _magic_data()


def _max_lengths():
    max_header_length = max([len(x[0]) + x[1] for x in magic_header_array])
    max_footer_length = max([len(x[0]) + abs(x[1]) for x in magic_footer_array])
    return max_header_length, max_footer_length


def _confidence(matches, ext=None):
    results = []
    for match in matches:
        con = (0.8 if len(match[0]) > 9 else
               float("0.{0}".format(len(match[0]))))
        if ext == match[0]:
            con = 0.9
        results.append(match + [con])
    return sorted(results, key=lambda x: x[3], reverse=True)


def _identify_all(header, footer, ext=None):
    """Attempt to identify 'data' by it's magic numbers"""

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
    if len(header) == 0:
        raise ValueError("Input was empty")
    info = _identify_all(header, footer, ext)[0]
    if mime:
        return info[1]
    return info[0] if not isinstance(info[0], list) else info[0][0]


def _file_details(filename):
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
    max_head, max_foot = _max_lengths()
    return string[:max_head], string[-max_foot:]


def ext_from_filename(filename):
    try:
        base, ext = filename.lower().rsplit(".", 1)
    except ValueError:
        return ''
    ext = ".{0}".format(ext)
    exts = [x[2] for x in chain(magic_header_array, magic_footer_array)]
    if base[-4:].startswith(".") and ext not in exts:
        return "{0}.{1}".format(base[-4:], ext)
    else:
        return ext


def from_file(filename, mime=False):
    """Opens file, attempts to identify content based
    off magic number and will return the file extension.
    If mime is True it will return the mime type instead."""

    head, foot = _file_details(filename)
    return _magic(head, foot, mime, ext_from_filename(filename))


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
        info = _identify_all(head, foot, ext_from_filename(filename))
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


def main():
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
    main()