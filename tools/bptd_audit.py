"""Audit: does every race's body part data let the player's ragdoll set up its head pose?
The engine (0x87E130) takes the first part of the player's BPTD with flags 0x02 (IK data) and 0x20 (IK headtracking)
and looks its IK start node (BPNI) up in the ragdoll's hkaSkeleton (the skeleton nodes that carry a collision object,
parented to the nearest such ancestor); the bone and its parent must exist. Races without BodyPartData= use the
player's DefaultBodyPartData (FalloutNV 00001D).
usage: python3 bptd_audit.py <folder with meshes\\PlayableCreatures\\*\\Skeleton*.nif> <ini folder> <plugins folder>"""
import sys, os, glob, configparser
sys.path.insert(0, '/home/claude/fnv')
from esm import Plugin, zstr
from nifedit import NifFile
ROOT, INI, PLUG = sys.argv[1:4]
ESM = {'falloutnv.esm': Plugin('/home/claude/fnv/FalloutNV.esm'), 'deadmoney.esm': Plugin('/home/claude/fnv/DeadMoney.esm')}
def plugin(name):
    k = name.lower()
    if k not in ESM:
        p = os.path.join(PLUG, name)
        if not os.path.exists(p): p = os.path.join('/home/claude/fnv/ttw', name)      # TTW masters (PointLookout, ThePitt...)
        ESM[k] = Plugin(p) if os.path.exists(p) else None
    return ESM[k]
def bptd(ref):
    if not ref: ref = 'FalloutNV.esm|00001D'
    name, fid = ref.split('|'); fid = int(fid, 16); note = ''
    p = plugin(name)
    if p is None and name.lower() == 'fallout3.esm': p, note = ESM['falloutnv.esm'], ' (Fallout3.esm not here: FalloutNV record of the same id)'
    if p is None: return None, ref + ' not found'
    idx = len(p.recs[0].getall('MAST')) if name.lower() not in ('falloutnv.esm',) else 0
    r = p.byfid.get((idx << 24) | fid) or p.byfid.get(fid)
    return r, ref + note
def ragdoll(skel):
    f = NifFile(skel); par = {}; coll = set(); names = {}
    for i, t in enumerate(f.btype):
        if f.types[t] in ('NiNode', 'BSFadeNode'):
            r = f.node(i); names[i] = f.strings[r['name']] if r['name'] >= 0 else ''
            if r['coll'] != -1: coll.add(i)
            for c in r['children']: par[c] = i
    out = {}
    for i in coll:
        p = par.get(i)
        while p is not None and p not in coll: p = par.get(p)
        out[names[i]] = names[p] if p is not None else None
    return out
def ancestor(skel, name, rd):
    f = NifFile(skel); par = {}; idx = {}
    for i, t in enumerate(f.btype):
        if f.types[t] in ('NiNode', 'BSFadeNode'):
            r = f.node(i); idx[f.strings[r['name']] if r['name'] >= 0 else ''] = i
            for c in r['children']: par[c] = i
    names = {v: k for k, v in idx.items()}
    i = idx.get(name)
    p = par.get(i) if i is not None else None
    while p is not None:
        if names.get(p) in rd: return names[p]
        p = par.get(p)
    return None
for ini in sorted(glob.glob(os.path.join(INI, '*.ini'))):
    cp = configparser.ConfigParser(strict=False, interpolation=None); cp.optionxform = str
    cp.read(ini, encoding='latin1')
    for sec in cp.sections():
        s = cp[sec]
        if 'Skeleton' not in s: continue
        skel = os.path.join(ROOT, 'meshes', *s['Skeleton'].split('\\'))
        if not os.path.exists(skel): print(f'{sec:24s} skeleton missing {skel}'); continue
        rd = ragdoll(skel)
        r, where = bptd(s.get('BodyPartData', ''))
        if r is None: print(f'{sec:24s} {where}'); continue
        part = None; parts = []; cur = {}
        for k, v in r.subs():
            if k == 'BPTN': cur = {'name': zstr(v)}; parts.append(cur)
            elif k == 'BPNI': cur['ik'] = zstr(v)
            elif k == 'BPND': cur['flags'] = v[4]
        ht = [p for p in parts if p.get('flags', 0) & 0x22 == 0x22]
        if not ht:
            near = [p for p in parts if p.get('flags', 0) & 0x20]
            print(f'{sec:24s} FAIL  {r.edid()} ({where}): no part with IK data + headtracking' +
                  (f" ({near[0]['name']} flags {near[0]['flags']:02X}, ik '{near[0].get('ik')}')" if near else '')); continue
        h = ht[0]; ik = h.get('ik', '')
        if ik not in rd:
            anc = ancestor(skel, ik, rd)        # DLL v79: the head pose is set up from the nearest ragdoll ancestor
            if anc: print(f"{sec:24s} ok    {r.edid()} ({where}): {h['name']} flags {h['flags']:02X} ik '{ik}' -> pose from ragdoll ancestor {anc}")
            else: print(f"{sec:24s} FAIL  {r.edid()} ({where}): {h['name']} ik '{ik}' is no ragdoll bone and has no ragdoll ancestor")
            continue
        if rd[ik] is None: print(f"{sec:24s} FAIL  {r.edid()} ({where}): {h['name']} ik '{ik}' has no ragdoll parent"); continue
        print(f"{sec:24s} ok    {r.edid()} ({where}): {h['name']} flags {h['flags']:02X} ik '{ik}' (ragdoll parent {rd[ik]})")
