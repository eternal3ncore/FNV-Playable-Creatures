import struct, re, sys
from pe import PE
p = PE('FalloutNV_unpacked.exe')
T0 = p.off(0x401000); TEXT = p.d[T0:T0 + 0xbdd5f0]
def find_str(s, ci=True):
    out = []
    for m in re.finditer(re.escape(s.encode()), p.d, re.I if ci else 0):
        va = p.va(m.start())
        # extend to full C-string
        st = m.start()
        while st > 0 and 32 <= p.d[st-1] < 127: st -= 1
        en = p.d.index(b'\0', m.start())
        out.append((p.va(st), p.d[st:en].decode('latin1')))
    return sorted(set(out))
def xrefs(va):
    b = struct.pack('<I', va); res = []
    for m in re.finditer(re.escape(b), TEXT):
        res.append(0x401000 + m.start())
    return res
if __name__ == '__main__':
    for s in sys.argv[1:]:
        for va, full in find_str(s):
            xs = xrefs(va)
            print(hex(va), repr(full), [hex(x) for x in xs[:12]])
