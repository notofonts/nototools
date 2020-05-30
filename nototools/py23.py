try:
    unicode = unicode
except NameError:
    unicode = str

try:
    unichr = unichr
except NameError:
    unichr = chr

try:
    basestring = basestring
except NameError:
    basestring = str
