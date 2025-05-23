Changelog
=========

Version 2.0.0
-------------

- Adding deep scan for improved accuracy #102 #94 #70 #69 #12 #3
- Changing to full semantic versioning to be able to denote bugfixes vs minor features
- Removing support for python 3.7, 3.8, 3.9, 3.10 and 3.11 please stick to 1.x release chain to support older versions

Version 1.29
------------

- Changing to publishing to pypi with Python 3.9
- Fixing #105 fsspec/gcsfs throws an ValueError instead of a OSError (thanks to Markus)
- Fixing github actions due to updates

Version 1.28
------------

- Adding #99 New file support (thanks to Andy - NebularNerd)
- Fixing #100 FITS files no longer had mime type (thanks to ejeschke)

Version 1.27
------------

- Adding new verbose output to command line with `-v` or `--verbose`
- Adding #92 include py.typed in sdist (thanks to Nicholas Bollweg - bollwyvl)
- Adding #93 Improve PDF file detection, fix json description (thanks to Péter - peterekepeter)
- Fixing #96 #86 stream does not work properly on opened small files (thanks to Felipe Lema and Andy - NebularNerd)
- Removing expected invalid WinZip signature

Version 1.26
------------

- Adding #87 sndhdr update and HD/CD/DVD Image files (thanks to Andy - NebularNerd)
- Adding #88 Add .caf mime type (thanks to William Bonnaventure)
- Fixing #89 add py.typed to package_data (thanks to Sebastian Kreft)

Version 1.25
------------

- Changing to support Python 3.7 again

Version 1.24
------------

- Adding #72 #75 #76 #81 `.what()` to be a drop in replacement for `imghdr.what()` (thanks to Christian Clauss and Andy - NebularNerd)
- Adding #67 Test on Python 3.13 beta (thanks to Christian Clauss)
- Adding #77 from __future__ import annotations (thanks to Christian Clauss
- Changing all HTML extensions to full `.html`
- Fixing #66 Confidence sorting (thanks to Andy - NebularNerd)

Version 1.23
------------

- Fixing #32 MP3 Detection improvements (thanks to Andy - NebularNerd and Sander)

Version 1.22
------------

- Adding #52 magic data for JPEG XS (thanks to Andy - NebularNerd)
- Adding #57 Multi-part checks with negative offsets (thanks to Andy - NebularNerd)
- Fixing #60 encoding warning (thanks to Andy - NebularNerd and Jason R. Coombs)

Version 1.21
------------

- Adding #50 details for  ZSoft .pcx files (thanks to Andy - NebularNerd)
- Adding #51 details for JXL files (thanks to Andy - NebularNerd)
- Adding #54 missing py.typed file (thanks to Raphaël Vinot)
- Fixing #53 magic data for GIF images (thanks to Andy - NebularNerd)

Version 1.20
------------

- Adding support for multi-part header checks (thanks to Andy)
- Fixing matches for webp (thanks to Nicolas Wicht)
- Fixing matches for epub (thanks to Alexander Walters)

Version 1.15
------------

- Adding fix for resetting the stream after reading part of it (thanks to R. Singh)

Version 1.14
------------

- Adding generic extension mapping for common file types
- Adding #36 details to readme about magic_stream and magic_string (thanks to Martin)
- Fixing multiple bad extensions and mimetypes
- Removing bad entry for 3gp5 selecting multiple things

Version 1.13
------------

- Adding support for Path for filename
- Adding details for mp4
- Adding details for avif and heif images

Version 1.12
------------

- Adding #38 webp mimetype (thanks to phith0n)
- Adding #37 SVG images (thanks to Gerhard Schmidt)
- Adding missing mimetypes for aac, vmdk, wmv and xcf

Version 1.11
------------

- Adding #34 test files to build (thanks to James French)
- Adding #33 install from pypi details (thanks to Sander)
- Removing #31 unsupported Python items in setup.py (thanks to Safihre)

Version 1.10
------------

- Fixing how confidence works (thanks to Sean Stallbaum)

Version 1.9
-----------

- Adding new methods for stream handling (from_stream, magic_stream) (thanks to Robbert Korving)

Version 1.8
-----------

- Adding support for various other files (thanks to Don Tsang)
- Adding missing mime types (thanks to Oleksandr)

Version 1.7
-----------

- Adding support for PCAPNG files (thanks to bannsec)
- Adding support for numerous other files updated by Gary C. Kessler
- Adding script for parsing FTK GCK sigs
- Changing test suites to github workflows instead of TravisCI
- Removing official support, new packages and test for python 2

Version 1.6
-----------

- Adding support for LZ4 and ZSTD archives (Thanks to Sergey Ponomarev)
- Adding support for more office formats (Thanks to andrewpmk)

Version 1.5
-----------

- Adding full magic info in results (Thanks to David Shunfenthal)
- Fixing magic_data.json not being added to sdist dist (Thanks to Andrey Zakharevich)

Version 1.4
-----------

- Fixing how `__main__` was implemented (Thanks to Victor Domingos)

Version 1.3
-----------

- Adding filename extension hinting for string (Thanks to jiel)
- Adding open office MIME types (Thanks to jiel)

Version 1.2
-----------

- Adding setup file
- Adding changelog
- Adding CI tests support for 3.4, 3.5, 3.6 and pypy
- Adding more basic documentation
- Adding magic detection from https://www.freedesktop.org/wiki/Specifications/shared-mime-info-spec/
- Removing testing on 3.2 due to Travis CI and coverage not getting along
- Changing to argparse instead of optparse
- Changing magic_file to not raise error on empty, simple provide an empty list
- Changing magic_data py file to a json file so it's easier to understand and modify
- Updating data to be a python file, so there is no dangerous eval


Version 1.1
-----------

- Adding tests
- Changing to MIT License

Version 1.0
-----------

- Initial release
