import os
from pathlib import Path

LOCAL_DIR = Path(os.path.realpath(os.path.dirname(__file__)))
RESOURCE_DIR = Path(os.path.join(LOCAL_DIR, "resources"))
IMAGE_DIR = Path(os.path.join(LOCAL_DIR, "resources", "images"))
VIDEO_DIR = Path(os.path.join(LOCAL_DIR, "resources", "video"))
AUDIO_DIR = Path(os.path.join(LOCAL_DIR, "resources", "audio"))
OFFICE_DIR = Path(os.path.join(LOCAL_DIR, "resources", "office"))
ARCHIVE_DIR = Path(os.path.join(LOCAL_DIR, "resources", "archive"))
MEDIA_DIR = Path(os.path.join(LOCAL_DIR, "resources", "media"))
SYSTEM_DIR = Path(os.path.join(LOCAL_DIR, "resources", "system"))
