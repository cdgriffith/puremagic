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

from typing import Optional, IO, Dict, Any
import os
import struct
from puremagic.scanners.helpers import Match

# Bytes for main.py to scan, these are the most common two
mp3_id3_match_bytes = b"ID3"  # All MP3's with V2 tags will start with this.
raw_mp3_match_bytes = b"\xff\xfb"  # Bytes for MP1 Layer III (CRC Present) **Typical MP3**

# MPEG-1 Layer I (MP1)
fffe_match_bytes = b"\xff\xfe"  # Bytes for MP1 Layer I (No CRC Protection)
ffff_match_bytes = b"\xff\xff"  # Bytes for MP1 Layer I (CRC Present)

# MPEG-1 Layer II (MP2)
fffc_match_bytes = b"\xff\xfc"  # Bytes for MP1 Layer II (No CRC Protection)
fffd_match_bytes = b"\xff\xfd"  # Bytes for MP1 Layer II (CRC Present)

# MPEG-1 Layer III (MP3)
fffa_match_bytes = b"\xff\xfa"  # Bytes for MP1 Layer III (No CRC Protection)
# fffb_match_bytes = b"\xff\xfb"  # Bytes for MP1 Layer III (CRC Present) **Typical MP3**

# MPEG-2 Layer I (MP1)
fff6_match_bytes = b"\xff\xf6"  # Bytes for MP2 Layer I (No CRC Protection)
fff7_match_bytes = b"\xff\xf7"  # Bytes for MP2 Layer I (CRC Present)

# MPEG-2 Layer II (MP2)
fff4_match_bytes = b"\xff\xf4"  # Bytes for MP2 Layer II (No CRC Protection)
fff5_match_bytes = b"\xff\xf5"  # Bytes for MP2 Layer II (CRC Present)

# MPEG-2 Layer III (MP3)
fff2_match_bytes = b"\xff\xf2"  # Bytes for MP2 Layer III (No CRC Protection)
fff3_match_bytes = b"\xff\xf3"  # Bytes for MP2 Layer III (CRC Present)

# MPEG-2.5 Layer I (MP1)
ffe6_match_bytes = b"\xff\xe6"  # Bytes for MP2.5 Layer I (No CRC Protection)
ffe7_match_bytes = b"\xff\xe7"  # Bytes for MP2.5 Layer I (CRC Present)

# MPEG-2.5 Layer II (MP2)
ffe4_match_bytes = b"\xff\xe4"  # Bytes for MP2.5 Layer II (No CRC Protection)
ffe5_match_bytes = b"\xff\xe5"  # Bytes for MP2.5 Layer II (CRC Present)

# MPEG-2.5 Layer III (MP3)
ffe2_match_bytes = b"\xff\xe2"  # Bytes for MP2.5 Layer III (No CRC Protection)
ffe3_match_bytes = b"\xff\xe3"  # Bytes for MP2.5 Layer III (CRC Present)

# Cached Data, prevents work being carried out more than once
cached_data = {"path": None, "matched": False, "name_end": [], "name_format": []}


