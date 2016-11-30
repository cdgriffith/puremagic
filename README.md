puremagic
=========

puremagic is a pure python module that will identify a file based off it's
magic numbers.

[![Build Status](https://travis-ci.org/cdgriffith/puremagic.png?branch=master)](https://travis-ci.org/cdgriffith/puremagic)

It is designed to be minimalistic and inherently cross platform
compatible. However this does come at the price of being incomplete.
It is also designed to be a stand in for python-magic, it incorporates the
functions from_file(filename[, mime]) and from_string(string[, mime])
however the magic_file() and magic_string() are more powerful and will also
display confidence and duplicate matches.

Advantages over using a wrapper for 'file' or 'libmagic':

* Faster
* Lightweight (10x smaller compared to wrapper and 'file')
* Cross platform compatible
    
Disadvantages:

* Not as powerful (Cannot identify nearly as many files)
* Duplications due to small or reused magic numbers

Compatibility:
    Tested on Python 2.6+ & 3.2+
        
### Usage

`from_file` will return the most likely file extension. `magic_file` will give
you every possible result it finds, as well as the confidence.

```python
    filename = "test/resources/images/test.gif"
    import puremagic
    ext = puremagic.from_file(filename)
    # '.gif'

    puremagic.magic_file(filename)
    # (2, [['.gif', 'image/gif', 'Graphics interchange format file (GIF87a)', 0.7],
    #      ['.gif', '', 'GIF file', 0.5]])

```

In this example, it matches a gif file perfectly. And with `magic_file` it gives
you the count of matching items first, then for each match provides:

- possible extension(s)
- mime type
- descritpion
- confidence (All headers have to perfectly match to make the list, however this orders it by longest header, therefore most precise, first)

But we can see this gives us exactly what we want with the first item only,
So why bother with more detail?

Lets try a more complicated file, such as Microsoft Office files.


```python
    puremagic.magic_file("test/resources/office/test.pptx")
    # (21, [[['.docx', '.pptx', 'xlsx'], 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'Microsoft Office 2007+ Open XML Format Document file', 0.9],
    #       ['.zip', 'application/zip', 'PKZIP Archive file', 0.5],
    #       ....
    # )

    puremagic.from_file("test/resources/office/test.pptx")
    # '.docx'

```

Newer Microsoft Office files are actually a set of zipped files. So
 it is able to identify it as an office file (and notice the lower confidence is properly a zip file),
 with the possible extensions, but will only label it as the first one.


### Script


```
    $ python puremagic.py [options] filename <filename2>...
```
    
### Practical Example

```
    import puremagic
    
    filename = "/path/unknownfile"
    
    try:
        filename += puremagic.from_file(filename)
    except puremagic.PureError:
        #subclass of LookupError
        filename += ".unknown"
```

### Acknowledgements

Gary C. Kessler
    For use of his File Signature Tables, available at:
    http://www.garykessler.net/library/file_sigs.html