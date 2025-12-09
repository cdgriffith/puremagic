# cSpell:disable

"""
MPEG Audio Deep Scanner (MP1, MP2, MP3).

This performs a frame-by-frame check-up to confirm if it's a bonafide MP3
A successful match is only returned if the main MPEG audio data stream can be decoded correctly.
*AND* if present an ID3v2 (which needs decoding to find the audio afterwards).

The scanner quickly pulls out all the crucial stream details:
    * **Sample Rate**
    * **Bit Rate**
    * **Bitrate Mode** (CBR/VBR)
    * **Channel Mode** (Mono/Stereo)
    * **Metadata Tag Styles**

Note on Tags:
    End-of-file metadata tags (like ID3v1 or APE) are checked purely for informational
    purposes and **do not influence the file's pass/fail status**. We include tolerance
    for these EOF tags even if they are placed in non-spec-compliant locations.
"""

import os
import struct
from typing import IO, Any, Dict, List, Optional

from puremagic.scanners.helpers import Match

"""These are all the valid signatures for raw MPEG Audio streams (Layers I, II, III), or those starting with a ID3v2 tag."""
mpeg_audio_signatures = [
    # The 'ID3' tag identifies a separate metadata block (like song title/artist)
    # that often precedes the actual MPEG audio data. It is not an audio frame header.
    b"ID3",  # ID3 Tag (Metadata header)
    b"\xff\xfb",  # MPEG 1, Layer 3 (MP3), Protected (CRC used)
    b"\xff\xfe",  # MPEG 1, Layer 3 (MP3), Reserved/Invalid Bit
    b"\xff\xff",  # MPEG 1, Layer 3 (MP3), Reserved/Invalid Bit
    b"\xff\xfc",  # MPEG 1, Layer 2, Protected (CRC used)
    b"\xff\xfd",  # MPEG 1, Layer 3, No Protection (CRC not used)
    b"\xff\xfa",  # MPEG 1, Layer 3 (MP3), Protected (CRC used)
    b"\xff\xf6",  # MPEG 1, Layer 2, No Protection (CRC not used)
    b"\xff\xf7",  # MPEG 1, Layer 3 (MP3), No Protection (CRC not used)
    b"\xff\xf4",  # MPEG 1, Layer 2, Protected (CRC used)
    b"\xff\xf5",  # MPEG 1, Layer 3 (MP3), No Protection (CRC not used)
    b"\xff\xf2",  # MPEG 1, Layer 2, Protected (CRC used)
    b"\xff\xf3",  # MPEG 1, Layer 3 (MP3), No Protection (CRC not used)
    b"\xff\xe6",  # MPEG 2, Layer 3 (MP3), Protected (CRC used)
    b"\xff\xe7",  # MPEG 2, Layer 3 (MP3), No Protection (CRC not used)
    b"\xff\xe4",  # MPEG 2, Layer 2, Protected (CRC used)
    b"\xff\xe5",  # MPEG 2, Layer 3 (MP3), No Protection (CRC not used)
    b"\xff\xe2",  # MPEG 2, Layer 2, Protected (CRC used)
    b"\xff\xe3",  # MPEG 2, Layer 3 (MP3), No Protection (CRC not used)
]


class DataCache:
    """
    We use a data cache as puremagic calls the script more than once.

    Work is performed on first call, cached output is returned in subsequent calls.
    """

    _processed_result = None
    _file_path = None
    _matched = False

    @classmethod
    def set_result(cls, result):
        """Stores the result after processing."""
        cls._processed_result = result
        cls._matched = True

    @classmethod
    def set_file_path(cls, file_path: os.PathLike | str):
        """Stores the file_path and resets results."""
        cls._file_path = file_path
        cls._processed_result = None
        cls._matched = False

    @classmethod
    def get_result(cls):
        """Retrieves the stored result."""
        return cls._processed_result

    @classmethod
    def is_matched(cls) -> bool:
        """Retrieves the stored result."""
        return cls._matched

    @classmethod
    def get_file_path(cls) -> os.PathLike | str:
        """Retrieves the file path."""
        return cls._file_path

    @classmethod
    def is_cached(cls):
        """Checks if the result has been processed yet."""
        return cls._processed_result is not None