class mp3_decoding:
    """
    MP3 Decoding needs a lot of things to make it work.

    Not everything here may be used in outputs at this time.
    """

    def __init__(self, file_path: os.PathLike | str):
        """Lookup tables are stored here."""
        self.mpeg_audio_signatures = [
            b"\xff\xfe",
            b"\xff\xff",
            b"\xff\xfc",
            b"\xff\xfd",
            b"\xff\xfa",
            b"\xff\xfb",
            b"\xff\xf6",
            b"\xff\xf7",
            b"\xff\xf4",
            b"\xff\xf5",
            b"\xff\xf2",
            b"\xff\xf3",
            b"\xff\xe6",
            b"\xff\xe7",
            b"\xff\xe4",
            b"\xff\xe5",
            b"\xff\xe2",
            b"\xff\xe3",
        ]
        self.mpeg_version_map = {3: "MPEG 1", 2: "MPEG 2", 0: "MPEG 2.5", 1: "Reserved"}
        self.mpeg_version_reverse = {"MPEG 1": 3, "MPEG 2": 2, "MPEG 2.5": 0}  # VBR offset lookup
        self.vbr_offsets = {
            # (MPEG_VERSION_INDEX, IS_MONO) -> Offset from byte 0
            (3, False): 36,  # MPEG 1, Stereo/Joint Stereo
            (3, True): 21,  # MPEG 1, Mono
            (2, False): 21,  # MPEG 2/2.5, Stereo/Joint Stereo
            (2, True): 13,  # MPEG 2/2.5, Mono
            (0, False): 21,  # MPEG 2.5 is treated same as MPEG 2
            (0, True): 13,
        }
        self.layer_map = {3: "Layer I", 2: "Layer II", 1: "Layer III (MP3)", 0: "Reserved"}
        self.channel_mode_map = {3: "Mono", 2: "Dual-Channel", 1: "Joint-Stereo", 0: "Stereo"}
        self.bit_rates = [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 0]
        self.sample_rates = [44100, 48000, 32000, 0]
        self._SR_TABLE = {
            3: [44100, 48000, 32000, 0],  # MPEG 1
            2: [22050, 24000, 16000, 0],  # MPEG 2
            0: [11025, 12000, 8000, 0],  # MPEG 2.5
        }

        # Bit Rate (kbps) depends on MPEG version and Layer
        self._BR_TABLE = {
            # MPEG 1
            3: {
                3: [0, 32, 64, 96, 128, 160, 192, 224, 256, 288, 320, 352, 384, 416, 448, 0],  # Layer I
                2: [0, 32, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 384, 0],  # Layer II
                1: [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 0],  # Layer III
            },
            # MPEG 2/2.5 (Use the same table for both versions 2 and 0)
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
        # VBR Flags Constants
        self.xing_flag_frames = 0x01  # Bit 0
        self.xing_flag_bytes = 0x02  # Bit 1
        self.xing_flag_toc = 0x04  # Bit 2
        self.xing_flag_scale = 0x08  # Bit 3
        self.tagsv22 = [
            b"BUF",
            b"CNT",
            b"COM",
            b"CRA",
            b"CRM",
            b"ETC",
            b"EQU",
            b"GEO",
            b"IPL",
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
            b"TSI",
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
            b"TSOP",
            b"TSOT",
            b"TSRC",
            b"TSSE",
            b"TSST",
            b"TXXX",
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
        ]
        self.lyric3_tags = [b"IND", b"LYR", b"INF", b"AUT", b"EAL", b"EAR", b"ETT", b"IMG", b"GRE"]
        """Temporary variables are stored here."""
        self.file_path = file_path
        self.file_size = os.path.getsize(file_path)
        self.id3_tag_size = 0
        self.id3_content_size = 0
        self.vbr_type = None
        self.vbr_offset = None
        self.vbr_flags_data = None
        self.first_frame_offset = -1  # Final determined start of the audio stream
        self.header_results = None
        self.header_bytes = None
        self.foot_scan_size = 1024  # Scan last 1024 bytes of file
        self.foot = None

    def footer_read(self, file) -> None:
        """Read file chunks as required."""
        # Footer data
        # We use either the byte size or file size whichever is smaller
        block_size = min(self.file_size, self.foot_scan_size)
        file.seek(self.file_size - block_size, os.SEEK_SET)
        self.foot = file.read(block_size)

    def check_id3v2_tag(self, head: bytes) -> None:
        """
        Checks got ID3v2 tags, a pass requires both byte matching AND
        decoding of the header size which we need to check the MP3 stream later.

        Calculates the size of the ID3v2 tag from the synchsafe size field (bytes 6-9).

        Returns None if we fail to decode the tag
        """

        if len(head) < 10:
            return None  # File is too small

        if head[0:3] != b"ID3":
            return None  # This should never happen

        size_field = head[6:10]  # Bytes 6 through 9 the size
        tag_content_size = 0
        if head[0:5] == b"ID3\x02\x00":  # v2.2
            # Perform a quick tag scan, one of these should be present in a valid tag
            if head[10:13] not in self.tagsv22:
                return None
            # ID3v2.2 uses a standard 4-byte big-endian integer for size
            tag_content_size = (size_field[0] << 24) | (size_field[1] << 16) | (size_field[2] << 8) | size_field[3]
            tag = "ID3v2.2"

        elif head[0:5] == b"ID3\x03\x00" or head[0:5] == b"ID3\x04\x00":
            # Perform a quick tag scan, one of these should be present in a valid tag
            if head[10:14] not in self.tagsv23:
                return None
            # ID3v2.3 and ID3v2.4 use the Synchsafe Integer for size
            tag_content_size = (size_field[0] << 21) | (size_field[1] << 14) | (size_field[2] << 7) | size_field[3]
            tag = "ID3v2.3" if head[0:5] == b"ID3\x03\x00" else "ID3v2.4"

        else:
            return None  # Invalid tag
        cached_data["name_end"].append(tag)
        total_size = 10 + tag_content_size  # Total tag size plus 10-byte header
        self.id3_tag_size = total_size
        self.id3_content_size = tag_content_size

    def find_audio_start_and_header(self, file_handle: IO[bytes]):
        """
        Scans forward until a valid MP3 frame sync word is found, using robust
        double-frame verification. This function is unchanged, relying on
        decode_mp3_header for robust validation and frame size.
        """
        current_scan_offset = self.id3_tag_size
        max_junk_to_scan = 16384

        limit = min(self.file_size, self.id3_tag_size + max_junk_to_scan)

        file_handle.seek(self.id3_tag_size, os.SEEK_SET)

        while current_scan_offset < limit:
            try:
                # 1. Read and check for sync word (FF Fxx)
                file_handle.seek(current_scan_offset, os.SEEK_SET)
                header_bytes_candidate = file_handle.read(4)

                if len(header_bytes_candidate) < 4:
                    break

                # Fast check for sync word
                if not (header_bytes_candidate[0] == 0xFF and (header_bytes_candidate[1] & 0xE0) == 0xE0):
                    current_scan_offset += 1
                    continue

                # 2. Decode and fully validate the header (raises ValueError on failure)
                candidate_results = self.decode_mp3_header(header_bytes_candidate)
                frame_size = candidate_results["raw_frame_size"]

                # 3. ROBUST VERIFICATION: Check for next frame sync
                next_frame_offset = current_scan_offset + frame_size

                if next_frame_offset + 2 >= self.file_size:
                    raise ValueError("Next frame check is past EOF.")

                # Jump to the expected start of the next frame
                file_handle.seek(next_frame_offset, os.SEEK_SET)
                next_sync_candidate = file_handle.read(2)

                # Check for FF E0 in the next frame
                if next_sync_candidate[0] == 0xFF and (next_sync_candidate[1] & 0xE0) == 0xE0:
                    # SUCCESS: Two consecutive, validly sized sync words found.
                    self.first_frame_offset = current_scan_offset
                    self.header_results = candidate_results
                    self.header_bytes = header_bytes_candidate
                    return  # Found the audio start
                else:
                    raise ValueError("Failed secondary frame sync check.")

            except ValueError:
                # Catch specific validation errors and continue scan
                pass
            except Exception:
                # Catch unexpected file IO errors and continue scan
                pass

            # Move the pointer one byte forward to continue the scan
            current_scan_offset += 1

        return None

    def decode_mp3_header(self, header_bytes: bytes) -> Dict[str, Any]:
        """
        Decodes the 4-byte header. Raises ValueError if invalid.
        Includes robust frame size calculation based on MPEG version and Layer.
        """
        if len(header_bytes) < 4:
            raise ValueError("Header is less than 4 bytes.")

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
        sr_list = self._SR_TABLE.get(mpeg_version_index)
        if not sr_list:
            raise ValueError("MPEG version not supported for Sample Rate lookup.")
        sample_rate_hz = sr_list[sample_rate_index]

        br_version_table = self._BR_TABLE.get(mpeg_version_index)
        if not br_version_table:
            raise ValueError("MPEG version not supported for Bit Rate lookup.")
        br_layer_list = br_version_table.get(layer_index)
        if not br_layer_list:
            raise ValueError("Layer not supported for Bit Rate lookup.")
        bit_rate_kbps = br_layer_list[bit_rate_index]

        if bit_rate_kbps == 0 or sample_rate_hz == 0:
            raise ValueError("Calculated bit rate or sample rate is zero.")

        # --- 3. Frame Size Calculation ---

        # Calculation constant depends on MPEG Version and Layer
        # Frame size is based on the number of samples per frame.
        if layer_index == 3:  # Layer I
            slot_size = 12
        elif layer_index == 2 or layer_index == 1:  # Layer II or Layer III
            # MPEG 1 uses 144, MPEG 2/2.5 use 72
            if mpeg_version_index == 3:  # MPEG 1
                slot_size = 144
            else:  # MPEG 2/2.5
                slot_size = 72

        # Frame Size Formula:
        # Layer I: FrameSize = floor((SlotSize * BitRate) / SampleRate + Padding) * 4
        # Layer II/III: FrameSize = floor((SlotSize * BitRate) / SampleRate + Padding)

        frame_size_val = int((slot_size * bit_rate_kbps * 1000) / sample_rate_hz + padding_bit)

        if layer_index == 3:  # Layer I requires multiplication by 4
            frame_size_val *= 4

        if frame_size_val < 4 or frame_size_val > 5000:
            raise ValueError("Calculated frame size is out of expected bounds.")

        # Compile the results dictionary
        results = {
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
        }
        return results

    def check_for_vbr_header(self, frame_bytes):
        """
        Checks for the presence of VBR headers, and if found, returns the offset and data.
        """
        mpeg_version_str = self.header_results["mpeg_version"]
        channel_mode_str = self.header_results["chanel_mode"]

        mpeg_version_index = self.mpeg_version_reverse.get(mpeg_version_str, 3)
        is_mono = channel_mode_str == "Mono"
        key = (mpeg_version_index, is_mono)
        try:
            vbr_offset = self.vbr_offsets[key]
        except KeyError:
            return None  # Cannot decode

        if len(frame_bytes) < vbr_offset + 4:
            return None  # Too short

        identifier_bytes = frame_bytes[vbr_offset : vbr_offset + 4]
        identifier = identifier_bytes.decode("ascii", errors="ignore")
        # On paper for LAME, Xing = VBR, Info = CBR, in reality could be mislabeled
        if identifier in ("Xing", "Info"):
            vbr_type = identifier
            vbr_flags_data = self.decode_vbr_header_flags(frame_bytes, vbr_offset)
            if vbr_flags_data is None:
                return None  # Cannot decode
            self.vbr_type = vbr_type
            self.vbr_offset = vbr_offset
            self.vbr_flags_data = vbr_flags_data

        elif identifier == "VBRI":  # Fraunhofer VBR
            self.vbr_type = identifier

    def decode_vbr_header_flags(self, frame_bytes, vbr_offset):
        """
        Reads the 4-byte VBR Flags field and determines the required parsing strategy.
        """
        flags_offset = vbr_offset + 4
        flags_bytes = frame_bytes[flags_offset : flags_offset + 4]

        if len(flags_bytes) < 4:
            return None  # Too short

        flags_int = struct.unpack(">I", flags_bytes)[0]

        # Check if Total Frames (0x01) AND Total Bytes (0x02) are present
        is_vbr_data_present = (flags_int & self.xing_flag_frames) and (flags_int & self.xing_flag_bytes)

        if is_vbr_data_present:
            file_type = "VBR/ABR (Strategy: Use Total Frames/Bytes for seek/duration)"
            vbr_data = self.decode_vbr_data(frame_bytes, vbr_offset, flags_int)
        else:
            file_type = "CBR (Constant Bit Rate) File (Strategy: Frame-by-Frame, Use Header's Frame Size)"
            vbr_data = {"total_frames": None, "total_bytes": None}

        flags_info = []
        if flags_int & self.xing_flag_frames:
            flags_info.append("Total Frames")
        if flags_int & self.xing_flag_bytes:
            flags_info.append("Total Bytes")
        if flags_int & self.xing_flag_toc:
            flags_info.append("TOC (Seeking Table)")
        if flags_int & self.xing_flag_scale:
            flags_info.append("VBR Scale")

        if not flags_info:
            flags_info.append("None (Metadata Only)")

        results = {
            "flags_value": flags_int,
            "flags_description": " + ".join(flags_info),
            "file_type_deduction": file_type,
            "vbr_data": vbr_data,
        }
        return results

    def decode_vbr_data(self, frame_bytes, vbr_offset, flags_int):
        """
        Reads the Total Frames and Total Bytes from the VBR header based on flags.
        The data starts 8 bytes after the VBR ID (4 bytes ID + 4 bytes Flags).
        """
        current_offset = vbr_offset + 8

        total_frames = None
        total_bytes = None

        # Read Total Frames (4 bytes, Big-endian)
        if flags_int & self.xing_flag_frames:
            frames_bytes = frame_bytes[current_offset : current_offset + 4]
            if len(frames_bytes) == 4:
                total_frames = struct.unpack(">I", frames_bytes)[0]
            current_offset += 4

        # Read Total Bytes (4 bytes, Big-endian)
        if flags_int & self.xing_flag_bytes:
            bytes_bytes = frame_bytes[current_offset : current_offset + 4]
            if len(bytes_bytes) == 4:
                total_bytes = struct.unpack(">I", bytes_bytes)[0]
            current_offset += 4

        return {"total_frames": total_frames, "total_bytes": total_bytes}

    def check_stream_consistency(self, file_handle, frame1_bit_rate_index, frame2_start_abs_offset, frame1_size):
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
                # Use absolute seek from the start of the file (os.SEEK_SET).
                file_handle.seek(current_offset, os.SEEK_SET)

                frame_header_bytes = file_handle.read(4)

                if len(frame_header_bytes) < 4:
                    break

                frame_bit_rate_index = self.extract_bit_rate_index(frame_header_bytes)

                if frame_bit_rate_index == -1 or frame_bit_rate_index != frame1_bit_rate_index:
                    # Found a change or invalid header at expected position -> VBR/ABR.
                    # This currently has a bodge for Layer II (.mp2)
                    # .mp2 does not have VBR, but does has frame 'wobble' that causes
                    # them to be mis-identified.
                    return "VBR" if self.header_results["layer"] != "Layer II" else "CBR"

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

    def end_of_file_tags(self) -> None:
        """
        A lot of tags formats store themselves at the end of the file.

        We check them here using a 1024 byte lump of the footer.
        """

        # 1. APE
        self.check_for_ape()
        # 2. ID3v1, ID3v1 Enhanced (TAG+), ID3v1.2 Enhanced Tag ('EXT')
        tag = self.check_for_id3v1()
        if not self.check_for_tagplus(tag) and not self.check_for_ext(tag):
            if tag:
                cached_data["name_end"].append("ID3v1")
        # 3. Lyrics3
        self.check_for_lyrics3()
        # 4. 3DI
        self.check_for_3di(tag)

    def check_for_ape(self) -> None:
        """
        Searches the foot string for the 32-byte APE footer.

        Reads the last 256 bytes to account for potential padding before
        the 32-byte tag structure begins, this allows for other tag formats.

        APE tags are fixed in their placement, but other tags may push them out the way
        (TAG+ or EXT) which means the data would be there but in the wrong place.

        Returns None if it fails for any reason.
        """
        ape_footer_size = 32
        buffer_length = len(self.foot)

        if buffer_length < ape_footer_size:
            return None  # Too small to contain a footer

        read_length = min(buffer_length, 256)  # Determine the length of the search block.
        search_block = self.foot[-read_length:]  # Extract the search block.

        try:
            signature_index = -1

            # Iterate backwards through the search block.
            for i in range(read_length - ape_footer_size, -1, -1):
                if search_block[i : i + 8] == b"APETAGEX":
                    signature_index = i
                    break

            if signature_index == -1:
                return None  # Cannot find the tag signature

            # Extract the 32-byte footer from the search block.
            footer_bytes = search_block[signature_index : signature_index + ape_footer_size]

            # 1. Check Version (bytes 8-11, Little-Endian)
            version = struct.unpack("<I", footer_bytes[8:12])[0]

            if version not in (1000, 2000):
                return None  # Unsupported/Invalid tag version

            # Add the tag version to the global cached data
            cached_data["name_end"].append("APEv2" if version == 2000 else "APEv1")

        except Exception:
            return None  # Handle potential struct errors

    def check_for_tagplus(self, tag: bool) -> bool:
        """
        Checks for the ID3v1 Enhanced Tag ('TAG+').

        While this should be located in one fixed place the spec and SpeedTag
        do not seem to align, so we use a broad search. There is also a chance
        another tag (like APE or EXT) can push it around which means the data would be there
        but in the wrong place.

        This is a simplified check for speed as it a fringe case.

        Returns None if it fails for any reason.
        Returns True to prevent ID3v1, avoids duplicates and extra work.
        """
        tagplus_size = 227
        if len(self.foot) < tagplus_size:
            return False  # Too small to contain a footer

        if (b"TAG+") in self.foot:  # Find the TAG+ marker
            if tag:
                # TAG+ extends ID3v1 TAG so you should always have both
                cached_data["name_end"].extend(["ID3v1", "TAG+"])
                return True
            else:
                return False  # TAG+ found but invalid
        else:
            return False  # Any other errors

    def check_for_ext(self, tag: bool) -> bool:
        """
        Checks for ID3v1.2 Enhanced Tag ('EXT').

        This is rigidly placed immediately before the standard 128-byte ID3v1 ('TAG') block.
        Like other EOF tags is can be pushed around so can fail even if data is present.

        Returns None if it fails for any reason.
        Returns True to prevent ID3v1 scans, avoids duplicates and extra work.
        """

        ext_tag = b"EXT"
        id3v1_tag = b"TAG"
        block_size = 128
        total_size = 256

        if len(self.foot) < total_size:
            return False  # Too small to hold 256 bytes.

        try:
            # The EXT block starts 256 bytes from EOF is 128 bytes.
            ext_signature_slice = self.foot[-total_size : -total_size + len(ext_tag)]

            # The subsequent ID3v1 TAG block starts 128 bytes from EOF.
            id3v1_signature_slice = self.foot[-block_size : -block_size + len(id3v1_tag)]

            if ext_signature_slice == ext_tag:  # Check EXT Signature
                if id3v1_signature_slice == id3v1_tag:  # Check for TAG
                    if tag:  # TAG is valid
                        cached_data["name_end"].extend(["ID3v1", "EXT"])
                        return True
                else:
                    return False  # EXT found but incomplete/invalid
            else:
                return False  # Not found

        except Exception:
            return False  # Any other errors

    def check_for_id3v1(self) -> bool:
        """
        Checks the last 128 bytes for an ID3v1 Tag footer.

        Validation relies on the 'TAG' signature
        AND either a 4-digit year (1900-2100) OR four null bytes in the Year field.

        Returns None if fails to find a correctly formatted TAG.
        Returns True if found.
        """

        tag_size = 128

        if len(self.foot) < tag_size:
            return False  # Too small to contain ID3v1 tag.

        try:
            tag_data = self.foot[-tag_size:]  # Get the last 128 bytes from the provided buffer

            if tag_data[:3] == b"TAG":  # Check for TAG
                year_bytes = tag_data[93:97]  # Get year data

                if year_bytes == b"\x00\x00\x00\x00":  # Check for empty year (all nulls)
                    return True

                try:  # Check for a plausible 4-digit year 1900-2100
                    year_str = year_bytes.decode("ascii", errors="ignore").strip(b"\x00".decode()).strip()

                    if len(year_str) == 4 and year_str.isdigit():
                        year_int = int(year_str)

                        if 1900 <= year_int <= 2100:
                            return True

                except Exception:
                    pass  # Fails decoding year or non null bytes

                return False  # Invalid TAG data
            else:
                return False  # TAG not found

        except Exception:
            return False  # Other unexpected issues

    def check_for_lyrics3(self) -> None:
        """
        Checks for Lyrics3v1 and Lyrics3v2 tags.

        NOTE: The Lyrics3 specification allows upto 1MB tag content.
        We first scan the 1024byte foot for LYRICSEND or LYRICS200 to avoid extra file reads.
        If found we have to read last 1.5MB to find LYRICSBEGIN (not optimal but required at present)
        While v2 includes a size field that could help us limit read sizes, the maths
        appears quite broken even when using the creators own MP3 MANAGER tool.

        As a LYRICS tag can exist with or without ID3v1 TAG we will not check it like with
        TAG+ or EXT

        Returns None if fails to find a correctly formatted tag.
        """

        try:
            if b"LYRICSEND" not in self.foot and b"LYRICS200" not in self.foot:
                return None

            with open(self.file_path, "rb") as file:
                # Read last 1.5MB of the file or whole file whichever is smaller
                # 1572864 bytes = 1.5MB
                file.seek(max(0, self.file_size - 1572864))
                lyrics_begin_data = file.read()
            """    
            Perform a rudimentary check to header start/end and
            at least a valid tag in between, could be spoofed but
            best we can do for the moment.    
            """
            if (
                b"LYRICSBEGIN" in lyrics_begin_data
                and b"LYRICSEND" in lyrics_begin_data
                and any(self.lyric3_tags) in lyrics_begin_data
            ):
                # Assume OK since v1 lacks size check
                cached_data["name_end"].append("Lyrics3v1")
            if (
                b"LYRICSBEGIN" in lyrics_begin_data
                and b"LYRICS200" in lyrics_begin_data
                and any(self.lyric3_tags) in lyrics_begin_data
            ):
                # Assume OK since v2 size check maths is broken
                cached_data["name_end"].append("Lyrics3v2")

        except Exception:
            return None  # Catch any errors

    def check_for_3di(self, tag: bool) -> None:
        """
        Checks for the '3DI' signature. This is a super niche tag
        used in some Japanese based players, but we're here to test
        these things.

        Location depends on ID3v1 presence:
        - 138 bytes from EOF (if ID3v1 present)
        - 10 bytes from EOF (if ID3v1 NOT present)

        Returns None if test fails.
        """
        try:
            offset = (self.file_size - 138) if tag else (self.file_size - 10)

            # Basic file size check for the determined offset
            if offset < 0:
                return None  # Too small

            # Check foot for tag
            start_index = len(self.foot) - offset
            tag_bytes = self.foot[start_index : start_index + 3]  # 3DI = 3

            if tag_bytes == b"3DI":
                cached_data["name_end"].append("3DI")

        except Exception:
            return None


def build_name(mp3) -> None:
    """Build the name."""
    if "Layer I" == mp3.header_results["layer"]:
        name = "MPEG-1 Audio Layer 1 (MP1) audio file"
        cached_data["ext"] = ".mp1"
    elif "Layer II" == mp3.header_results["layer"]:
        name = "MPEG-1 Audio Layer 2 (MP2) audio file"
        cached_data["ext"] = ".mp2"
    elif "Layer III (MP3)" == mp3.header_results["layer"]:
        name = "MPEG-1 Audio Layer 3 (MP3) audio file"
        cached_data["ext"] = ".mp3"
    else:
        name = "MPEG-1 Audio Unknown Layer audio file"  # This should never happen
    name_end = ""
    name_list = []
    try:
        if cached_data["name_format"]:
            name_list.extend(cached_data["name_format"])  # This adds sample, bitrate etc..
        if cached_data["name_end"]:
            name_list.extend(cached_data["name_end"])  # This adds tags
        name_end += f" [{' '.join(name_list)}]"
        cached_data["name"] = name + name_end
    except Exception:
        return None


def test_mp3(file_path: os.PathLike | str, head: bytes) -> Optional[Match]:
    """Test for MP3 format."""
    if cached_data.get("path") == file_path:
        # Tests if we already have matched data
        # We need this for speed as PureMagic calls this script more than once.
        if cached_data.get("matched"):
            return Match(extension=cached_data["ext"], name=cached_data["name"], mime_type="audio/mpeg", confidence=1.0)
        else:
            return None
    else:
        cached_data.clear()  # Clear for a new file
        cached_data.update(matched=False, name_end=[], name_format=[], name="", path=file_path)
        mp3 = mp3_decoding(file_path)
        try:
            with open(file_path, "rb") as file:
                mp3.footer_read(file)
                file.seek(0)
                # Files with a ID3v2 tag.
                if mp3_id3_match_bytes in head[:3]:  # ID3
                    mp3.check_id3v2_tag(head)
                    mp3.find_audio_start_and_header(file)
                    if mp3.first_frame_offset == -1:
                        return None  # Invalid MP3
                # Files without a ID3v2, assume frame 1 is at offset 0 tag.
                if head[:2] in mp3.mpeg_audio_signatures:  # Raw stream
                    file.seek(0)
                    header_bytes_frame1 = file.read(4)
                    if len(header_bytes_frame1) < 4:
                        return None  # Too short
                    try:
                        mp3.header_results = mp3.decode_mp3_header(header_bytes_frame1)
                        mp3.first_frame_offset = 0
                        mp3.header_bytes = header_bytes_frame1
                        file.seek(4, os.SEEK_SET)  # Set pointer after header for VBR check
                    except ValueError:
                        return None  # Invalid MP3
                # Start VBR/CBR check
                frame1_bit_rate_index = mp3.header_results["bit_rate_index"]
                raw_frame_size = mp3.header_results["raw_frame_size"]
                # bit_rate_f1 = mp3.bit_rates[frame1_bit_rate_index]
                # Read the rest of the metadata area for VBR/LAME check
                metadata_bytes = file.read(146)
                # Combine header and metadata area for VBR check
                frame_start_area = mp3.header_bytes + metadata_bytes
                # Check for VBR Header
                mp3.check_for_vbr_header(frame_start_area)
                # Check Stream Consistency by seeking to Frame 2 and 3
                if raw_frame_size > 0:
                    # Calculate the absolute start offset of Frame 2 (where F2 begins)
                    frame2_start_abs_offset = mp3.first_frame_offset + raw_frame_size

                    stream_type_deduction = mp3.check_stream_consistency(
                        file,  # File handle
                        frame1_bit_rate_index,  # F1 rate index
                        frame2_start_abs_offset,  # Absolute start offset of F2
                        raw_frame_size,  # Size of F1 (the step size)
                    )
                else:
                    stream_type_deduction = None

            mp3.end_of_file_tags()  # May not need file open any longer
            # We should be certain now if it's an MP3
            # If we can deduce CBR/VBR and Syncword was successfully decoded we shoud be safe
            if stream_type_deduction is not None and mp3.header_results.get("sync_word"):
                cached_data["name_format"].extend(
                    [
                        mp3.header_results["bit_rate"],
                        mp3.header_results["sample_rate"],
                        mp3.header_results["chanel_mode"],
                        stream_type_deduction,
                    ]
                )
                if mp3.vbr_type is not None:
                    cached_data["name_format"].append(mp3.vbr_type)
                build_name(mp3)
                cached_data.update(matched=True)
        except Exception:
            return None  # If we cannot decode an MP3 it's either corrupt or not an MP3.
        return Match(extension=cached_data["ext"], name=cached_data["name"], mime_type="audio/mpeg", confidence=1.0)


def main(file_path: os.PathLike | str, head: bytes) -> Optional[Match]:
    return test_mp3(file_path, head)
