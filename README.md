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

```
    import puremagic
    ext = puremagic.from_file(filename)
```


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
        filename += ".txt"
```

### Acknowledgements

Gary C. Kessler
    For use of his File Signature Tables, available at:
    http://www.garykessler.net/library/file_sigs.html