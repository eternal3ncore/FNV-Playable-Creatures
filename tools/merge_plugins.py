"""Merges family plugins (PlayableCreatures_<Family>.esp) into one plugin, plus its settings file.

Local ids stay as they are (the families were split from combined builds, so they don't overlap) except the few every
family has its own copy of - the empty hair / eyes (0x801 / 0x802, TTW 0x8800 / 0x8801) and the voice quest (0x4800):
the first family keeps them, the others get fresh ids after every family's next id. Own-form references are rewritten
the way build_plugins.py does for add-ons (every 4-byte value that is one of the family's own forms; WEAP DATA and the
non-form BPND bytes skipped); an add-on's references to its base plugin become the merged plugin's.
The vanilla combat topics (Hit / Death / Attack / PowerAttack) that every family's voice records override are merged:
one DIAL override with every family's quest (QSTI) and one child group with every family's INFOs (each conditioned on
its own races, so their order doesn't matter).
Settings: every section of the families' settings files, Plugin= and every Plugin|FormID naming a merged plugin
changed to the merged plugin (ids through the same map). Voices: sound\\voice\\<family plugin>\\ -> sound\\voice\\<merged>\\
(the file names carry the INFO ids, which don't change).
usage: python3 merge_plugins.py <out.esp> <masters: nv|ttw> <family plugin dir> <settings dir> <out.ini> Family [...]"""
import os, re, struct, sys, zlib
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE))
from families import BY_NAME, FNV_MASTERS, TTW_MASTERS, masters_of
from build_plugins import ORDER, refs_at, BPND_FORMS, sub, z

FLAG_COMPRESSED = 0x40000


def subs_of(data):
    out = []; i = 0; big = None
    while i < len(data):
        t = data[i:i + 4].decode('latin1'); n, = struct.unpack_from('<H', data, i + 4); i += 6
        if t == 'XXXX': big, = struct.unpack_from('<I', data, i); i += n; continue
        if big is not None: n = big; big = None
        out.append((t, data[i:i + n])); i += n
    return out


class Rec:
    def __init__(s, typ, flags, fid, vc, data, children=None):
        s.type = typ; s.flags = flags; s.fid = fid; s.vc = vc; s.data = data; s.children = children   # children: DIAL topic group records
    def subs(s):
        d = zlib.decompress(s.data[4:]) if s.flags & FLAG_COMPRESSED else s.data
        return subs_of(d)
    def set_subs(s, subs):
        s.data = b''.join(sub(k, v) for k, v in subs); s.flags &= ~FLAG_COMPRESSED
    def edid(s):
        for k, v in s.subs():
            if k == 'EDID': return v.rstrip(b'\0').decode('latin1')
        return ''
    def raw(s):
        out = s.type.encode() + struct.pack('<III', len(s.data), s.flags, s.fid) + s.vc + s.data
        if s.children is not None:
            body = b''.join(r.raw() for r in s.children)
            out += b'GRUP' + struct.pack('<IIiI', 24 + len(body), s.fid, 7, 0) + b'\0' * 4 + body
        return out


def read(path):
    d = open(path, 'rb').read()
    hsz, = struct.unpack_from('<I', d, 4)
    hdr = subs_of(d[24:24 + hsz])
    masters = [v.rstrip(b'\0').decode('latin1') for k, v in hdr if k == 'MAST']
    next_id = [struct.unpack_from('<I', v, 8)[0] for k, v in hdr if k == 'HEDR'][0]
    tops = {}
    def recs_in(o, e):
        out = []
        while o < e:
            if d[o:o + 4] == b'GRUP':
                gsz, label, gtype = struct.unpack_from('<IIi', d, o + 4)
                assert gtype == 7 and out and out[-1].type == 'DIAL' and out[-1].fid == label, (path, o, gtype)
                out[-1].children = recs_in(o + 24, o + gsz); o += gsz; continue
            t = d[o:o + 4].decode('latin1'); sz, fl, fid = struct.unpack_from('<III', d, o + 4)
            out.append(Rec(t, fl, fid, d[o + 16:o + 24], d[o + 24:o + 24 + sz])); o += 24 + sz
        return out
    o = 24 + hsz
    while o < len(d):
        assert d[o:o + 4] == b'GRUP'
        gsz = struct.unpack_from('<I', d, o + 4)[0]; label = d[o + 8:o + 12].decode('latin1')
        tops.setdefault(label, []).extend(recs_in(o + 24, o + gsz)); o += gsz
    return masters, next_id, tops


