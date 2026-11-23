"""VYLI image format (version 1): a list of loadable segments plus an entry address, little-endian."""
import struct

MAGIC = b"VYLI"
VERSION = 1
MAX_SEGMENTS = 64


class ImageError(ValueError):
    pass


def pack(segments, entry):
    """segments: list of (address, bytes)."""
    if len(segments) > MAX_SEGMENTS:
        raise ImageError("too many segments")
    out = bytearray(MAGIC + struct.pack("<HHQ", VERSION, len(segments), entry))
    for addr, data in segments:
        out += struct.pack("<QQ", addr, len(data)) + bytes(data)
    return bytes(out)


def unpack(blob):
    if len(blob) < 16 or blob[:4] != MAGIC:
        raise ImageError("bad magic")
    version, nseg, entry = struct.unpack_from("<HHQ", blob, 4)
    if version != VERSION:
        raise ImageError(f"unsupported image version {version}")
    if nseg > MAX_SEGMENTS:
        raise ImageError("too many segments")
    off, segs = 16, []
    for _ in range(nseg):
        if off + 16 > len(blob):
            raise ImageError("truncated segment header")
        addr, size = struct.unpack_from("<QQ", blob, off)
        off += 16
        if size > len(blob) - off:
            raise ImageError("truncated segment data")
        segs.append((addr, blob[off:off + size]))
        off += size
    if off != len(blob):
        raise ImageError("trailing bytes after last segment")
    return segs, entry
