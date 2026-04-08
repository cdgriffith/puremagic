import re
import os
from zipfile import ZipFile

from puremagic.scanners.helpers import Match

match_bytes = b"PK\x03\x04"
office_macro_enable_match = b"macroEnabled"

application_re = re.compile(b"<Application>(.*)</Application>")
_content_type_re = re.compile(rb'ContentType="([^"]*main[^"]*)"')

# Maps OOXML main content type fragments (from [Content_Types].xml) to
# (extension, name, mime_type). Based on ECMA-376 Part 2.
_OOXML_CONTENT_TYPE_MAP: dict[str, tuple[str, str, str]] = {
    # Word
    "wordprocessingml.document.main+xml": (
        ".docx",
        "Word Document",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ),
    "wordprocessingml.template.main+xml": (
        ".dotx",
        "Word Template",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.template",
    ),
    "ms-word.document.macroEnabled.main+xml": (
        ".docm",
        "Word Document (Macro-Enabled)",
        "application/vnd.ms-word.document.macroEnabled.12",
    ),
    "ms-word.template.macroEnabledTemplate.main+xml": (
        ".dotm",
        "Word Template (Macro-Enabled)",
        "application/vnd.ms-word.template.macroEnabled.12",
    ),
    # Excel
    "spreadsheetml.sheet.main+xml": (
        ".xlsx",
        "Excel Spreadsheet",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ),
    "spreadsheetml.template.main+xml": (
        ".xltx",
        "Excel Template",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.template",
    ),
    "ms-excel.sheet.macroEnabled.main+xml": (
        ".xlsm",
        "Excel Spreadsheet (Macro-Enabled)",
        "application/vnd.ms-excel.sheet.macroEnabled.12",
    ),
    "ms-excel.template.macroEnabled.main+xml": (
        ".xltm",
        "Excel Template (Macro-Enabled)",
        "application/vnd.ms-excel.template.macroEnabled.12",
    ),
    "ms-excel.sheet.binary.macroEnabled.main": (
        ".xlsb",
        "Excel Binary Workbook",
        "application/vnd.ms-excel.sheet.binary.macroEnabled.12",
    ),
    "ms-excel.addin.macroEnabled.main+xml": (
        ".xlam",
        "Excel Add-In (Macro-Enabled)",
        "application/vnd.ms-excel.addin.macroEnabled.12",
    ),
    # PowerPoint
    "presentationml.presentation.main+xml": (
        ".pptx",
        "PowerPoint Presentation",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ),
    "presentationml.template.main+xml": (
        ".potx",
        "PowerPoint Template",
        "application/vnd.openxmlformats-officedocument.presentationml.template",
    ),
    "ms-powerpoint.presentation.macroEnabled.main+xml": (
        ".pptm",
        "PowerPoint Presentation (Macro-Enabled)",
        "application/vnd.ms-powerpoint.presentation.macroEnabled.12",
    ),
    "ms-powerpoint.template.macroEnabled.main+xml": (
        ".potm",
        "PowerPoint Template (Macro-Enabled)",
        "application/vnd.ms-powerpoint.template.macroEnabled.12",
    ),
    "presentationml.slideshow.main+xml": (
        ".ppsx",
        "PowerPoint Slideshow",
        "application/vnd.openxmlformats-officedocument.presentationml.slideshow",
    ),
    "ms-powerpoint.slideshow.macroEnabled.main+xml": (
        ".ppsm",
        "PowerPoint Slideshow (Macro-Enabled)",
        "application/vnd.ms-powerpoint.slideshow.macroEnabled.12",
    ),
    "ms-powerpoint.addin.macroEnabled.main+xml": (
        ".ppam",
        "PowerPoint Add-In (Macro-Enabled)",
        "application/vnd.ms-powerpoint.addin.macroEnabled",
    ),
}


