import timeit
import sys
import os
import puremagic
import time
try:
    import test.magic as magic
    magic.from_file('%s' % os.path.join("test", "resources", "images", "test.jpg"), mime=True)
    ism = True
except Exception, e:
    print str(e)
    print "Please download magic to compare timing: https://github.com/ahupp/python-magic"
    print ""
    sys.exit()
    ism = False

testimage = os.path.join("test", "resources", "images", "test.jpg")
testvideo = os.path.join("test", "resources", "video", "test.avi")
testoffic = os.path.join("test", "resources", "office", "test.docx")
testarchs = os.path.join("test", "resources", "archive", "test.bz2")
testmeida = os.path.join("test", "resources", "media", "test (split).vmdk")
tests = [
    testimage,
    testvideo,
    testoffic,
    testarchs,
    testmeida
]
    
import timeit

print "Compare puremagic to python-magic wrapper times. Each test is run 1000 times to figure out a fair average"

for test in tests:
    pm = timeit.timeit("puremagic.from_file('%s', mime=True)" % test, setup="import puremagic", number=1000)
    m = timeit.timeit("magic.from_file('%s', mime=True)" % test, setup="import test.magic as magic", number=1000)
    if m > pm:
        print "puremagic was " + str(m/pm)[0:4] + " times faster than magic testing '%s'" % os.path.basename(test)
    elif pm > m:
        print "magic was " + str(pm/m)[0:4] + " times faster than puremagic testing '%s'" % os.path.basename(test)
    
    