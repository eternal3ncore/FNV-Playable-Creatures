import struct
class PE:
    def __init__(s, path):
        s.d = open(path,'rb').read(); d = s.d
        e = struct.unpack_from('<I', d, 0x3c)[0]
        nsec = struct.unpack_from('<H', d, e+6)[0]; opt = struct.unpack_from('<H', d, e+20)[0]
        s.base = struct.unpack_from('<I', d, e+24+28)[0]
        s.secs = []
        o = e + 24 + opt
        for i in range(nsec):
            name = d[o:o+8].rstrip(b'\0').decode(); vs, va, rs, ro = struct.unpack_from('<IIII', d, o+8)
            s.secs.append((name, s.base+va, vs, ro, rs)); o += 40
    def off(s, va):
        for n, v, vs, ro, rs in s.secs:
            if v <= va < v + max(vs, rs): return ro + va - v
    def read(s, va, n): o = s.off(va); return s.d[o:o+n]
    def va(s, off):
        for n, v, vs, ro, rs in s.secs:
            if ro <= off < ro + rs: return v + off - ro
