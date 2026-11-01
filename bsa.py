"""BSA (FO3/FNV) reader. Usage:
  python3 bsa.py list <bsa> [substr...]
  python3 bsa.py extract <bsa> <outdir> <substr...>
"""
import struct, zlib, sys, os

class BSA:
    def __init__(s, path):
        s.f = open(path, 'rb'); f = s.f
        magic, ver, off, s.aflags, nfold, nfile, lfold, lfile, fflags = struct.unpack('<4sIIIIIIII', f.read(36))
        assert magic == b'BSA\0', magic
        folders = [struct.unpack('<QII', f.read(16)) for _ in range(nfold)]
        recs = []
        for h, cnt, o in folders:
            if s.aflags & 1:
                n = f.read(1)[0]; fname = f.read(n)[:-1].decode('latin1')
            else: fname = ''
            for _ in range(cnt):
                fh, sz, fo = struct.unpack('<QII', f.read(16)); recs.append([fname, None, sz, fo])
        if s.aflags & 2:
            names = f.read(lfile).split(b'\0')
            for r, n in zip(recs, names): r[1] = n.decode('latin1')
        s.files = recs
    def paths(s):
        return [f"{d}\\{n}" for d, n, _, _ in s.files]
    def read(s, rec):
        d, n, sz, fo = rec
        comp = bool(s.aflags & 4) ^ bool(sz & 0x40000000)
        sz &= 0x3FFFFFFF
        s.f.seek(fo); data = s.f.read(sz)
        if s.aflags & 0x100:
            l = data[0]; data = data[1 + l:]
        if comp:
            data = zlib.decompress(data[4:])
        return data

if __name__ == '__main__':
    cmd, path = sys.argv[1], sys.argv[2]
    b = BSA(path)
    if cmd == 'list':
        subs = [x.lower() for x in sys.argv[3:]]
        for d, n, sz, fo in b.files:
            p = f"{d}\\{n}"
            if all(x in p.lower() for x in subs): print(p, sz & 0x3FFFFFFF)
    elif cmd == 'extract':
        out = sys.argv[3]; subs = [x.lower() for x in sys.argv[4:]]
        k = 0
        for rec in b.files:
            p = f"{rec[0]}\\{rec[1]}"
            if any(x in p.lower() for x in subs):
                dst = os.path.join(out, *p.split('\\'))
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                open(dst, 'wb').write(b.read(rec)); k += 1
        print('extracted', k)
