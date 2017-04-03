Changelog
=========

Version 1.3
-----------

- Adding filename extension hinting for string (Thanks to jiel)
- Adding open office MIME tpyes (Thanks to jiel)

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