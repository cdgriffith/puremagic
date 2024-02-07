# -*- coding: utf-8 -*-
import unittest
from tempfile import NamedTemporaryFile
import os
from io import BytesIO
import pytest
from pathlib import Path

import puremagic

LOCAL_DIR = os.path.realpath(os.path.dirname(__file__))
IMAGE_DIR = os.path.join(LOCAL_DIR, "resources", "images")
VIDEO_DIR = os.path.join(LOCAL_DIR, "resources", "video")
AUDIO_DIR = os.path.join(LOCAL_DIR, "resources", "audio")
OFFICE_DIR = os.path.join(LOCAL_DIR, "resources", "office")
ARCHIVE_DIR = os.path.join(LOCAL_DIR, "resources", "archive")
MEDIA_DIR = os.path.join(LOCAL_DIR, "resources", "media")
SYSTEM_DIR = os.path.join(LOCAL_DIR, "resources", "system")
TGA_FILE = os.path.join(IMAGE_DIR, "test.tga")


class TestMagic(unittest.TestCase):
    def setUp(self):
        self.mp4magic = b"\x00\x00\x00\x1C\x66\x74\x79\x70\x4D\x53\x4E\
\x56\x01\x29\x00\x46\x4D\x53\x4E\x56\x6D\x70\x34\x32"
        self.expect_ext = ".mp4"
        self.expect_mime = "video/mp4"

    def group_test(self, directory):
        failures = []
        ext_failures = []
        mime_failures = []
        for item in os.listdir(directory):
            try:
                ext = puremagic.from_file(os.path.join(directory, item))
            except puremagic.PureError:
                failures.append(item)
            else:
                if not item.endswith(ext):
                    ext_failures.append((item, ext))

            try:
                mime = puremagic.from_file(os.path.join(directory, item), mime=True)
            except puremagic.PureError:
                failures.append(item)
            else:
                if not mime:
                    mime_failures.append(item)
        if failures:
            raise AssertionError(
                "The following items could not be identified from the {} folder: {}".format(
                    directory, ", ".join(failures)
                )
            )
        if ext_failures:
            raise AssertionError(
                "The following files did not have the expected extensions: {}".format(
                    ", ".join(['"{}" expected "{}"'.format(item, ext) for item, ext in ext_failures])
                )
            )
        if mime_failures:
            raise AssertionError("The following files did not have a mime type: {}".format(", ".join(mime_failures)))

    def test_file(self):
        """File identification"""
        mp4file = NamedTemporaryFile(delete=False)
        mp4file.write(self.mp4magic)
        mp4file.close()
        ext = puremagic.from_file(mp4file.name)
        os.unlink(mp4file.name)
        self.assertEqual(self.expect_ext, ext)

    def test_hex_string(self):
        """Hex string identification"""
        ext = puremagic.from_string(self.mp4magic)
        self.assertEqual(self.expect_ext, ext)

    def test_string(self):
        """String identification"""
        ext = puremagic.from_string(bytes(self.mp4magic))
        self.assertEqual(self.expect_ext, ext)

    def test_string_with_confidence(self):
        """String identification: magic_string"""
        ext = puremagic.magic_string(bytes(self.mp4magic))
        self.assertEqual(self.expect_ext, ext[0].extension)
        self.assertRaises(ValueError, puremagic.magic_string, "")

    def test_magic_string_with_filename_hint(self):
        """String identification: magic_string with hint"""
        filename = os.path.join(OFFICE_DIR, "test.xlsx")
        with open(filename, "rb") as f:
            data = f.read()
        ext = puremagic.magic_string(data, filename=filename)
        self.assertEqual(".xlsx", ext[0].extension)

    def test_not_found(self):
        """Bad file type via string"""
        try:
            with self.assertRaises(puremagic.PureError):
                puremagic.from_string("not applicable string")
        except TypeError:
            # Python 2.6 doesn't support using
            # assertRaises as a context manager
            pass

    def test_magic_file(self):
        """File identification with magic_file"""
        self.assertEqual(puremagic.magic_file(TGA_FILE)[0].extension, ".tga")
        open("test_empty_file", "w").close()
        try:
            self.assertRaises(ValueError, puremagic.magic_file, "test_empty_file")
        finally:
            os.unlink("test_empty_file")

    def test_stream(self):
        """Stream identification"""
        ext = puremagic.from_stream(BytesIO(self.mp4magic))
        self.assertEqual(self.expect_ext, ext)
        self.assertRaises(ValueError, puremagic.from_stream, BytesIO(b""))

    def test_magic_stream(self):
        """File identification with magic_stream"""
        with open(TGA_FILE, "rb") as f:
            stream = BytesIO(f.read())
        result = puremagic.magic_stream(stream, TGA_FILE)
        self.assertEqual(result[0].extension, ".tga")
        self.assertRaises(ValueError, puremagic.magic_stream, BytesIO(b""))

    def test_mime(self):
        """Identify mime type"""
        self.assertEqual(puremagic.from_file(TGA_FILE, True), "image/tga")

    def test_images(self):
        """Test common image formats"""
        self.group_test(IMAGE_DIR)

    def test_video(self):
        """Test common video formats"""
        self.group_test(VIDEO_DIR)

    def test_audio(self):
        """Test common audio formats"""
        self.group_test(AUDIO_DIR)

    def test_office(self):
        """Test common office document formats"""
        # Office files have very similar magic numbers, and may overlap
        for item in os.listdir(OFFICE_DIR):
            puremagic.from_file(os.path.join(OFFICE_DIR, item))

    def test_archive(self):
        """Test common compressed archive formats"""
        # pcapng files from https://wiki.wireshark.org/Development/PcapNg
        self.group_test(ARCHIVE_DIR)

    def test_media(self):
        """Test common media formats"""
        self.group_test(MEDIA_DIR)

    def test_system(self):
        """Test common system formats"""
        self.group_test(SYSTEM_DIR)

    def test_ext(self):
        """Test ext from filename"""
        ext = puremagic.ext_from_filename("test.tar.bz2")
        assert ext == ".tar.bz2", ext

    def test_cmd_options(self):
        """Test CLI options"""
        from puremagic.main import command_line_entry

        command_line_entry(__file__, "test.py")

    def test_bad_magic_input(self):
        """Test bad magic imput"""
        with pytest.raises(ValueError):
            puremagic.main._magic(None, None, None)

    def test_fake_file(self):
        assert puremagic.magic_file(filename=Path(LOCAL_DIR, "resources", "fake_file")) == []


if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestMagic)
    unittest.TextTestRunner(verbosity=2).run(suite)
