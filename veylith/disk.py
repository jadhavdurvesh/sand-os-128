"""SAND-128 virtual-machine disk container (512-byte header + VYLI v2 payload)."""
import struct
from . import asm, image
MAGIC=b"SAND128D"
VERSION=1
SECTOR_SIZE=512
HEADER=struct.Struct("<8sIIQQQ")
DEFAULT_SIZE=2<<20
class DiskError(ValueError): pass
def checksum(data):
    h=14695981039346656037
    for b in data:
        h^=b
        h=(h*1099511628211)&0xffffffffffffffff
    return h
def pack(payload,disk_size=DEFAULT_SIZE):
    payload=bytes(payload);minimum=SECTOR_SIZE+len(payload)
    if disk_size<minimum or disk_size%SECTOR_SIZE:raise DiskError("disk size must be a 512-byte multiple large enough for VYLI payload")
    header=HEADER.pack(MAGIC,VERSION,SECTOR_SIZE,SECTOR_SIZE,len(payload),checksum(payload))
    return header+bytes(SECTOR_SIZE-len(header))+payload+bytes(disk_size-minimum)
def unpack(blob):
    if len(blob)<SECTOR_SIZE:raise DiskError("truncated SAND-128 boot sector")
    magic,version,sector,offset,length,digest=HEADER.unpack(blob[:HEADER.size])
    if magic!=MAGIC or version!=VERSION or sector!=SECTOR_SIZE or offset!=SECTOR_SIZE:raise DiskError("unsupported SAND-128 disk header")
    if length>len(blob)-offset:raise DiskError("truncated VYLI payload")
    payload=blob[offset:offset+length]
    if checksum(payload)!=digest:raise DiskError("disk payload checksum mismatch")
    image.unpack(payload)
    return payload
def build(kernel_source,user_source,disk_size=DEFAULT_SIZE):
    kernel=asm.assemble(kernel_source);user=asm.assemble(user_source)
    ks,entry=image.unpack(kernel);us,_=image.unpack(user)
    return pack(image.pack(ks+us,entry),disk_size)
