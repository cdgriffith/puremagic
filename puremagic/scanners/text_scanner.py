import csv
import re
import os

from puremagic.scanners.helpers import Match

crlf_pattern = re.compile(r"\r\n")
lf_pattern = re.compile(r"(?<!\r)\n")
cr_pattern = re.compile(r"\r(?!\n)")


def decode_any(unicode: bytes) -> tuple[str, str]:
    try:
        return unicode.decode("ascii"), "ascii"
    except UnicodeDecodeError:
        pass
    for encoding in {"utf-8", "cp1252"}:
        try:
            return unicode.decode(encoding), encoding
        except UnicodeDecodeError:
            pass
    raise TypeError("No encoding found")


def csv_check(file_path, text) -> Match | None:
    """
    Validate if content appears to be CSV format.
    """
    if not text or len(text.strip()) == 0:
        return None

    # Split the text into lines
    lines = text.splitlines()
    if len(lines) < 2:  # Need at least 2 lines to detect a pattern
        # If filename ends with .csv, give it the benefit of the doubt
        if str(file_path).lower().endswith('.csv'):
            return Match(
                ".csv",
                "Comma-separated values (single line)",
                "text/csv",
                confidence=0.7
            )
        return None

    # Remove any blank lines
    lines = [line for line in lines if line.strip()]
    if len(lines) < 2:
        return None
    if len(lines) > 100:
        lines = lines[:-1] # Remove last line in case it's been truncated

    # Try to determine the delimiter by checking common ones
    potential_delimiters = [',', ';', '\t', '|', ':']
    delimiter_scores = {}

    for delimiter in potential_delimiters:
        # Skip if delimiter isn't in the text
        if delimiter not in text:
            continue

        # Count fields in each line using this delimiter
        field_counts = [len(line.split(delimiter)) for line in lines]

        # Calculate consistency score (higher is better)
        if len(field_counts) >= 2:
            # Check if most lines have the same number of fields
            most_common_count = max(set(field_counts), key=field_counts.count)
            matching_lines = sum(1 for count in field_counts if count == most_common_count)
            consistency = matching_lines / len(field_counts)

            # More than one field required
            if most_common_count > 1:
                # Score based on consistency and number of fields
                delimiter_scores[delimiter] = (consistency, most_common_count)

    # Try using csv module's Sniffer as a fallback
    csv_sniffer_result = None
    try:
        dialect = csv.Sniffer().sniff(text, delimiters=''.join(potential_delimiters))
        csv_sniffer_result = dialect.delimiter
    except Exception:
        pass

    # If csv.Sniffer found a delimiter, give it priority
    if csv_sniffer_result and csv_sniffer_result in potential_delimiters:
        best_delimiter = csv_sniffer_result
        confidence = 0.95
    elif delimiter_scores:
        # Find best delimiter based on consistency and field count
        best_delimiter = max(delimiter_scores.items(), key=lambda x: (x[1][0], x[1][1]))[0]
        consistency, field_count = delimiter_scores[best_delimiter]

        # Calculate confidence based on consistency and number of fields
        confidence = 0.6 + (consistency * 0.3) + min(0.1, (field_count - 1) * 0.02)
    else:
        # No clear delimiter pattern found
        return None


    #
    # # Check for quotes that might indicate CSV
    # has_quoted_fields = '"' in text and (f'"{best_delimiter}' in text or f'{best_delimiter}\"')
    #

    delimiter_counts = []
    for line in lines:
        delim_count = line.count(best_delimiter)
        if delim_count == 0:
            return None
        delimiter_counts.append(delim_count)

    average = sum(delimiter_counts) / len(delimiter_counts)

    max_percentage = 5 / 100
    allowed_deviation = average * max_percentage

    for num in delimiter_counts:
        if abs(num - average) > allowed_deviation:
            return None

    # Boost confidence if filename ends with .csv
    if str(file_path).lower().endswith('.csv'):
        confidence = min(1.0, confidence + 0.1)

    # Return match with appropriate confidence
    delimiter_name = {
        ',': 'comma',
        ';': 'semicolon',
        '\t': 'tab',
        '|': 'pipe',
        ':': 'colon'
    }.get(best_delimiter, best_delimiter)

    return Match(
        ".csv",
        f"{delimiter_name}-separated values",
        "text/csv",
        confidence=confidence
    )