class EndOfFileTags:
    """Processes all end of file tags."""

    def __init__(self, file_size: int):
        self.tags = []
        self.file_size = file_size
        self.foot_string = None
        self.foot_size = 1572864  # 1.5MB in bytes, changes if file is smaller

    def _id3v1(self) -> bool:
        """
        Searches for ID3v1 TAG in last 128 bytes.

        Validation relies on the 'TAG' signature
        AND either a 4-digit year (1900-2100)
        OR four null bytes in the Year field
        OR four spaces (hex 20 used by non compliant encoders/taggers).

        Returns True so we can check for TAG+ or EXT.
        Returns None if tag is not valid, no point then checking above.
        """
        tag_size = 128

        if self.foot_size < tag_size:
            return False  # Too small to contain ID3v1 tag.

        try:
            find_tag_loc = self.foot_string.rfind(b"TAG")
            if find_tag_loc == -1:
                return False  # Tag not found

            tag_calc_size = self.foot_size - find_tag_loc
            if tag_calc_size != tag_size:
                return False  # Tag not 128 bytes

            # Year is stored at byte 93 and 97 of TAG
            # this should be a 4 digit number, or 4 nulls
            # but some crappy enocders use hex 20 (spaces)
            year = self.foot_string[find_tag_loc + 93 : find_tag_loc + 97]
            if year == b"\x00\x00\x00\x00" or year == b"\x20\x20\x20\x20":  # Check for empty year (all nulls)
                self.tags.append("ID3v1")
                return True
            try:
                year_str = year.decode("ascii", errors="ignore").replace("\x00", "").replace("\x20", "").strip()
                if len(year_str) == 4 and year_str.isdigit():  # Check for a plausible 4-digit year 1900-2100
                    year_int = int(year_str)
                    if 1900 <= year_int <= 2100:
                        self.tags.append("ID3v1")
                        return True
            except ValueError:
                pass

            return None  # Year could not be found

        except Exception:
            return None  # Other unexpected issues

    def _tag_plus(self) -> None:
        """
        Checks for the ID3v1 Enhanced Tag ('TAG+').

        This should be located in one fixed place at 355 bytes from end of file.
        There is a chance another tag (like APE or EXT) can push it around,
        which means the data could be there, but in the wrong place.

        Validation relies on the 'TAG+' signature, correct tag size,
        AND either the approved speed bytes (01=slow, 02=medium, 03=fast, 04=hardcore)
        OR a null byte (00) if unpopulated.

        Returns None as a graceful exit if TAG+ not found
        """
        tag_size = 128
        tag_plus_size = 227
        speed_loc = 184  # Speed byte posistion in tag
        combined_size = tag_plus_size + tag_size

        if self.foot_size < combined_size:  # TAG+ + ID3v1
            return None  # Too small to contain TAG+

        try:
            # Scan only calculated tag area, try to avoid false positives
            tag_start = self.foot_size - combined_size
            tag_end = tag_start + tag_plus_size
            find_tag_loc = self.foot_string.rfind(b"TAG+", tag_start, tag_end)
            if find_tag_loc == -1:
                return None  # Tag not found

            tag_calc_size = self.foot_size - find_tag_loc
            if tag_calc_size != combined_size:
                return None  # Tag+ not valid size

            speed_position = find_tag_loc + speed_loc
            if 0 <= self.foot_string[speed_position] <= 4:
                self.tags.append("TAG+")
            else:
                return None  # Speed byte not in range

        except Exception:
            return None  # Other unexpected issues

    def _ext_tag(self) -> None:
        """
        Checks for the ID3v1.2 Enhanced Tag ('EXT').

        This should be located in one fixed place at 256 bytes from end of file.
        There is a chance another tag (like APE or EXT) can push it around,
        which means the data could be there, but in the wrong place.

        Validation relies on the 'EXT' signature and correct tag size.
        Unable to validate further as tag has no fixed content.

        Returns None as a graceful exit if EXT not found
        """
        tag_size = 128
        ext_tag_size = 128
        combined_size = ext_tag_size + tag_size

        if self.foot_size < combined_size:  # EXT + ID3v1
            return None  # Too small to contain EXT

        try:
            # Scan only calculated tag area, try to avoid false positives
            tag_start = self.foot_size - combined_size
            tag_end = tag_start + ext_tag_size
            find_tag_loc = self.foot_string.rfind(b"EXT", tag_start, tag_end)
            if find_tag_loc == -1:
                return None  # Tag not found

            tag_calc_size = self.foot_size - find_tag_loc
            if tag_calc_size != combined_size:
                return None  # EXT not valid size
            else:
                self.tags.append("EXT")

        except Exception:
            return None  # Other unexpected issues

    def _3di(self, id3v1: bool) -> None:
        """
        Checks for the rare ID3v1 3DI tag ('3DI').

        This should be located in either.
        a) 10 bytes from end of file if no ID3v1
        b) 10 bytes in front of ID3v1
        There is a chance another tag (like APE or EXT) can push it around,
        which means the data could be there, but in the wrong place.

        Validation relies on the '3DI' signature and correct tag size.
        Unable to validate further as tag has no fixed content.

        Returns None as a graceful exit if 3DI not found
        """
        tag_size = 128
        size_3di = 10
        combined_size = (size_3di + tag_size) if id3v1 else size_3di
        if self.foot_size < combined_size:  # 3DI OR 3DI + ID3v1
            return None  # Too small to contain 3DI

        try:
            # Scan only calculated tag area, try to avoid false positives
            tag_start = self.foot_size - combined_size
            tag_end = tag_start + size_3di
            find_tag_loc = self.foot_string.rfind(b"3DI", tag_start, tag_end)
            if find_tag_loc == -1:
                return None  # Tag not found

            tag_calc_size = self.foot_size - find_tag_loc
            if tag_calc_size != combined_size:
                return None  # 3DI not valid size
            else:
                self.tags.append("3DI")

        except Exception:
            return None  # Other unexpected issues

    def _lyrics3(self, id3v1: bool) -> None:
        """
        Checks for the Lyrics3 v1 and v2.

        These are large tags (upto 1MB) and should be located at:
        a) Upto 1024 bytes from end of file if no ID3v1
        b) Upto 1152 bytes from end of file if ID3v1 present
        There is a chance another tag (like APE or EXT) can push it around,
        which means the data could be there, but in the wrong place.

        Validation relies on:
        a) For v1: LYRICSBEGIN and LYRICSEND
        AND a scan for metatag to see if any are present
        Unable to validate further as tag has no fixed content.
        b) For v2: LYRICSBEGIN and LYRICS200
        AND a scan for metatag to see if any are present
        AND check the size of the found tag, matches the size metatag.

        Returns None as a graceful exit if tag block not found
        """
        id3v1_size = 128
        max_tag_size = 1048576  # This is on paper the max a Lyrics3 tag could be (v1 in theory has no limit)
        combined_size = (max_tag_size + id3v1_size) if id3v1 else max_tag_size

        if self.foot_size < combined_size:  # LYRICS OR LYRICS + ID3v1
            combined_size = self.foot_size  # We have no way to know what size the tag is

        try:
            # Scan only calculated tag area, try to avoid false positives
            # This just checks for LYRICSEND or LYRICS200 marker immediately
            # before EOF or TAG
            lyricsend_size = 9  # This is for LYRICSEND or LYRICS200
            end_size = (lyricsend_size + id3v1_size) if id3v1 else lyricsend_size
            end_tag_start = self.foot_size - end_size
            end_tag_end = end_tag_start + lyricsend_size
            found_lyric = None
            for lyric_end in (b"LYRICSEND", b"LYRICS200"):
                find_tag_end = self.foot_string.rfind(lyric_end, end_tag_start, end_tag_end)
                if find_tag_end != -1:
                    found_lyric = lyric_end
            if found_lyric is None:
                return None  # No end marker found

            # Now we can scan for the start marker,
            # as we cannot overly target a scan we go for a broad
            # search of the last 1MB (or smaller) of the file.
            max_allowed_search_size = min(self.foot_size, self.file_size)
            tag_start_start = max_allowed_search_size - combined_size
            tag_start_end = tag_start_start + max_tag_size
            find_tag_start = self.foot_string.rfind(b"LYRICSBEGIN", tag_start_start, tag_start_end)
            if find_tag_start == -1:
                return None  # Tag start not found

            # Now we have the tag size and can scan inside the tag
            lyric3_tags = [b"IND", b"LYR", b"INF", b"AUT", b"EAL", b"EAR", b"ETT", b"IMG", b"GRE"]
            tag_block = self.foot_string[find_tag_start:end_tag_end]

            if found_lyric == b"LYRICSEND":  # v1
                if any(tag in tag_block for tag in lyric3_tags):  # This is the best we can do for v1
                    self.tags.append("Lyricsv1")

            if found_lyric == b"LYRICS200":  # v2
                # Get the v2 size data
                tag_size = len(tag_block)  # This matches Hex editors so length is correct
                size_tag_size = 6
                v2_tag_data = self.foot_string[end_tag_start - size_tag_size : end_tag_end - lyricsend_size]
                v2_tag_size_calc = int(v2_tag_data) + size_tag_size + lyricsend_size
                if any(tag in tag_block for tag in lyric3_tags) and tag_size == v2_tag_size_calc:
                    self.tags.append("Lyricsv2")

            return None  # Could not find a valid tag block

        except Exception:
            return None  # Other unexpected issues

    def _ape(self, id3v1: bool) -> None:
        """
        Checks for the Ape v1 and v2.

        These are complicated tags, we currently test for the most common variants.
        a) v1 with APETAGEX footer, at end of file or before ID3v1
        b) v2 with APETAGEX header and footer, at end of file or before ID3v1
        There is a chance another tag (like Lyrics3 or EXT) can push it around,
        which means the data could be there, but in the wrong place.

        We currently do not test for weird variants such as:
        a) v1 lacking the APETAGEX footer
        b) v2 lacking the APETAGEX header/footer
        c) v2 placed at the start of the file
        If sample files with these ever appear we can look to test.

        Validation relies on:
        a) For v1: finding the APETAGEX footer
        AND decode the tag for size and fixed marker checks.
        b) For v2: finding the APETAGEX header and footer
        AND decode the tag for size and fixed marker checks.

        Returns None as a graceful exit if tag block not found
        """
        common_ape_keys = (
            b"Title",
            b"Artist",
            b"Album",
            b"Track",
            b"Year",
            b"Genre",
            b"Comment",
            b"Album Artist",
            b"Composer",
            b"Copyright",
            b"Disc",
            b"Grouping",
            b"Lyrics",
            b"Publisher",
            b"Subtitle",
            b"Performer",
            b"Conductor",
            b"Rating",
            b"File",
            b"URL",
            b"Cover Art (Front)",  # front Titled to match search
            b"Cover Art (Back)",  # back Titled to match search
            b"Media",
            b"Language",
            b"ReplayGain Track Gain",
            b"ReplayGain Track Peak",
            b"ReplayGain Album Gain",
            b"ReplayGain Album Peak",
            b"ISRC",
            b"MCN",
        )
        id3v1_size = 128
        max_tag_size = 1048576  # This is a pratical scan range of 1MB, Ape v2 in theory can be 4GB
        combined_size = (max_tag_size + id3v1_size) if id3v1 else max_tag_size

        if self.foot_size < combined_size:  # APE OR APE + ID3v1
            combined_size = self.foot_size  # We have no way to know what size the tag is

        try:
            # Scan only calculated tag area, try to avoid false positives
            # This just checks for APETAGEX marker immediately
            # before EOF or ID3v1 TAG
            apextag_size = 32  # This is for APETAGEX and data bytes
            end_size = (apextag_size + id3v1_size) if id3v1 else apextag_size
            end_tag_start = self.foot_size - end_size
            end_tag_end = end_tag_start + apextag_size

            find_tag_end = self.foot_string.rfind(b"APETAGEX", end_tag_start, end_tag_end)
            if find_tag_end == -1:
                return None  # Tag not found

            # Footer tag
            # Check Version (bytes 8-11, Little-Endian)
            f_version = struct.unpack("<I", self.foot_string[end_tag_start + 8 : end_tag_start + 12])[0]
            if f_version not in (1000, 2000):
                return None  # Unsupported/Invalid tag version
            # Check Size (bytes 13-16, Little-Endian)
            f_size = struct.unpack("<I", self.foot_string[end_tag_start + 12 : end_tag_start + 16])[0]

            if f_version == 1000:  # v1
                # Reach first key in tag, in APE the tag key name is preceeded by 8 bytes associated with it.
                first_key = combined_size - ((end_size + f_size) - apextag_size) + 8
                # APE does not care about case for tag keys, but Title and UPPER are commonly accepted as standard
                if not self.foot_string[first_key:].title().startswith(common_ape_keys):
                    return None  # Tag may start with a unknown or invalid key
                self.tags.append("APEv1")

            if f_version == 2000:  # v2
                # Get the APEXTAG header
                tag_header = combined_size - ((end_size + f_size) - apextag_size) - apextag_size
                tag_block = self.foot_string[tag_header:end_tag_end]
                h_version = struct.unpack("<I", self.foot_string[tag_header + 8 : tag_header + 12])[0]
                h_size = struct.unpack("<I", self.foot_string[tag_header + 12 : tag_header + 16])[0]
                first_key = combined_size - ((end_size + f_size) - apextag_size) + 8
                if h_version != f_version:
                    return None  # Tag versions do not match
                if h_size != f_size:
                    return None  # Tag size bytes do not match
                if len(tag_block) != h_size + apextag_size:  # APE size does not include the 32 header bytes
                    return None  # Tag size bytes and real size do not match
                if not self.foot_string[first_key:].title().startswith(common_ape_keys):
                    return None  # Tag may start with a unknown or invalid key
                self.tags.append("APEv2")

            return None  # Could not find a valid tag block

        except Exception:
            return None  # Other unexpected issues

    def find_tags(self, file: IO[bytes]) -> None:
        """Read last 1.5MB of file and look for tags."""
        file.seek(max(0, self.file_size - self.foot_size))
        self.foot_string = file.read()
        self.foot_size = len(self.foot_string) if len(self.foot_string) < self.foot_size else self.foot_size
        file.seek(0)
        id3v1 = self._id3v1()
        if id3v1:  # These two require an ID3v1 TAG to be present
            self._tag_plus()
            self._ext_tag()
        self._3di(id3v1)
        self._lyrics3(id3v1)
        self._ape(id3v1)


