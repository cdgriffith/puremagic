Changelog
=========

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