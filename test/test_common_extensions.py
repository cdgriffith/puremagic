import unittest
import puremagic
from tempfile import NamedTemporaryFile
import os

LOCAL_DIR = os.path.realpath(os.path.dirname(__file__))
IMAGE_DIR = os.path.join(LOCAL_DIR, "resources", "images")
VIDEO_DIR = os.path.join(LOCAL_DIR, "resources", "video")
AUDIO_DIR = os.path.join(LOCAL_DIR, "resources", "audio")
OFFICE_DIR = os.path.join(LOCAL_DIR, "resources", "office")
ARCHIVE_DIR = os.path.join(LOCAL_DIR, "resources", "archive")
MEDIA_DIR = os.path.join(LOCAL_DIR, "resources", "media")
SYSTEM_DIR = os.path.join(LOCAL_DIR, "resources", "system")


class TestMagic(unittest.TestCase):

    def setUp(self):
        self.mp4magic = "\x00\x00\x00\x1C\x66\x74\x79\x70\x4D\x53\x4E\x56\x01\x29\x00\x46\x4D\x53\x4E\x56\x6D\x70\x34\x32"
        self.expect_ext = ".mp4"
        self.expect_mime = "video/mp4"
    
    def test_file(self):
        """File identifcation                           |"""
        mp4file = NamedTemporaryFile(delete=False)
        mp4file.write(self.mp4magic)
        mp4file.close()
        ext = puremagic.from_file(mp4file.name)
        os.unlink(mp4file.name)
        self.assertEqual(self.expect_ext, ext)
        
    def test_hex_string(self):
        """Hex string identifcation                     |"""
        ext = puremagic.from_string(self.mp4magic)
        self.assertEqual(self.expect_ext, ext)
        
    def test_string(self):
        """String identifcation                         |"""
        ext = puremagic.from_string(str(self.mp4magic))
        self.assertEqual(self.expect_ext, ext)
        
    def test_not_found(self):
        """Bad file type via string                     |"""
        with self.assertRaises(LookupError):
            puremagic.from_string("not applicable string")
       
    def test_images(self):
        """Test common image formats                    |"""
        for item in os.listdir(IMAGE_DIR):
            try:
                result = puremagic.from_file(os.path.join(IMAGE_DIR, item))
                self.assertTrue(item.endswith(result))
            except Exception as e:
                self.fail(str(e) + item)

    def test_video(self):
        """Test common video formats                    |"""
        for item in os.listdir(VIDEO_DIR):
            try:
                puremagic.from_file(os.path.join(VIDEO_DIR, item))
            except Exception as e:
                self.fail(str(e) + item)
                
    def test_audio(self):
        """Test common audio formats                    |"""
        for item in os.listdir(AUDIO_DIR):
            try:
                puremagic.from_file(os.path.join(AUDIO_DIR, item))
            except Exception as e:
                self.fail(str(e) + item)
                
    def test_office(self):
        """Test common office document formats          |"""
        for item in os.listdir(OFFICE_DIR):
            try:
                puremagic.from_file(os.path.join(OFFICE_DIR, item))
            except Exception as e:
                self.fail(str(e) + item)
                
    def test_archive(self):
        """Test common compressed archive formats       |"""
        for item in os.listdir(ARCHIVE_DIR):
            try:
                puremagic.from_file(os.path.join(ARCHIVE_DIR, item))
            except Exception as e:
                self.fail(str(e) + item)
                
    def test_media(self):
        """Test common media formats                    |"""
        for item in os.listdir(MEDIA_DIR):
            try:
                puremagic.from_file(os.path.join(MEDIA_DIR, item))
            except Exception as e:
                self.fail(str(e) + item)
                
    def test_system(self):
        """Test common system formats                   |"""
        for item in os.listdir(SYSTEM_DIR):
            try:
                puremagic.from_file(os.path.join(SYSTEM_DIR, item))
            except Exception as e:
                self.fail(str(e) + item)


suite = unittest.TestLoader().loadTestsFromTestCase(TestMagic)
unittest.TextTestRunner(verbosity=2).run(suite)