class MpegAudioDecoder:
    """
    Decodes the raw mpeg audio stream.

    This handles Layers I, II and III, with CBR and VBR encodings.
    Returns None if any part of the decoding fails.
    """

    def __init__(self):
        # --- STATE AND OUTPUT ---
        self.tags = []
        self.header_results = {}
        self.first_frame_offset = 0

        # VBR
        self.vbr_info = None  # Stores detected VBR tag string ("Xing", "VBRI", etc.)
        self.VBRI_OFFSET = 36  # Constant for VBRI tag offset

        # --- LOOKUP TABLES ---
        self.sample_rate_table = {
            3: [44100, 48000, 32000, 0],  # MPEG 1
            2: [22050, 24000, 16000, 0],  # MPEG 2
            0: [11025, 12000, 8000, 0],  # MPEG 2.5
        }
        self.bitrate_table = {
            # MPEG 1
            3: {
                3: [0, 32, 64, 96, 128, 160, 192, 224, 256, 288, 320, 352, 384, 416, 448, 0],  # Layer I
                2: [0, 32, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 384, 0],  # Layer II
                1: [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 0],  # Layer III
            },
            # MPEG 2/2.5
            2: {
                3: [0, 32, 48, 56, 64, 80, 96, 112, 128, 144, 160, 176, 192, 224, 256, 0],  # Layer I
                2: [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160, 0],  # Layer II
                1: [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160, 0],  # Layer III
            },
            0: {
                3: [0, 32, 48, 56, 64, 80, 96, 112, 128, 144, 160, 176, 192, 224, 256, 0],  # Layer I
                2: [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160, 0],  # Layer II
                1: [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160, 0],  # Layer III
            },
        }
        self.mpeg_version_map = {3: "MPEG 1", 2: "MPEG 2", 0: "MPEG 2.5", 1: "Reserved"}
        self.mpeg_version_reverse = {"MPEG 1": 3, "MPEG 2": 2, "MPEG 2.5": 0}
        self.layer_map = {3: "Layer I (MP1)", 2: "Layer II (MP2)", 1: "Layer III (MP3)", 0: "Reserved"}
        self.channel_mode_map = {3: "Mono", 2: "Dual-Channel", 1: "Joint-Stereo", 0: "Stereo"}
        self.vbr_offsets = {
            # (MPEG_VERSION_INDEX, IS_MONO) -> Offset from byte 0
            (3, False): 36,  # MPEG 1, Stereo/Joint Stereo
            (3, True): 21,  # MPEG 1, Mono
            (2, False): 21,  # MPEG 2/2.5, Stereo/Joint Stereo
            (2, True): 13,  # MPEG 2/2.5, Mono
            (0, False): 21,  # MPEG 2.5, Stereo
            (0, True): 13,  # MPEG 2.5, Mono
        }

    def _parse_vbr_header(self, frame_bytes: bytes, header_results: Dict[str, Any]) -> Optional[str]:
        """
        Checks the first frame for Xing/Info (LAME) and VBRI (Fraunhofer) VBR tags.

        This function relies on self._decode_mp3_header having already passed its
        internal validity checks (sync word, reserved bits, valid rates).

        Returns the tag identifier string ("Xing", "Info", or "VBRI") if a tag is found,
        otherwise returns None.
        """
        # 1. Basic Validity Checks
        if not header_results.get("sync_word") or header_results.get("layer") == "Reserved":
            return None

        # VBR headers are for Layer III only
        if header_results.get("layer") != "Layer III (MP3)":
            return None

        # 2. Determine Offsets using validated results
        mpeg_version_str = header_results.get("mpeg_version")
        mpeg_version_index = self.mpeg_version_reverse.get(mpeg_version_str)

        if mpeg_version_index is None:
            return None

        channel_mode_str = header_results.get("chanel_mode", "Stereo")
        is_mono = channel_mode_str == "Mono"
        found_tag = None

        # --- 3. Check Xing/Info Tag ---
        key = (mpeg_version_index, is_mono)
        xing_vbr_offset = self.vbr_offsets.get(key)

        if xing_vbr_offset is not None and len(frame_bytes) >= xing_vbr_offset + 4:
            identifier_bytes = frame_bytes[xing_vbr_offset : xing_vbr_offset + 4]
            identifier = identifier_bytes.decode("ascii", errors="ignore")

            if identifier in ("Xing", "Info"):
                found_tag = identifier

        # --- 4. Check VBRI Tag ---
        vbri_vbr_offset = self.VBRI_OFFSET

        # Only check VBRI if Xing/Info was not found
        if found_tag is None and len(frame_bytes) >= vbri_vbr_offset + 4:
            identifier_bytes = frame_bytes[vbri_vbr_offset : vbri_vbr_offset + 4]
            identifier = identifier_bytes.decode("ascii", errors="ignore")

            if identifier == "VBRI":
                found_tag = "VBRI"

        # --- 5. Return ---
        return found_tag

    def _decode_mp3_header(self, header_bytes: bytes) -> None:
        """
        Decodes the 4-byte header. Raises ValueError if invalid.
        Performs frame size calculation based on MPEG version and Layer.
        """

        header_int = struct.unpack(">I", header_bytes)[0]

        # Extract Fields
        sync_word = (header_int >> 20) & 0xFFF
        mpeg_version_index = (header_int >> 19) & 0b11
        layer_index = (header_int >> 17) & 0b11
        bit_rate_index = (header_int >> 12) & 0b1111
        sample_rate_index = (header_int >> 10) & 0b11
        padding_bit = (header_int >> 9) & 0b1
        channel_mode_index = (header_int >> 6) & 0b11

        # --- 1. Basic Validation ---
        if sync_word != 0xFFF:
            raise ValueError("Sync word not fully set.")
        if mpeg_version_index == 1 or layer_index == 0:
            raise ValueError("Reserved MPEG version or Layer used.")
        if bit_rate_index == 0 or bit_rate_index == 15 or sample_rate_index == 3:
            raise ValueError("Reserved bit rate, index 0, or sample rate index used.")

        # --- 2. Lookup Values ---
        sr_list = self.sample_rate_table.get(mpeg_version_index)
        if not sr_list:
            raise ValueError("MPEG version not supported for Sample Rate lookup.")
        sample_rate_hz = sr_list[sample_rate_index]

        br_version_table = self.bitrate_table.get(mpeg_version_index)
        if not br_version_table:
            raise ValueError("MPEG version not supported for Bit Rate lookup.")

        br_layer_list = br_version_table.get(layer_index)
        if not br_layer_list:
            raise ValueError("Layer not supported for Bit Rate lookup.")

        bit_rate_kbps = br_layer_list[bit_rate_index]

        if bit_rate_kbps == 0 or sample_rate_hz == 0:
            raise ValueError("Calculated bit rate or sample rate is zero.")

        # --- 3. Frame Size Calculation ---
        if layer_index == 3:  # Layer I
            slot_size = 12
        elif layer_index == 2 or layer_index == 1:  # Layer II or Layer III
            # MPEG 1 uses 144, MPEG 2/2.5 use 72
            if mpeg_version_index == 3:  # MPEG 1
                slot_size = 144
            else:  # MPEG 2/2.5
                slot_size = 72

        # Frame Size Formula:
        frame_size_val = int((slot_size * bit_rate_kbps * 1000) / sample_rate_hz + padding_bit)

        if layer_index == 3:  # Layer I requires multiplication by 4
            frame_size_val *= 4

        if frame_size_val < 4 or frame_size_val > 5000:
            raise ValueError("Calculated frame size is out of expected bounds.")

        # Compile the results dictionary
        self.header_results = {
            "sync_word": True,
            "mpeg_version": self.mpeg_version_map.get(mpeg_version_index),
            "layer": self.layer_map.get(layer_index),
            "bit_rate": f"{bit_rate_kbps}k",
            "sample_rate": f"{sample_rate_hz / 1000:.1f}Khz",
            "padding": padding_bit,
            "chanel_mode": self.channel_mode_map.get(channel_mode_index, "Reserved"),
            "frame_size": f"{frame_size_val} bytes",
            "raw_frame_size": frame_size_val,  # CRUCIAL for seeking
            "bit_rate_index": bit_rate_index,
            "mpeg_version_index": mpeg_version_index,
        }

    # --- OBSOLETE VBR METHODS REMOVED ---

    def _check_stream_consistency(
        self, file_handle, frame1_bit_rate_index, frame2_start_abs_offset, frame1_size
    ) -> str | None:
        """
        Checks the bit rate index of the next few frames (up to 3 total) against
        the first frame to determine stream consistency.
        """
        frames_to_check = 2
        current_offset = frame2_start_abs_offset
        step_size = frame1_size

        total_frames_checked = 1  # We start having checked Frame 1

        for i in range(1, frames_to_check + 1):
            total_frames_checked += 1
            try:
                file_handle.seek(current_offset, os.SEEK_SET)
                frame_header_bytes = file_handle.read(4)
                if len(frame_header_bytes) < 4:
                    return None  # Too short to hold a frame header

                frame_bit_rate_index = self.extract_bit_rate_index(frame_header_bytes)

                if frame_bit_rate_index == -1 or frame_bit_rate_index != frame1_bit_rate_index:
                    # Found a change or invalid header at expected position -> VBR/ABR.
                    # This currently has a bodge for Layer II (.mp2)
                    return "VBR" if self.header_results["layer"] != "Layer II (MP2)" else "CBR"

                # If consistent, prepare for the next frame check.
                current_offset += step_size

            except Exception:
                return None

        # If the loop completed without finding a difference (F1=F2=F3)
        return "CBR"

    def extract_bit_rate_index(self, header_bytes):
        """Utility to quickly get the bit rate index for stream consistency check."""
        if len(header_bytes) < 4:
            return -1
        # Check for sync word (FF Ex) before extracting
        if header_bytes[0] != 0xFF or (header_bytes[1] & 0xE0) != 0xE0:
            return -1

        header_int = struct.unpack(">I", header_bytes)[0]
        return (header_int >> 12) & 0b1111

    def decoder(self, head: bytes, file: IO[bytes]):
        """Decodes the MPEG Audios Stream."""

        # 1. Seek to start (after ID3v2)
        file.seek(self.first_frame_offset, os.SEEK_SET)

        # Decode the first frame header (H1)
        header_bytes_frame1 = file.read(4)
        if len(header_bytes_frame1) < 4:
            return None

        try:
            # Fills self.header_results
            self._decode_mp3_header(header_bytes_frame1)
        except ValueError:
            return None

        raw_frame_size = self.header_results["raw_frame_size"]

        # 2. Read the area for VBR check
        read_size_for_vbr_check = min(raw_frame_size - 4, 150)
        frame_body_for_vbr = file.read(read_size_for_vbr_check)

        # Combine header and body bytes for easy slicing in the VBR parser
        frame_bytes_for_vbr = header_bytes_frame1 + frame_body_for_vbr

        # 3. Check for VBR Header (Xing/Info/VBRI)
        self.vbr_info = self._parse_vbr_header(frame_bytes_for_vbr, self.header_results)

        frame_step_size = raw_frame_size

        # 4. Check Stream Consistency by seeking to Frame 2 and 3
        if raw_frame_size > 0:
            frame2_start_abs_offset = self.first_frame_offset + frame_step_size
            frame1_bit_rate_index = self.header_results["bit_rate_index"]

            stream_type_deduction = self._check_stream_consistency(
                file,
                frame1_bit_rate_index,
                frame2_start_abs_offset,
                frame_step_size,
            )
        else:
            stream_type_deduction = None

        # 5. Final Result Compilation
        if stream_type_deduction is not None and self.header_results.get("sync_word"):
            self.tags = [
                self.header_results["bit_rate"],
                self.header_results["sample_rate"],
                self.header_results["chanel_mode"],
            ]

            # Use the VBR info if present, otherwise use the deduction
            if self.vbr_info:
                self.tags.append(f"Encoded as VBR ({self.vbr_info} Tag)")
            else:
                self.tags.append(stream_type_deduction)

            return self.tags

        return None


