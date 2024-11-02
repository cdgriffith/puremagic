from collections import namedtuple


class Match(namedtuple):
    def __new__(cls, extension, name, mime_type, confidence=1):
        return super().__new__(cls, extension, name, mime_type, confidence)