def all_recs(tops):
    for recs in tops.values():
        for r in recs:
            yield r
            for c in r.children or []: yield c


def main():
    out, mset, src_dir, ini_dir, out_ini, *names = sys.argv[1:]
    M = FNV_MASTERS if mset == 'nv' else TTW_MASTERS
    O = len(M); merged = os.path.basename(out)
    fams = [BY_NAME[n] for n in names]
    data = {}
    for f in fams:
        assert masters_of(f)[:len(TTW_MASTERS if f['ttw'] else FNV_MASTERS)] == M[:len(TTW_MASTERS if f['ttw'] else FNV_MASTERS)]
        if f['ttw']: assert mset == 'ttw', f['name'] + ' needs the TTW master list'
        data[f['name']] = read(os.path.join(src_dir, f['plugin']))
        assert data[f['name']][0] == masters_of(f), (f['name'], data[f['name']][0])
    # id maps: family -> {old full id: new full id}
    next_free = max(nid for _, nid, _ in data.values())
    taken = set(); maps = {}
    for f in fams:
        masters, nid, tops = data[f['name']]; oi = len(masters)
        mp = {}
        for r in all_recs(tops):
            if r.fid >> 24 != oi: continue
            l = r.fid & 0xFFFFFF
            if l in taken: l = next_free; next_free += 1
            taken.add(l); mp[r.fid] = (O << 24) | l
        maps[f['name']] = mp
    for f in fams:                                   # an add-on's references to its base plugin's forms
        if f['addon_of']:
            base = BY_NAME[f['addon_of']]; assert base['name'] in maps, f['name'] + ' needs ' + base['name']
            bi = len(masters_of(f)) - 1; boi = len(masters_of(base))
            maps[f['name']].update({(bi << 24) | (k & 0xFFFFFF): v for k, v in maps[base['name']].items() if k >> 24 == boi})
    # rewrite every record of every family
    groups = {}; dial = {}
    for f in fams:
        mp = maps[f['name']]; own = set(mp)
        masters, nid, tops = data[f['name']]
        def fix(r):
            subs = []
            for k, v in r.subs():
                if k != 'EDID':
                    b = bytearray(v)
                    for i in refs_at(v, own):
                        if (k == 'BPND' and i not in BPND_FORMS) or (r.type == 'WEAP' and k == 'DATA'): continue
                        struct.pack_into('<I', b, i, mp[struct.unpack_from('<I', v, i)[0]])
                    v = bytes(b)
                subs.append((k, v))
            r.set_subs(subs); r.fid = mp.get(r.fid, r.fid)
            for c in r.children or []: fix(c)
        for label, recs in tops.items():
            for r in recs:
                fix(r)
                if r.type == 'DIAL' and r.fid >> 24 < O:         # an override of a vanilla topic: merged below
                    if r.fid not in dial: dial[r.fid] = r; groups.setdefault(label, []).append(r)
                    else:
                        d0 = dial[r.fid]; s0 = d0.subs(); have = {v for k, v in s0 if k == 'QSTI'}
                        add = [(k, v) for k, v in r.subs() if k in ('QSTI', 'QSTR') and v not in have]
                        last = max(i for i, (k, _) in enumerate(s0) if k in ('QSTI', 'QSTR'))
                        d0.set_subs(s0[:last + 1] + add + s0[last + 1:])
                        d0.children = (d0.children or []) + (r.children or [])
                else: groups.setdefault(label, []).append(r)
    # checks: unique ids / editor ids
    seen = {}; eds = {}
    for label, recs in groups.items():
        for r in recs:
            for x in [r] + (r.children or []):
                assert x.fid not in seen, f'duplicate id {x.fid:08X}'; seen[x.fid] = 1
                e = x.edid()
                if e and x.type not in ('DIAL',):
                    assert e not in eds, f'duplicate EDID {e}'; eds[e] = 1
    unknown = set(groups) - set(ORDER); assert not unknown, unknown
    body = b''; nrec = 0
    for label in ORDER:
        if label not in groups: continue
        g = b''.join(r.raw() for r in groups[label])
        body += b'GRUP' + struct.pack('<I4sIIHH', 24 + len(g), label.encode(), 0, 0, 0, 0) + g
        nrec += 1 + sum(1 + (0 if r.children is None else 1 + len(r.children)) for r in groups[label])
    desc = ('Playable Creatures: every New Vegas race in one plugin' if mset == 'nv' else
            'Playable Creatures: every race (New Vegas + Tale of Two Wastelands) in one plugin') + \
           '. Replaces the pack plugins (don\'t load both). Needs PlayableCreatures.dll (xNVSE).'
    hdr = [('HEDR', struct.pack('<fII', 1.34, nrec, next_free)), ('CNAM', z('i3ncore')), ('SNAM', z(desc))]
    for m in M: hdr += [('MAST', z(m)), ('DATA', struct.pack('<Q', 0))]
    h = b''.join(sub(k, v) for k, v in hdr)
    open(out, 'wb').write(b'TES4' + struct.pack('<IIIIHH', len(h), 0, 0, 0, 15, 0) + h + body)
    ren = [(f['name'], k & 0xFFFFFF, v & 0xFFFFFF) for f in fams for k, v in maps[f['name']].items()
           if (k & 0xFFFFFF) != (v & 0xFFFFFF) and k >> 24 == len(masters_of(f))]
    print(f'{merged}: {len(fams)} families, {len(seen)} forms, {nrec} records+groups, next id {next_free:X}, renumbered {len(ren)}: '
          + ', '.join(f'{n} {a:X}->{b:X}' for n, a, b in ren))
    # settings
    plugins = {f['plugin'].lower(): f['name'] for f in fams}
    lines = [f'; Playable Creatures - {merged}: race settings for the merged plugin, read by PlayableCreatures.dll.',
             '; One section per race; the keys are described in PlayableCreatures_INI_KEYS.md (Playable Creatures Core).', '']
    def ref(m):
        p, l = m.group(1), int(m.group(2), 16)
        if p.lower() not in plugins: return m.group(0)
        f = BY_NAME[plugins[p.lower()]]; oi = len(masters_of(f))
        return f'{merged}|{maps[f["name"]].get((oi << 24) | l, (O << 24) | l) & 0xFFFFFF:06X}'
    nsec = 0
    for f in fams:
        p = os.path.join(ini_dir, f'PlayableCreatures_{f["name"]}.ini')
        if not os.path.exists(p): continue
        sec = None; oi = len(masters_of(f))
        for line in open(p, encoding='utf-8').read().replace('\r', '').split('\n'):
            if not line or line.startswith(';'): continue
            if line.startswith('['):
                if lines[-1] != '': lines.append('')
                lines.append(line); nsec += 1; continue
            k, _, v = line.partition('=')
            if k == 'Plugin': v = merged
            elif k in ('Race', 'ChildRace'): v = f'{maps[f["name"]][(oi << 24) | int(v, 16)] & 0xFFFFFF:06X}'
            else: v = re.sub(r'([^|,\s]+\.es[mp])\|([0-9A-Fa-f]+)', ref, v)
            lines.append(f'{k}={v}')
        lines.append('')
    open(out_ini, 'w', newline='\r\n').write('\n'.join(lines))
    print(f'{os.path.basename(out_ini)}: {nsec} sections')


if __name__ == '__main__':
    main()
