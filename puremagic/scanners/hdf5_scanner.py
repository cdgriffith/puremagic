import os

from puremagic.scanners.helpers import Match

HDF5_MAGIC = b"\x89HDF\r\n\x1a\n"

# HDF5 subtype signatures: (mandatory, optional, min_optional, ext, name, mime)
# All mandatory strings must be present, plus at least min_optional of the optional strings.
_SUBTYPES = [
    # AnnData - single-cell genomics (h5ad)
    ([], [b"/obs", b"/var", b"/X"], 2, ".h5ad", "AnnData", "application/x-anndata"),
    # Loom - single-cell genomics
    ([], [b"/matrix", b"/row_attrs", b"/col_attrs"], 2, ".loom", "Loom single-cell data", "application/x-loom"),
    # Multi-resolution Cooler (must check before single-resolution)
    (
        [b"/resolutions"],
        [b"/bins", b"/chroms"],
        1,
        ".mcool",
        "Multi-resolution Cooler contact matrix",
        "application/x-mcool",
    ),
    # Cooler - genomic contact matrices
    ([], [b"/bins", b"/chroms", b"/pixels"], 2, ".cool", "Cooler contact matrix", "application/x-cooler"),
    # BIOM v2 - biological observation matrix
    (
        [],
        [b"BIOM", b"/observation", b"/sample"],
        2,
        ".biom2",
        "BIOM v2 biological observation matrix",
        "application/x-biom2",
    ),
    # mz5 - mass spectrometry
    ([], [b"/SpectrumMetaData", b"/ChomatogramMetaData"], 1, ".mz5", "mz5 mass spectrometry data", "application/x-mz5"),
    # h5mlm - ML model
    ([], [b"model_type", b"h5mlm"], 1, ".h5mlm", "HDF5 ML model", "application/x-h5mlm"),
]


def main(file_path: os.PathLike | str, head: bytes, foot: bytes) -> Match | None:
    if not head or not head.startswith(HDF5_MAGIC):
        return None

    # Read a larger chunk to find group/dataset names
    with open(file_path, "rb") as f:
        data = f.read(65536)

    for mandatory, optional, min_optional, ext, name, mime in _SUBTYPES:
        if not all(s in data for s in mandatory):
            continue
        opt_matches = sum(1 for s in optional if s in data)
        if opt_matches >= min_optional:
            return Match(
                extension=ext,
                name=name,
                mime_type=mime,
                confidence=0.9,
            )

    return None