class ID3v2Decoder:
    """
    Decodes the ID3v2 tag and calculates the file offset where the audio stream begins.
    Its sole responsibility is parsing the tag data at offset 0.
    """

    def __init__(self, file_size: int, mpega: type[Any]):  # Using Any for the type hint to simplify
        self.id3v2_tag = None
        self.file_size = file_size
        self.id3_tag_size = None  # Total tag size (10-byte header + content)

        # NOTE: Keeping these MPEGA constants for now, but they could be removed
        # if they aren't used in _check_id3v2_tag (which they are not).
        self.sample_rate_table = mpega.sample_rate_table
        self.bitrate_table = mpega.bitrate_table
        self.mpeg_version_map = mpega.mpeg_version_map
        self.layer_map = mpega.layer_map
        self.channel_mode_map = mpega.channel_mode_map

        # Tag lists remain for validation
        self.tagsv22 = [
            b"AEN",
            b"BUF",
            b"CNT",
            b"COM",
            b"CRA",
            b"CRM",
            b"ETC",
            b"EQU",
            b"GEO",
            b"LNK",
            b"MCI",
            b"MLL",
            b"PIC",
            b"POP",
            b"REV",
            b"RVA",
            b"SLT",
            b"STC",
            b"TAL",
            b"TBP",
            b"TCM",
            b"TCO",
            b"TCR",
            b"TDA",
            b"TDY",
            b"TEN",
            b"TFT",
            b"TIM",
            b"TKE",
            b"TLA",
            b"TLE",
            b"TMT",
            b"TOA",
            b"TOF",
            b"TOL",
            b"TOR",
            b"TOT",
            b"TP1",
            b"TP2",
            b"TP3",
            b"TP4",
            b"TPA",
            b"TPB",
            b"TRC",
            b"TRD",
            b"TRK",
            b"TSS",
            b"TT1",
            b"TT2",
            b"TT3",
            b"TXT",
            b"TXX",
            b"TYE",
            b"UFI",
            b"ULT",
            b"WAF",
            b"WAR",
            b"WAS",
            b"WCM",
            b"WCP",
            b"WPB",
            b"WXX",
            b"WIR",
            b"UIN",
        ]
        self.tagsv23 = [
            b"AENC",
            b"APIC",
            b"ASPI",
            b"COMM",
            b"COMR",
            b"ENCR",
            b"EQU2",
            b"ETCO",
            b"GEOB",
            b"GRID",
            b"LINK",
            b"MCDI",
            b"MLLT",
            b"OWNE",
            b"PRIV",
            b"PCNT",
            b"POPM",
            b"POSS",
            b"RBUF",
            b"RVA2",
            b"RVRB",
            b"SEEK",
            b"SIGN",
            b"SYLT",
            b"SYTC",
            b"UFID",
            b"USER",
            b"USLT",
            b"WCOM",
            b"WCOP",
            b"WOAF",
            b"WOAR",
            b"WOAS",
            b"WORS",
            b"WPAY",
            b"WPUB",
            b"WXXX",
            b"TYER",
            b"TDAT",
            b"TIME",
            b"TORY",
            b"TALB",
            b"TBPM",
            b"TCOM",
            b"TCON",
            b"TCOP",
            b"TDEN",
            b"TDLY",
            b"TDOR",
            b"TDRC",
            b"TDRL",
            b"TDTG",
            b"TENC",
            b"TEXT",
            b"TFLT",
            b"TIPL",
            b"TIT1",
            b"TIT2",
            b"TIT3",
            b"TKEY",
            b"TLAN",
            b"TLEN",
            b"TMCL",
            b"TMED",
            b"TMOO",
            b"TOAL",
            b"TOFN",
            b"TOLY",
            b"TOPE",
            b"TOWN",
            b"TPE1",
            b"TPE2",
            b"TPE3",
            b"TPE4",
            b"TPOS",
            b"TPRO",
            b"TPUB",
            b"TRCK",
            b"TRSN",
            b"TRSO",
            b"TSOA",
            b"TSOC",
            b"TSOP",
            b"TSOT",
            b"TSRC",
            b"TSSE",
            b"TSST",
            b"TXXX",
        ]
        self.tagsv23_3letter = [
            b"WAF",
            b"WIR",
            b"WYY",
        ]

    # --- ID3V2 Parsing Logic ---

    def _check_id3v2_tag(self, head: bytes) -> Optional[int]:
        """
        Checks for ID3v2 tags. Calculates the size of the ID3v2 tag from the
        synchsafe size field (bytes 6-9).

        Returns the total tag size (header + content) on success, or None on failure.
        """

        if len(head) < 10:
            return None  # Header too small

        if head[0:3] != b"ID3":
            return None  # This should never happen if called correctly

        size_field = head[6:10]
        tag_content_size = 0
        tag = None

        # ID3v2.2
        if head[0:5] == b"ID3\x02\x00":
            if head[10:13] not in self.tagsv22:
                return None
            # ID3v2.2 uses a standard 4-byte big-endian integer for size
            tag_content_size = (size_field[0] << 24) | (size_field[1] << 16) | (size_field[2] << 8) | size_field[3]
            tag = "ID3v2.2"

        # ID3v2.3 or ID3v2.4
        elif head[0:5] == b"ID3\x03\x00" or head[0:5] == b"ID3\x04\x00":
            # Quick tag scan for v2.3/v2.4 (4-letter frames)
            if head[10:14] not in self.tagsv23:
                # Check for niche 3-letter v2.3 frames
                if head[10:13] not in self.tagsv23_3letter:
                    return None
            # ID3v2.3 and ID3v2.4 use the Synchsafe Integer for size
            tag_content_size = (size_field[0] << 21) | (size_field[1] << 14) | (size_field[2] << 7) | size_field[3]
            tag = "ID3v2.3" if head[0:5] == b"ID3\x03\x00" else "ID3v2.4"

        else:
            return None  # Invalid tag version

        # Commit success state
        self.id3v2_tag = tag
        self.id3_tag_size = 10 + tag_content_size  # Total tag size plus 10-byte header

        # Return the offset where the audio stream starts
        return self.id3_tag_size

    # --- Public Entry Point ---

    def decode_id3v2(self, head: bytes) -> int:
        """
        Decodes the ID3v2 tag header (if present at offset 0).

        Returns the absolute file offset where the first audio frame should be
        (0 if no ID3v2 tag is found).
        """
        # The file stream IO is no longer needed in this simplified class.

        # Check the tag and calculate the size
        audio_start_offset = self._check_id3v2_tag(head)

        # If _check_id3v2_tag was successful, it returns the tag size (the starting offset).
        # Otherwise, it returns None, meaning the audio starts at offset 0.
        return audio_start_offset if audio_start_offset is not None else 0


