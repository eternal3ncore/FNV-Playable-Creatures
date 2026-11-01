import os, struct, zlib, sys, json
GAME = os.path.expanduser('~/mnt/Fallout New Vegas/Data')
MO2 = os.path.expanduser('~/mnt/MO2')
prof = MO2 + '/profiles/Default/'
mods = [l[1:].strip() for l in open(prof + 'modlist.txt', encoding='utf-8', errors='replace') if l.startswith('+')]
plugins = [l.strip() for l in open(prof + 'plugins.txt', encoding='utf-8', errors='replace') if l.strip() and not l.startswith('#')]
plugins = [p.lstrip('*') for p in plugins]
def find(name):
    for m in mods:                       # top of modlist = highest priority
        p = os.path.join(MO2, 'mods', m, name)
        if os.path.exists(p): return p
    p = os.path.join(GAME, name)
    return p if os.path.exists(p) else None
def records(data, typ):
    out = []
    def walk(i, end):
        while i < end:
            t = data[i:i+4]
            if t == b'GRUP':
                gsz, lab, gt = struct.unpack_from('<I4sI', data, i+4)
                if gt == 0 and lab != typ.encode(): i += gsz; continue
                walk(i+24, i+gsz); i += gsz
            else:
                sz, fl, fid = struct.unpack_from('<III', data, i+4)
                if t == typ.encode():
                    raw = data[i+24:i+24+sz]
                    if fl & 0x40000: raw = zlib.decompress(raw[4:])
                    out.append((fid, fl, raw))
                i += 24 + sz
    hdr = struct.unpack_from('<I', data, 4)[0]
    walk(24 + hdr, len(data))
    return out
def subs(raw):
    i = 0; o = []
    while i < len(raw):
        t = raw[i:i+4].decode('latin1'); s = struct.unpack_from('<H', raw, i+4)[0]; o.append((t, raw[i+6:i+6+s])); i += 6 + s
    return o
def masters(data):
    hsz = struct.unpack_from('<I', data, 4)[0]
    return [v.rstrip(b'\0').decode('latin1') for t, v in subs(data[24:24+hsz]) if t == 'MAST']
res = []
for pi, pl in enumerate(plugins):
    path = find(pl)
    if not path: res.append(dict(plugin=pl, missing=True)); continue
    data = open(path, 'rb').read()
    ms = masters(data)
    for fid, fl, raw in records(data, 'IDLE'):
        mi = fid >> 24
        owner = ms[mi] if mi < len(ms) else pl
        ss = subs(raw); d = dict(ss)
        anam = struct.unpack('<II', d['ANAM']) if 'ANAM' in d else (0, 0)
        def g(f):
            m = f >> 24
            return [ms[m] if m < len(ms) else pl, f & 0xFFFFFF] if f else None
        res.append(dict(plugin=pl, owner=owner, fid=fid & 0xFFFFFF, edid=d.get('EDID', b'').rstrip(b'\0').decode('latin1'),
                        modl=d.get('MODL', b'').rstrip(b'\0').decode('latin1'), parent=g(anam[0]), prev=g(anam[1]),
                        data=d.get('DATA', b'').hex(), ctda=[c.hex() for t, c in ss if t == 'CTDA']))
json.dump(res, open(os.path.expanduser('~/mnt/Fallout New Vegas/_PCWork/idlescan.json'), 'w'))
print(len(res), 'idle records;', sum(1 for r in res if r.get('missing')), 'missing plugins')
