from dataclasses import dataclass


@dataclass
class Match:
    extension: str
    name: str
    mime_type: str
    confidence: float = 1
