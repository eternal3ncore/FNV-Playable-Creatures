"""Minimal FNV (TES4-format) plugin reader for analysis."""
import struct, zlib, mmap

class Rec:
    __slots__ = ("type", "flags", "fid", "off", "size", "_subs", "_f")
    def __init__(s, f, typ, flags, fid, off, size):
        s._f = f; s.type = typ; s.flags = flags; s.fid = fid; s.off = off; s.size = size; s._subs = None
    def data(s):
        raw = s._f.mm[s.off:s.off + s.size]
        if s.flags & 0x00040000:
            raw = zlib.decompress(raw[4:])
        return raw
    def subs(s):
        if s._subs is None:
            d = s.data(); out = []; i = 0; big = None
            while i < len(d):
                t = d[i:i+4].decode('latin1'); sz = struct.unpack_from('<H', d, i+4)[0]; i += 6
                if t == 'XXXX':
                    big = struct.unpack_from('<I', d, i)[0]; i += sz; continue
                if big is not None: sz = big; big = None
                out.append((t, d[i:i+sz])); i += sz
            s._subs = out
        return s._subs
    def get(s, t):
        for k, v in s.subs():
            if k == t: return v
    def getall(s, t):
        return [v for k, v in s.subs() if k == t]
    def edid(s):
        v = s.get('EDID'); return v.rstrip(b'\0').decode('latin1') if v else ''
    def __repr__(s): return f"<{s.type} {s.fid:08X} {s.edid()}>"

def zstr(b):
    return b.split(b'\0')[0].decode('latin1') if b is not None else None

class Plugin:
    def __init__(s, path):
        s.fh = open(path, 'rb'); s.mm = mmap.mmap(s.fh.fileno(), 0, access=mmap.ACCESS_READ)
        s.recs = []; s.byfid = {}; s.byedid = {}
        s._walk(0, len(s.mm))
    def _walk(s, start, end):
        i = start; mm = s.mm
        while i < end:
            t = mm[i:i+4].decode('latin1')
            if t == 'GRUP':
                gsz = struct.unpack_from('<I', mm, i+4)[0]
                s._walk(i + 24, i + gsz); i += gsz
            else:
                sz, fl, fid = struct.unpack_from('<III', mm, i+4)
                r = Rec(s, t, fl, fid, i + 24, sz)
                s.recs.append(r); s.byfid[fid] = r; i += 24 + sz
    def index_edids(s, types=None):
        for r in s.recs:
            if types and r.type not in types: continue
            e = r.edid()
            if e: s.byedid[e] = r
    def of(s, t): return [r for r in s.recs if r.type == t]
