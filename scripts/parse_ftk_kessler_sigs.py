#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
This is a very ugly helper script to keep up to date with file types in
Gary C. Kessler's FTK_sigs_GCK archive.

"""


import os
import xml.etree.ElementTree as ET
import binascii
import json

import puremagic

folder = "FTK_sigs_GCK"

sigs = []

for file in os.listdir(folder):
    if file.endswith(".xml"):
        tree = ET.parse(os.path.join(folder, file))
        root = tree.getroot()
        sig = {}
        for child in root[0]:
            if child.text:
                sig[child.tag] = child.text
            else:
                for grandchild in child:
                    if grandchild.tag == 'EXT_NAME':
                        sig[grandchild.tag] = grandchild.text.lower().split("|")
                    else:
                        sig[grandchild.tag] = grandchild.text
        sigs.append(sig)

known_sigs = {binascii.hexlify(x[0]).decode('ascii') for x in puremagic.magic_header_array}

for sig in sigs:
    sig['SIG'] = sig['SIG'].lower().strip()
    try:
        offset = int(sig.get('OFFSET', 0))
    except Exception:
        continue

    if sig['SIG'] not in known_sigs and len(sig['EXT_NAME']) == 1 and len(sig['EXT_NAME'][0]) < 5:
        print("\t\t{},".format(json.dumps([sig['SIG'], int(sig.get('OFFSET', 0)), ".{}".format(sig.get('EXT_NAME', '')[0]), "", sig['DESCRIPTION']])))
    elif sig['SIG'] not in known_sigs:
        for ext in sig['EXT_NAME']:
            if ext != "(none)":
                print("\t\t{},".format(json.dumps([sig['SIG'], offset, ".{}".format(ext), "", sig['DESCRIPTION']])))
            else:
                print("\t\t{},".format(json.dumps([sig['SIG'], offset, "", "", sig['DESCRIPTION']])))