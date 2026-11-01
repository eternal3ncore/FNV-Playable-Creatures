import struct, re, sys
from pe import PE
p = PE('FalloutNV_unpacked.exe'); T0 = p.off(0x401000); TEXT = p.d[T0:T0+0xbdd5f0]
def funcstart(a):
    i = a - 0x401000
    while i > 0:
        if TEXT[i:i+3] == b'\x55\x8b\xec' and TEXT[i-1] in (0xcc, 0xc3, 0x90): return 0x401000 + i
        i -= 1
_callmap = None
def callers(target):
    global _callmap
    if _callmap is None:
        _callmap = {}
        for m in re.finditer(rb'[\xe8\xe9]', TEXT):
            i = m.start()
            if i + 5 > len(TEXT): break
            rel = struct.unpack_from('<i', TEXT, i+1)[0]
            _callmap.setdefault((0x401000 + i + 5 + rel) & 0xFFFFFFFF, []).append((0x401000 + i, 'call' if TEXT[i] == 0xe8 else 'jmp'))
    ptr = [p.va(m.start()) for m in re.finditer(re.escape(struct.pack('<I', target)), p.d)]
    return _callmap.get(target, []), ptr
if __name__ == "__main__":
    for a in sys.argv[1:]:
        t = funcstart(int(a[1:], 16)) if a.startswith("f") else int(a, 16)
        c, ptrs = callers(t)
        print(hex(t), [(hex(x), k, hex(funcstart(x))) for x, k in c][:25], 'ptrs', [hex(x) for x in ptrs if x][:10])