def _detect_from_content_types(zip_file: ZipFile) -> Match | None:
    """Detect OOXML format from [Content_Types].xml main content types.

    This is the ECMA-376 standard approach, working with all compliant
    implementations (Microsoft Office, LibreOffice, Google Docs, etc.).
    """
    try:
        ct_data = zip_file.read("[Content_Types].xml")
    except KeyError:
        return None

    for match in _content_type_re.finditer(ct_data):
        content_type = match.group(1).decode("utf-8")
        for key, (ext, name, mime) in _OOXML_CONTENT_TYPE_MAP.items():
            if key in content_type:
                return Match(ext, name, mime)

    return None


def open_office_check(internal_files: list[str], zip_file: ZipFile, extension: str | None = None) -> Match | None:
    if "content.xml" not in internal_files:
        return None
    if "mimetype" not in internal_files:
        return None

    known_extensions = ["odt", "ods", "odp", "sxd", "sxi", "sxw"]

    mime_type = zip_file.read("mimetype").decode("utf-8").strip()

    if "application/vnd.oasis.opendocument.text" in mime_type:
        return Match(".odt", "OpenDocument Text Document", "application/vnd.oasis.opendocument.text")
    if "application/vnd.oasis.opendocument.spreadsheet" in mime_type:
        return Match(".ods", "OpenDocument Spreadsheet", "application/vnd.oasis.opendocument.spreadsheet")
    if "application/vnd.oasis.opendocument.presentation" in mime_type:
        return Match(".odp", "OpenDocument Presentation", "application/vnd.oasis.opendocument.presentation")
    if extension in known_extensions and mime_type.startswith("application/vnd.oasis.opendocument"):
        return Match(extension, "OpenDocument", mime_type)

    return None