def build_name(mpega_results: Dict, id3v2_tags: str, mpega_tags: List, eof_tags: List, vbr_type: str) -> str | None:
    """Return the full name string and extension."""
    # set version: MPEG-1, MPEG-2, MPEG-2.5
    # Reserved if a super rare fringe case that should never happen
    version = (
        mpega_results["mpeg_version"].replace(" ", "-")
        if mpega_results["mpeg_version"] != "Reserved"
        else "MPEG-Unknown Version"
    )
    if mpega_results["layer"] == "Layer I (MP1)":
        layer = mpega_results["layer"]
        ext = ".mp1"
    elif mpega_results["layer"] == "Layer II (MP2)":
        layer = mpega_results["layer"]
        ext = ".mp2"
    elif mpega_results["layer"] == "Layer III (MP3)":
        layer = mpega_results["layer"]
        ext = ".mp3"
    else:
        # This should never happen
        layer = "Unknown Layer"
        ext = ".mpga"
    name = f"{version} Audio {layer} file"
    name_end = ""
    name_list = []
    try:
        if mpega_tags:
            name_list.extend(mpega_tags)  # This adds sample, bitrate etc..
        if vbr_type:
            tag_name = f"LAME({vbr_type})" if vbr_type in ("Xing", "Info") else vbr_type
            name_list.append(tag_name)  # Add VBR encoder info for LAME or Fraunhofer
        if id3v2_tags:
            name_list.append(id3v2_tags)  # This adds ID3v2 tag
        if eof_tags:
            name_list.extend(eof_tags)  # This adds tags such as ID3v1, APE, TAG+ etc...
        name_end += f" [{' '.join(name_list)}]"
        full_name = name + name_end
    except Exception:
        return None, None  # Really should not happen
    return full_name, ext