def file_ending_match(extension, text, mime, file_path):
    return Match(extension, text, mime, confidence=1.0 if str(file_path).lower().endswith(extension) else 0.9)

def dynamic_checks(text, file_path) -> Match | None:
    text = text.strip()
    if text.startswith("$MeshFormat"):
        return file_ending_match(".msh", "Gmsh mesh format", "text/plain", file_path)
    if "GenePix ArrayList" in text[:256]:
        return file_ending_match(".gal", "Gal GenePix ArrayList", "text/plain", file_path)
    if text.startswith("##gff-version"):
        return file_ending_match(".gff", "GFF3", "text/plain", file_path)
    if "GenePix Results" in text[:256]:
        return file_ending_match(".gpr", "GenePix Results", "text/plain", file_path)
    if "mzTab-version" in text[:256]:
        if "mzTab-version	2" in text[:256]:
            return file_ending_match(".mztab2", "mzTab version 2", "text/plain", file_path)
        return file_ending_match(".mztab", "mzTab", "text/plain", file_path)
    if text.startswith("***tesr"):
        return file_ending_match(".tesr", "Neper tesr format", "text/plain", file_path)
    if text.startswith("***tess"):
        return file_ending_match(".tess", "Neper tess format", "text/plain", file_path)
    if text.startswith("# PEFF "):
        # consider adding r"# PEFF \d+.\d+"
        return file_ending_match(".peff", "PSI Extended FASTA Format", "text/plain", file_path)
    if text.startswith("ply") and "format ascii" in text[:128]:
        return file_ending_match(".plyascii", "PLY mesh format", "text/plain", file_path)
    if text.startswith("RBT_PARAMETER_FILE_V"):
        return file_ending_match(".prm", "prm", "text/plain", file_path)
    if "# vtk DataFile" in text[:256]:
        return file_ending_match(".vtkascii", "vtk", "text/plain", file_path)
    if "<VTKFile " in text[:256]:
        return file_ending_match(".vtpascii", "vtpascii", "text/plain", file_path)
    if text.startswith("# CMAP File "):
        return file_ending_match(".cmap", "cmap", "text/plain", file_path)

    return None

def main(file_path: os.PathLike | str, _, __) -> Match | None:
    with open(file_path, "rb") as file:
        head = file.read(1_000_000)

    if len(head) < 8:
        return Match("", "very short file", "application/octet-stream", confidence=0.5)

    try:
        text, encoding = decode_any(head)
    except TypeError:
        return Match("", "data", "application/octet-stream", confidence=0.5)

    if csv_match := csv_check(file_path, text):
        return csv_match

    if obscure_match := dynamic_checks(text, file_path):
        return obscure_match

    crlf = len(crlf_pattern.findall(text))
    lf = len(lf_pattern.findall(text))
    cr = len(cr_pattern.findall(text))
    if crlf + lf + cr == 0:
        return Match(".txt", f"{encoding} text", "text/plain", confidence=0.9)

    if crlf > lf and crlf > cr:
        return Match(".txt", f"{encoding} text, with CRLF line terminators", "text/plain", confidence=0.9)
    if cr > lf and cr > crlf:
        return Match(".txt", f"{encoding} text, with CR line terminators", "text/plain", confidence=0.9)
    if lf > cr and lf > crlf:
        return Match(".txt", f"{encoding} text, with LF line terminators", "text/plain", confidence=0.9)
    return Match(".txt", f"{encoding} text", "text/plain", confidence=0.9)
