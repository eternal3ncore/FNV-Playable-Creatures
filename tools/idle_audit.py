"""Scan plugins for everything that can make the player play an idle animation.
  IDLE   every record: EDID, MODL, parent / previous (ANAM), DATA, conditions (function, param, op, value, run-on)
  scripts with an idle command: SCTX of SCPT / INFO / QUST / PACK / PERK / TERM / MESG / NOTE / CHAL records that
         mention PlayIdle, PickIdle, StartMisterSandman, StartCannibal, ForceIdle, PlayGroup or SkipAnim
  PACK   idle lists (IDLA)
usage: python3 idle_audit.py out.json plugin.esm [plugin ...]   (paths; masters first)"""
import json, os, struct, sys, zlib

WANT = {b'IDLE', b'SCPT', b'DIAL', b'QUST', b'PACK', b'PERK', b'TERM', b'MESG', b'NOTE', b'CHAL', b'ACTI', b'ALCH'}
KEYS = (b'playidle', b'pickidle', b'startmistersandman', b'startcannibal', b'forceidle', b'playgroup', b'skipanim')


def subs(data):
    i = 0; big = None
    while i + 6 <= len(data):
        t = data[i:i + 4]; n, = struct.unpack_from('<H', data, i + 4); i += 6
        if t == b'XXXX': big, = struct.unpack_from('<I', data, i); i += n; continue
        if big is not None: n = big; big = None
        yield t.decode('latin1'), data[i:i + n]; i += n


def records(buf, off, end, out, plugin):
    while off < end:
        t = buf[off:off + 4]; size, = struct.unpack_from('<I', buf, off + 4)
        if t == b'GRUP':
            label = buf[off + 8:off + 12]; gtype, = struct.unpack_from('<i', buf, off + 12)
            if gtype != 0 or label in WANT: records(buf, off + 24, off + size, out, plugin)
            off += size; continue
        flags, fid = struct.unpack_from('<II', buf, off + 8)
        data = buf[off + 24:off + 24 + size]
        if t in WANT or t == b'INFO':
            if flags & 0x40000: data = zlib.decompress(data[4:])
            handle(t.decode(), fid, flags, data, out, plugin)
        off += 24 + size


def cond(v):
    typ = v[0]; val, = struct.unpack_from('<f', v, 4); fn, = struct.unpack_from('<H', v, 8)
    p1, p2 = struct.unpack_from('<II', v, 12); run = struct.unpack_from('<I', v, 20)[0] if len(v) >= 24 else 0
    ref = struct.unpack_from('<I', v, 24)[0] if len(v) >= 28 else 0
    return [fn, p1, p2, typ >> 5, typ & 0x1F, val, run, ref]


def handle(t, fid, flags, data, out, plugin):
    ss = list(subs(data)); d = {}
    for k, v in ss: d.setdefault(k, v)
    edid = d.get('EDID', b'').rstrip(b'\0').decode('latin1')
    if t == 'IDLE':
        an = d.get('ANAM', b'\0' * 8)
        out['idle'].append(dict(plugin=plugin, fid=fid, edid=edid, modl=d.get('MODL', b'').rstrip(b'\0').decode('latin1'),
                                parent=struct.unpack_from('<I', an, 0)[0], prev=struct.unpack_from('<I', an, 4)[0] if len(an) >= 8 else 0,
                                data=d.get('DATA', b'').hex(), cond=[cond(v) for k, v in ss if k == 'CTDA'], deleted=bool(flags & 0x20)))
        return
    for k, v in ss:
        if k == 'SCTX' and any(x in v.lower() for x in KEYS):
            out['script'].append(dict(plugin=plugin, type=t, fid=fid, edid=edid, text=v.rstrip(b'\0').decode('latin1')))
    if t == 'PACK':
        idl = [struct.unpack_from('<I', v, i)[0] for k, v in ss if k == 'IDLA' for i in range(0, len(v), 4)]
        if idl: out['pack'].append(dict(plugin=plugin, fid=fid, edid=edid, idles=idl))


def masters(buf):
    h = buf[24:24 + struct.unpack_from('<I', buf, 4)[0]]
    return [v.rstrip(b'\0').decode('latin1') for k, v in subs(h) if k == 'MAST']


if __name__ == '__main__':
    out = {'idle': [], 'script': [], 'pack': [], 'masters': {}}
    for p in sys.argv[2:]:
        buf = open(p, 'rb').read(); n = os.path.basename(p)
        out['masters'][n] = masters(buf)
        hs, = struct.unpack_from('<I', buf, 4)
        records(buf, 24 + hs, len(buf), out, n)
        print(n, len(out['idle']), len(out['script']), file=sys.stderr)
    json.dump(out, open(sys.argv[1], 'w'))