def test_mpega(file_path: os.PathLike | str, head: bytes) -> Optional[Match]:
    """Main workflow"""
    if DataCache.is_cached() and DataCache.get_file_path() == file_path:
        if DataCache.is_matched():
            return DataCache.get_result()  # Send cached results
        else:
            return None  # No match was made
    else:
        DataCache.set_file_path(file_path)
        eof = EndOfFileTags(os.path.getsize(file_path))
        mpega = MpegAudioDecoder()
        id3v2 = ID3v2Decoder(os.path.getsize(file_path), mpega)
        try:
            with open(file_path, "rb") as file:
                eof.find_tags(file)
                # If ID3v2 present, test and then adjust frame offset
                if b"ID3" == head[0:3]:
                    mpega.first_frame_offset = id3v2.decode_id3v2(head)
                mpega.decoder(head, file)
        except Exception:
            return None  # If the decode process fails for any unknown reason

        full_name, ext = build_name(mpega.header_results, id3v2.id3v2_tag, mpega.tags, eof.tags, mpega.vbr_info)
        if full_name is None or ext is None:
            return None  # Name building failed for some reason

        # Store the result for future calls, then return
        result = Match(extension=ext, name=full_name, mime_type="audio/mpeg", confidence=1.0)
        DataCache.set_result(result)
        return result


def main(file_path: os.PathLike | str, head: bytes, _) -> Optional[Match]:
    return test_mpega(file_path, head)
