puremagic
=========

puremagic is a pure python module that will identify a file based off
it's magic numbers.

|CoverageStatus| |License| |PyPi|

It is designed to be minimalistic and inherently cross platform
compatible. It is also designed to be a stand in for python-magic, it
incorporates the functions from\_file(filename[, mime]) and
from\_string(string[, mime]) however the magic\_file() and
magic\_string() are more powerful and will also display confidence and
duplicate matches.

It does NOT try to match files off non-magic string. In other words it
will not search for a string within a certain window of bytes like
others might.

Advantages over using a wrapper for 'file' or 'libmagic':

-  Faster
-  Lightweight
-  Cross platform compatible
-  No dependencies

Disadvantages:

-  Does not have as many file types
-  No multilingual comments
-  Duplications due to small or reused magic numbers

(Help fix the first two disadvantages by contributing!)

Compatibility
~~~~~~~~~~~~~

-  Python 3.8+

Using github ci to run continuous integration tests on listed platforms.

Install from pypy
-----------------

.. code:: bash

        $ pip install puremagic

On linux environments, you may want to be clear you are using python3

.. code:: bash

        $ python3 -m pip install puremagic


Install from source
-------------------

In either a virtualenv or globally, simply run:

.. code:: bash

        $ python setup.py install

Usage
-----

"from_file" will return the most likely file extension. "magic_file"
will give you every possible result it finds, as well as the confidence.

.. code:: python

        import puremagic

        filename = "test/resources/images/test.gif"

        ext = puremagic.from_file(filename)
        # '.gif'

        puremagic.magic_file(filename)
        # [['.gif', 'image/gif', 'Graphics interchange format file (GIF87a)', 0.7],
        #  ['.gif', '', 'GIF file', 0.5]]

With "magic_file" it gives each match, highest confidence first:

-  possible extension(s)
-  mime type
-  description
-  confidence (All headers have to perfectly match to make the list,
   however this orders it by longest header, therefore most precise,
   first)

If you already have a file open, or raw byte string, you could also use:

* from_string
* from_stream
* magic_string
* magic_stream

.. code:: python

        with open(r"test\resources\video\test.mp4", "rb") as file:
            print(puremagic.magic_stream(file))

        # [PureMagicWithConfidence(byte_match=b'ftypisom', offset=4, extension='.mp4', mime_type='video/mp4', name='MPEG-4 video', confidence=0.8),
        #  PureMagicWithConfidence(byte_match=b'iso2avc1mp4', offset=20, extension='.mp4', mime_type='video/mp4', name='MP4 Video', confidence=0.8)]

Script
------

*Usage*

.. code:: bash

        $ python -m puremagic [options] filename <filename2>...

*Examples*

.. code:: bash

        $ python -m puremagic test/resources/images/test.gif
        'test/resources/images/test.gif' : .gif

        $ python -m puremagic -m test/resources/images/test.gif test/resources/audio/test.mp3
        'test/resources/images/test.gif' : image/gif
        'test/resources/audio/test.mp3' : audio/mpeg

FAQ
---

*The file type is actually X but it's showing up as Y with higher
confidence?*

This can happen when the file's signature happens to match a subset of a
file standard. The subset signature will be longer, therefore report
with greater confidence, because it will have both the base file type
signature plus the additional subset one.

*You don't have sliding offsets that could better detect plenty of
common formats, why's that?*

Design choice, so it will be a lot faster and more accurate. Without
more intelligent or deeper identification past a sliding offset I don't
feel comfortable including it as part of a 'magic number' library.

*Your version isn't as complete as I want it to be, where else should I
look?*

Look into python modules that wrap around libmagic or use something like
Apache Tika.

Acknowledgements
----------------

Gary C. Kessler


For use of his File Signature Tables, available at:
http://www.garykessler.net/library/file_sigs.html

Freedesktop.org

For use of their shared-mime-info file (even if they do use XML, blea), available at:
https://cgit.freedesktop.org/xdg/shared-mime-info/

License
-------

MIT Licenced, see LICENSE, Copyright (c) 2013-2024 Chris Griffith

.. |CoverageStatus| image:: https://coveralls.io/repos/github/cdgriffith/puremagic/badge.svg?branch=develop
   :target: https://coveralls.io/github/cdgriffith/puremagic?branch=develop
.. |PyPi| image:: https://img.shields.io/pypi/v/puremagic.svg?maxAge=2592000
   :target: https://pypi.python.org/pypi/puremagic/
.. |License| image:: https://img.shields.io/pypi/l/puremagic.svg
   :target: https://pypi.python.org/pypi/puremagic/
