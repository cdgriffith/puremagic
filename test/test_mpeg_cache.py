import os
import shutil

import puremagic
from test.common import AUDIO_DIR


def test_mp3_cache_invalidated_when_file_rewritten(tmp_path):
    """#169: a file rewritten in place at the same path must be scanned again."""
    corrupt = b"\xff\xfb" + b"\x00" * 100

    control = tmp_path / "control.mp3"
    control.write_bytes(corrupt)
    expected_corrupt = puremagic.from_file(control)
    assert expected_corrupt != ".mp3"

    target = tmp_path / "rewritten.mp3"
    shutil.copyfile(AUDIO_DIR / "test.mp3", target)
    assert puremagic.from_file(target) == ".mp3"

    target.write_bytes(corrupt)
    # Guarantee a different mtime even on filesystems with coarse timestamps
    stat = os.stat(target)
    os.utime(target, ns=(stat.st_atime_ns, stat.st_mtime_ns + 2_000_000_000))
    assert puremagic.from_file(target) == expected_corrupt


def test_mp3_cache_reused_for_unchanged_file(tmp_path):
    target = tmp_path / "same.mp3"
    shutil.copyfile(AUDIO_DIR / "test.mp3", target)
    first = puremagic.magic_file(target)
    second = puremagic.magic_file(target)
    assert first == second
    assert first[0].extension == ".mp3"
