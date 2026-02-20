=========
puremagic
=========

puremagic is a pure python module that will identify a file based off
its magic numbers. It has zero runtime dependencies and serves as a
lightweight, cross-platform alternative to python-magic/libmagic.

It is designed to be minimalistic and inherently cross platform
compatible. It is also designed to be a stand in for python-magic. It
implements the functions :code:`from_file(filename[, mime])` and
:code:`from_string(string[, mime])` however the :code:`magic_file()` and
:code:`magic_string()` are more powerful and will also display confidence and
duplicate matches.

Starting with version 2.0, puremagic includes a **deep scan** system
that performs content-aware analysis beyond simple magic number matching.
This improves accuracy for formats like Office documents, text files,
CSV, MP3, Python source, JSON, HDF5, email, and many scientific formats.
Deep scan is enabled by default and can be disabled by setting the
environment variable :code:`PUREMAGIC_DEEPSCAN=0`.

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

-  Python 3.12+

For use with Python 3.7–3.11, use the 1.x release chain.

Using github ci to run continuous integration tests on listed platforms.

Install from PyPI
-----------------

.. code:: bash

        $ pip install puremagic

On linux environments, you may want to be clear you are using python3

.. code:: bash

        $ python3 -m pip install puremagic

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

Deep Scan
---------

Deep scan performs content-aware analysis when magic number matching
alone is not enough. It is enabled by default and runs automatically
as part of the normal identification pipeline.

The following format-specific scanners are included:

-  **ZIP** — Distinguishes Office formats (xlsx/docx/pptx), OpenDocument
   (odt/ods/odp), and their macro-enabled variants by inspecting ZIP internals
-  **MPEG Audio** — Parses MP3/MPEG audio frames to validate and identify audio files
-  **Text** — Detects text encodings, line endings (CRLF/LF/CR), CSV files
   with automatic delimiter detection, and email messages (.eml)
-  **Python** — Validates Python source via :code:`ast.parse()` and keyword analysis
-  **PDF** — Format-specific PDF validation
-  **JSON** — JSON format validation
-  **HDF5** — Identifies HDF5 subtypes used in scientific computing (AnnData,
   Loom, Cooler, BIOM v2, mz5, and more)
-  **Audio** — Identifies HCOM and SNDR audio formats
-  **Dynamic text checks** — Recognizes many scientific and bioinformatics text
   formats including VCF, SAM, GFF, PLY, VTK, and others

To disable deep scan, set the environment variable:

.. code:: bash

        $ export PUREMAGIC_DEEPSCAN=0

Script
------

*Usage*

.. code:: bash

        $ python -m puremagic [options] filename <filename2>...

*Options*

-  :code:`-m, --mime` — Return the MIME type instead of file extension
-  :code:`-v, --verbose` — Print verbose output with all possible matches
-  :code:`--version` — Show program version

Directories can be passed as arguments; all files within will be scanned.

*Examples*

.. code:: bash

        $ python -m puremagic test/resources/images/test.gif
        'test/resources/images/test.gif' : .gif

        $ python -m puremagic -m test/resources/images/test.gif test/resources/audio/test.mp3
        'test/resources/images/test.gif' : image/gif
        'test/resources/audio/test.mp3' : audio/mpeg

Upgrading from 1.x
-------------------

Version 2.0 includes the following breaking changes:

-  **Python 3.12+ required** — Python 3.7–3.11 are no longer supported.
   Use the 1.x release chain for older Python versions.
-  **Removed** :code:`puremagic.what()` — The :code:`imghdr` drop-in replacement
   has been removed. Use :code:`puremagic.from_file()` instead.
-  **Removed** :code:`magic_header_array`, :code:`magic_footer_array`, and
   :code:`multi_part_dict` from the public API.
-  **Removed** :code:`setup.py` — The project now uses :code:`pyproject.toml`
   exclusively.
-  Internal functions have been renamed from private (e.g. :code:`_magic_data`)
   to public (e.g. :code:`magic_data`).

FAQ
---

*The file type is actually X but it's showing up as Y with higher
confidence?*

This can happen when the file's signature happens to match a subset of a
file standard. The subset signature will be longer, therefore report
with greater confidence, because it will have both the base file type
signature plus the additional subset one.


Acknowledgements
----------------

Gary C. Kessler

For use of his File Signature Tables, available at:
https://filesig.search.org/

Freedesktop.org

For use of their shared-mime-info file, available at:
https://cgit.freedesktop.org/xdg/shared-mime-info/

License
-------

MIT Licenced, see LICENSE, Copyright (c) 2013-2026 Chris Griffith
