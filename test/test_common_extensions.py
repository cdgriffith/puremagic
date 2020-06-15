import unittest
from tempfile import NamedTemporaryFile
import os
from io import BytesIO

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
        for item in os.listdir(directory):
            print(item)
            try:
                ext = puremagic.from_file(os.path.join(directory, item))
            except puremagic.PureError:
                failures.append(item)
            else:
                if not item.endswith(ext):
                    ext_failures.append((item, ext))
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

    def test_file(self):
        """File identification                          |"""
        mp4file = NamedTemporaryFile(delete=False)
        mp4file.write(self.mp4magic)
        mp4file.close()
        ext = puremagic.from_file(mp4file.name)
        os.unlink(mp4file.name)
        self.assertEqual(self.expect_ext, ext)

    def test_hex_string(self):
        """Hex string identification                    |"""
        ext = puremagic.from_string(self.mp4magic)
        self.assertEqual(self.expect_ext, ext)

    def test_string(self):
        """String identification                        |"""
        ext = puremagic.from_string(bytes(self.mp4magic))
        self.assertEqual(self.expect_ext, ext)

    def test_string_with_filename_hint(self):
        """String identification with filename hint     |"""
        filename = os.path.join(OFFICE_DIR, "test.xlsx")
        with open(filename, "rb") as f:
            data = f.read()
        ext = puremagic.from_string(data)
        # .docx and .xlsx have same signature
        self.assertEqual(".docx", ext)
        # with the hint from_string() shoud find the correct extension
        ext = puremagic.from_string(data, filename=filename)
        self.assertEqual(".xlsx", ext)

    def test_string_with_confidence(self):
        """String identification: magic_string          |"""
        ext = puremagic.magic_string(bytes(self.mp4magic))
        self.assertEqual(self.expect_ext, ext[0].extension)
        self.assertRaises(ValueError, puremagic.magic_string, "")

    def test_magic_string_with_filename_hint(self):
        """String identification: magic_string with hint|"""
        filename = os.path.join(OFFICE_DIR, "test.xlsx")
        with open(filename, "rb") as f:
            data = f.read()
        ext = puremagic.magic_string(data, filename=filename)
        self.assertEqual(".xlsx", ext[0].extension)

    def test_not_found(self):
        """Bad file type via string                     |"""
        try:
            with self.assertRaises(puremagic.PureError):
                puremagic.from_string("not applicable string")
        except TypeError:
            # Python 2.6 doesn't support using
            # assertRaises as a context manager
            pass

    def test_magic_file(self):
        """File identification with magic_file          |"""
        self.assertEqual(puremagic.magic_file(TGA_FILE)[0].extension, ".tga")
        open("test_empty_file", "w").close()
        try:
            self.assertRaises(ValueError, puremagic.magic_file, "test_empty_file")
        finally:
            os.unlink("test_empty_file")

    def test_stream(self):
        """Stream identification                        |"""
        ext = puremagic.from_stream(BytesIO(self.mp4magic))
        self.assertEqual(self.expect_ext, ext)
        self.assertRaises(ValueError, puremagic.from_stream, BytesIO(b""))

    def test_mime(self):
        """Identify mime type                           |"""
        self.assertEqual(puremagic.from_file(TGA_FILE, True), "image/tga")

    def test_images(self):
        """Test common image formats                    |"""
        self.group_test(IMAGE_DIR)

    def test_video(self):
        """Test common video formats                    |"""
        self.group_test(VIDEO_DIR)

    def test_audio(self):
        """Test common audio formats                    |"""
        self.group_test(AUDIO_DIR)

    def test_office(self):
        """Test common office document formats          |"""
        # Office files have very similar magic numbers, and may overlap
        for item in os.listdir(OFFICE_DIR):
            puremagic.from_file(os.path.join(OFFICE_DIR, item))

    def test_archive(self):
        """Test common compressed archive formats       |"""
        # pcapng files from https://wiki.wireshark.org/Development/PcapNg
        self.group_test(ARCHIVE_DIR)

    def test_media(self):
        """Test common media formats                    |"""
        self.group_test(MEDIA_DIR)

    def test_system(self):
        """Test common system formats                   |"""
        self.group_test(SYSTEM_DIR)

    def test_ext(self):
        """Test ext from filename                       |"""
        ext = puremagic.ext_from_filename("test.tar.bz2")
        assert ext == ".tar.bz2", ext

    def test_cmd_options(self):
        """Test CLI options                             |"""
        from puremagic.main import command_line_entry

        command_line_entry(__file__, "test.py")


if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestMagic)
    unittest.TextTestRunner(verbosity=2).run(suite)
