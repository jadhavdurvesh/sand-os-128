"""SAND-128 virtual-machine disk container (512-byte boot header + VYLI v2 payload)."""
import hashlib
import struct
from . import asm, image

MAGIC = b"SAND128D"
VERSION = 1
SECTOR_SIZE = 512
HEADER = struct.Struct("<8sIIQQ32s")
DEFAULT_SIZE = 2 << 20

class DiskError(ValueError):
    pass

def pack(payload, disk_size=DEFAULT_SIZE):
    payload = bytes(payload)
    minimum = SECTOR_SIZE + len(payload)
    if disk_size < minimum or disk_size % SECTOR_SIZE:
        raise DiskError("disk size must be a 512-byte multiple large enough for the VYLI payload")
    header = HEADER.pack(MAGIC, VERSION, SECTOR_SIZE, SECTOR_SIZE, len(payload), hashlib.sha256(payload).digest())
    return header + bytes(SECTOR_SIZE - len(header)) + payload + bytes(disk_size - minimum)

def unpack(blob, verify=True):
    if len(blob) < SECTOR_SIZE:
        raise DiskError("truncated SAND-128 boot sector")
    magic, version, sector, offset, length, digest = HEADER.unpack(blob[:HEADER.size])
    if magic != MAGIC or version != VERSION or sector != SECTOR_SIZE or offset != SECTOR_SIZE:
        raise DiskError("unsupported SAND-128 disk header")
    if length > len(blob) - offset:
        raise DiskError("truncated VYLI payload in disk image")
    payload = blob[offset:offset + length]
    if verify and hashlib.sha256(payload).digest() != digest:
        raise DiskError("VYLI payload checksum mismatch")
    image.unpack(payload)
    return payload

def build(kernel_source, user_source, disk_size=DEFAULT_SIZE):
    kernel = asm.assemble(kernel_source)
    user = asm.assemble(user_source)
    kernel_segments, entry = image.unpack(kernel)
    user_segments, _ = image.unpack(user)
    return pack(image.pack(kernel_segments + user_segments, entry), disk_size)
