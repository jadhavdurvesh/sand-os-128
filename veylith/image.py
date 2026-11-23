"""VYLI v2 executable image with 128-bit entry addresses, segment addresses and sizes."""
MAGIC=b"VYLI"
VERSION=2
MAX_SEGMENTS=64
U128_MAX=(1<<128)-1
class ImageError(ValueError): pass
def _u128(value,label):
    if not isinstance(value,int) or not 0<=value<=U128_MAX: raise ImageError(f"{label} must be an unsigned 128-bit integer")
    return value.to_bytes(16,"little")
def pack(segments,entry):
    if len(segments)>MAX_SEGMENTS: raise ImageError("too many segments")
    out=bytearray(MAGIC+VERSION.to_bytes(2,"little")+len(segments).to_bytes(2,"little")+_u128(entry,"entry"))
    for addr,data in segments:
        data=bytes(data);out+=_u128(addr,"segment address")+_u128(len(data),"segment size")+data
    return bytes(out)
def unpack(blob):
    if len(blob)<24 or blob[:4]!=MAGIC: raise ImageError("bad or truncated VYLI v2 header")
    version=int.from_bytes(blob[4:6],"little");count=int.from_bytes(blob[6:8],"little");entry=int.from_bytes(blob[8:24],"little")
    if version!=VERSION: raise ImageError(f"unsupported image version {version}; expected {VERSION}")
    if count>MAX_SEGMENTS: raise ImageError("too many segments")
    off,segs=24,[]
    for _ in range(count):
        if off+32>len(blob): raise ImageError("truncated segment header")
        addr=int.from_bytes(blob[off:off+16],"little");size=int.from_bytes(blob[off+16:off+32],"little");off+=32
        if size>len(blob)-off: raise ImageError("truncated segment data")
        segs.append((addr,blob[off:off+size]));off+=size
    if off!=len(blob): raise ImageError("trailing bytes after last segment")
    return segs,entry
