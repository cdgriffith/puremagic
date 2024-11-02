from __future__ import annotations

import re
import os
from typing import Optional
from zipfile import ZipFile

from puremagic.scanners.helpers import Match

match_bytes = b"PK\x03\x04"
office_macro_enable_match = b"macroEnabled"

application_re = re.compile(b"<Application>(.*)</Application>")


def open_office_check(internal_files: list[str], zip_file: ZipFile, extension: str | None = None) -> Optional[Match]:
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


def office_check(internal_files: list[str], zip_file: ZipFile, extension: str | None = None) -> Optional[Match]:
    if "[Content_Types].xml" not in internal_files:
        return None
    if "docProps/app.xml" not in internal_files:
        return None
    app_type_matches = application_re.search(zip_file.read("docProps/app.xml"))
    if not app_type_matches:
        return None
    application_type = app_type_matches.group(1).decode("utf-8")

    if "PowerPoint" in application_type:
        if extension:
            if extension == "ppsm":
                return Match(".ppsm", application_type, "application/vnd.ms-powerpoint.slideshow.macroEnabled.12")
            if extension == "potm":
                return Match(".potm", application_type, "application/vnd.ms-powerpoint.template.macroEnabled.12")
            if extension == "potx":
                return Match(
                    "potx",
                    application_type,
                    "application/vnd.openxmlformats-officedocument.presentationml.template",
                )
            if extension == "ppam":
                return Match(".ppam", application_type, "application/vnd.ms-powerpoint.addin.macroEnabled")
        if office_macro_enable_match in zip_file.read("[Content_Types].xml"):
            return Match(".ppsm", application_type, "application/vnd.ms-powerpoint.slideshow.macroEnabled.12")
        return Match(
            "pptx",
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
                    "xltx",
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
                    "dotx",
                    application_type,
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.template",
                )
        if office_macro_enable_match in zip_file.read("[Content_Types].xml"):
            return Match(".docm", application_type, "application/vnd.ms-word.document.macroEnabled.12")
        return Match(
            "docx", application_type, "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

    return None


def jar_check(internal_files: list[str], zip_file: ZipFile) -> Optional[Match]:

    if "META-INF/MANIFEST.MF" not in internal_files:
        return None
    if "version.json" not in internal_files:
        return None

    if b'"java_version":' in zip_file.read("version.json"):
        return Match(".jar", "Java Archive", "application/java-archive")
    return None


def apk_check(internal_files: list[str]) -> Optional[Match]:
    if "META-INF/MANIFEST.MF" not in internal_files:
        return None
    if "AndroidManifest.xml" in internal_files:
        return Match(".apk", "Android Package", "application/vnd.android.package-archive")
    return None


def xpi_check(internal_files: list[str], zip_file: ZipFile) -> Optional[Match]:
    if "install.rdf" in internal_files and b"mozilla:install-manifest" in zip_file.read("install.rdf"):
        return Match(".xpi", "Mozilla Firefox Add-on", "application/x-xpinstall")
    return None


def fb2_check(internal_files: list[str], zip_file: ZipFile, extension: Optional[str] = None) -> Optional[Match]:
    if (
        len(internal_files) == 1
        and internal_files[0].endswith(".fb2")
        and b"<FictionBook" in zip_file.read(internal_files[0])
    ):
        if extension:
            if extension == "fb2.zip":
                return Match(".fb2.zip", "FictionBook", "application/x-fictionbook+xml")
            if extension == "fbz":
                return Match(".fbz", "FictionBook", "application/x-fictionbook+xml")
        return Match(".fb2.zip", "FictionBook", "application/x-fictionbook+xml")

    return None


def cbz_check(internal_files: list[str], extension: str) -> Optional[Match]:
    if extension != "cbz":
        return None
    image_extensions = (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".tif")
    for file in internal_files:
        if not file.lower().endswith(image_extensions):
            return None
    return Match(".cbz", "Comic Book Archive", "application/vnd.comicbook+zip")


def main(file_path: os.PathLike, _, __) -> Optional[Match]:
    extension = str(file_path).split(".")[-1].lower()
    if extension == "zip" and not str(file_path).endswith(".fb2.zip"):
        return Match(".zip", "ZIP archive", "application/zip")

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

        fb_result = fb2_check(internal_files, myzip, extension)
        if fb_result:
            return fb_result

        cbz_result = cbz_check(internal_files, extension)
        if cbz_result:
            return cbz_result

        return None
