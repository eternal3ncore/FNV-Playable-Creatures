import struct, re, sys
from pe import PE
p = PE('FalloutNV_unpacked.exe')
u32 = lambda va: struct.unpack('<I', p.read(va, 4))[0]
def td_name(td):
    o = p.off(td + 8); return p.d[o:p.d.index(b'\0', o)].decode('latin1')
def vtables_of(clsname):
    # find type descriptor ".?AVname@@"
    m = p.d.find(('.?AV%s@@' % clsname).encode() + b'\0')
    td = p.va(m) - 8
    # find COLs referencing td (COL: sig, offset, cdOffset, pTD, pCHD)
    res = []
    for mm in re.finditer(re.escape(struct.pack('<I', td)), p.d):
        colva = p.va(mm.start() - 12)
        if colva is None: continue
        sig, off, cdo = struct.unpack('<III', p.read(colva, 12))
        if sig != 0: continue
        # vtable = location after pointer to COL
        for m2 in re.finditer(re.escape(struct.pack('<I', colva)), p.d):
            vt = p.va(m2.start()) + 4
            res.append((off, hex(vt)))
    return sorted(res)
if __name__ == '__main__':
    for c in sys.argv[1:]: print(c, vtables_of(c))