def _detect_from_application(
    internal_files: list[str], zip_file: ZipFile, extension: str | None = None
) -> Match | None:
    """Fallback detection using docProps/app.xml Application tag."""
    if "docProps/app.xml" not in internal_files:
        return None
    app_type_matches = application_re.search(zip_file.read("docProps/app.xml"))
    if not app_type_matches:
        return None
    application_type = app_type_matches.group(1).decode("utf-8")

    if "PowerPoint" in application_type:
        if extension:
            if extension == "pptm":
                return Match(".pptm", application_type, "application/vnd.ms-powerpoint.presentation.macroEnabled.12")
            if extension == "ppsm":
                return Match(".ppsm", application_type, "application/vnd.ms-powerpoint.slideshow.macroEnabled.12")
            if extension == "ppsx":
                return Match(
                    ".ppsx",
                    application_type,
                    "application/vnd.openxmlformats-officedocument.presentationml.slideshow",
                )
            if extension == "potm":
                return Match(".potm", application_type, "application/vnd.ms-powerpoint.template.macroEnabled.12")
            if extension == "potx":
                return Match(
                    ".potx",
                    application_type,
                    "application/vnd.openxmlformats-officedocument.presentationml.template",
                )
            if extension == "ppam":
                return Match(".ppam", application_type, "application/vnd.ms-powerpoint.addin.macroEnabled")
        if office_macro_enable_match in zip_file.read("[Content_Types].xml"):
            return Match(".pptm", application_type, "application/vnd.ms-powerpoint.presentation.macroEnabled.12")
        return Match(
            ".pptx",
            application_type,
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        )
    if "Excel" in application_type:
        if extension:
            if extension == "xlsm":
                return Match(".xlsm", application_type, "application/vnd.ms-excel.sheet.macroEnabled.12")
            if extension == "xlsb":
                return Match(".xlsb", application_type, "application/vnd.ms-excel.sheet.binary.macroEnabled.12")
            if extension == "xlam":
                return Match(".xlam", application_type, "application/vnd.ms-excel.addin.macroEnabled.12")
            if extension == "xltm":
                return Match(".xltm", application_type, "application/vnd.ms-excel.template.macroEnabled.12")
            if extension == "xltx":
                return Match(
                    ".xltx",
                    application_type,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.template",
                )
        if office_macro_enable_match in zip_file.read("[Content_Types].xml"):
            return Match(".xlsm", application_type, "application/vnd.ms-excel.sheet.macroEnabled.12")

        return Match(".xlsx", application_type, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    if "Word" in application_type:
        if extension:
            if extension == "docm":
                return Match(".docm", application_type, "application/vnd.ms-word.document.macroEnabled.12")
            if extension == "dotm":
                return Match(".dotm", application_type, "application/vnd.ms-word.template.macroEnabled.12")
            if extension == "dotx":
                return Match(
                    ".dotx",
                    application_type,
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.template",
                )
        if office_macro_enable_match in zip_file.read("[Content_Types].xml"):
            return Match(".docm", application_type, "application/vnd.ms-word.document.macroEnabled.12")
        return Match(
            ".docx", application_type, "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

    return None


def office_check(internal_files: list[str], zip_file: ZipFile, extension: str | None = None) -> Match | None:
    if "[Content_Types].xml" not in internal_files:
        return None

    # Primary: content-type-based detection (works with all OOXML creators)
    result = _detect_from_content_types(zip_file)
    if result:
        return result

    # Fallback: application-based detection for non-standard OOXML packages
    return _detect_from_application(internal_files, zip_file, extension)


def jar_check(internal_files: list[str], zip_file: ZipFile) -> Match | None:
    if "META-INF/MANIFEST.MF" not in internal_files:
        return None
    if "version.json" not in internal_files:
        return None

    if b'"java_version":' in zip_file.read("version.json"):
        return Match(".jar", "Java Archive", "application/java-archive")
    return None


def apk_check(internal_files: list[str]) -> Match | None:
    if "META-INF/MANIFEST.MF" not in internal_files:
        return None
    if "AndroidManifest.xml" in internal_files:
        return Match(".apk", "Android Package", "application/vnd.android.package-archive")
    return None


def xpi_check(internal_files: list[str], zip_file: ZipFile) -> Match | None:
    if "install.rdf" in internal_files and b"mozilla:install-manifest" in zip_file.read("install.rdf"):
        return Match(".xpi", "Mozilla Firefox Add-on", "application/x-xpinstall")
    return None


def fb2_check(internal_files: list[str], zip_file: ZipFile, file_path: os.PathLike) -> Match | None:
    if (
        len(internal_files) == 1
        and internal_files[0].endswith(".fb2")
        and b"<FictionBook" in zip_file.read(internal_files[0])
    ):
        if str(file_path).endswith("fb2.zip"):
            return Match(".fb2.zip", "FictionBook", "application/x-fictionbook+xml")
        if str(file_path).endswith("fbz"):
            return Match(".fbz", "FictionBook", "application/x-fictionbook+xml")
        return Match(".fb2.zip", "FictionBook", "application/x-fictionbook+xml")

    return None


def cbz_check(internal_files: list[str], extension: str) -> Match | None:
    if extension != "cbz":
        return None
    image_extensions = (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".tif")
    for file in internal_files:
        if not file.lower().endswith(image_extensions):
            return None
    return Match(".cbz", "Comic Book Archive", "application/vnd.comicbook+zip")


def main(file_path: os.PathLike, _, __) -> Match | None:
    extension = str(file_path).split(".")[-1].lower()

    with ZipFile(file_path) as myzip:
        internal_files = myzip.namelist()
        office_result = office_check(internal_files, myzip, extension)
        if office_result:
            return office_result

        open_office_result = open_office_check(internal_files, myzip)
        if open_office_result:
            return open_office_result

        jar_result = jar_check(internal_files, myzip)
        if jar_result:
            return jar_result

        apk_result = apk_check(internal_files)
        if apk_result:
            return apk_result

        xpi_result = xpi_check(internal_files, myzip)
        if xpi_result:
            return xpi_result

        fb_result = fb2_check(internal_files, myzip, file_path)
        if fb_result:
            return fb_result

        cbz_result = cbz_check(internal_files, extension)
        if cbz_result:
            return cbz_result

        # No specific format detected — return generic ZIP (same confidence as other matches)
        return Match(".zip", "ZIP archive", "application/zip")
