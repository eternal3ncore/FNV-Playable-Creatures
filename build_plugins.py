"""Builds the Playable Creatures plugins: one per creature family (families.py), PlayableCreatures_<Family>.esp.

  1. the race records of every family are built together, as before: build_esp.py (New Vegas races, New Vegas master
     list) and build_esp_ttw.py (Tale of Two Wastelands races, ids 0x8800.., TTW master list)
  2. each family plugin takes its records (EDID prefixes, families.py) verbatim - same local ids, same master list -
     plus a copy of the shared records it uses (the empty hair / eyes), renamed PC<Family>NoHair / PC<Family>Eyes, and
     its own copy of the empty mesh path (PlayableCreatures\\<family folder>\\Empty.nif)
  3. its voice records (build_voices.py: own quest, topic overrides, INFOs) are merged in
An add-on (addon_of) lists its base family's plugin as its last master, so its own forms move up one index.
New Vegas families need only New Vegas + its DLC and also run under Tale of Two Wastelands; TTW families need TTW's masters.

usage: python3 build_plugins.py <out dir>   -> <out>/PlayableCreatures_<Family>.esp + voice_plan_<Family>.tsv"""
import os, struct, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from esm import Plugin
from families import FAMILIES, BY_NAME, FNV_MASTERS, TTW_MASTERS, EMPTY_OLD, masters_of, empty_path, family_of_edid

VOICE_ID_BASE = '0x4800'
TTW_ID_BASE = '0x8800'
# vanilla top-group order (FalloutNV.esm)
ORDER = ('GMST TXST MICN GLOB CLAS FACT HDPT HAIR EYES RACE SOUN ASPC MGEF SCPT LTEX ENCH SPEL ACTI TACT TERM ARMO BOOK '
         'CONT DOOR INGR LIGH MISC STAT SCOL MSTT PWAT GRAS TREE FURN WEAP AMMO NPC_ CREA LVLC LVLN KEYM ALCH IDLM NOTE '
         'COBJ PROJ LVLI WTHR CLMT REGN NAVI CELL WRLD DIAL QUST IDLE PACK CSTY LSCR ANIO WATR EFSH EXPL DEBR IMGS IMAD '
         'FLST PERK BPTD ADDN AVIF RADS CAMS CPTH VTYP IPCT IPDS ARMA ECZN MESG RGDL DOBJ LGTM MUSC IMOD REPU RCPE RCCT '
         'CHIP CSNO LSCT MSET ALOC CHAL AMEF CCRD CMNY CDCK DEHY HUNG SLPD').split()
# shared by several families: each family plugin gets its own copy, named after the family
SHARED = {'PCZetanNoHair': 'PC{}NoHair', 'PCZetanEyes': 'PC{}Eyes', 'PCTTWNoHair': 'PC{}NoHair', 'PCTTWEyes': 'PC{}Eyes'}
UNUSED = {'PCRadImmunityAbility'}      # no record, ini key or DLL code refers to it (radiation immunity = race abilities)


def z(s): return s.encode('latin1') + b'\0'
def sub(t, data):
    if len(data) > 0xFFFF: return b'XXXX' + struct.pack('<HI', 4, len(data)) + t.encode() + struct.pack('<H', 0) + data
    return t.encode() + struct.pack('<H', len(data)) + data


def run(script, out, env, *extra):
    e = dict(os.environ, **env)
    r = subprocess.run([sys.executable, '-P', os.path.join(HERE, script), out, *extra], env=e, capture_output=True, text=True, cwd='/tmp')
    if r.returncode: sys.exit(f'{script} failed:\n{r.stdout}\n{r.stderr}')
    return r.stdout


BPND_FORMS = (12, 16, 32, 36, 68, 72)      # the form ids in a body part's BPND (debris, explosions, impact data sets); the
                                           # rest is floats / bytes that can read like one of our ids


def refs_at(data, own):
    """offsets of every 4-byte value in data that is one of our own form ids"""
    return [i for i in range(len(data) - 3) if struct.unpack_from('<I', data, i)[0] in own]


class Src:
    """one built plugin: its records, own index and the own-form references of each record"""
    def __init__(self, path):
        self.p = Plugin(path)
        self.recs = [r for r in self.p.recs if r.type != 'TES4']
        hdr = self.p.recs[0]
        self.masters = [v.rstrip(b'\0').decode('latin1') for k, v in hdr.subs() if k == 'MAST']
        self.own_idx = len(self.masters)
        self.own = {r.fid for r in self.recs if r.fid >> 24 == self.own_idx}
        self.refs = {r.fid: {struct.unpack_from('<I', v, i)[0] for k, v in r.subs() if k != 'EDID' for i in refs_at(v, self.own)
                             if (k != 'BPND' or i in BPND_FORMS) and not (r.type == 'WEAP' and k == 'DATA')}   # WEAP DATA: value / health / weight / damage / clip, no form ids
                     for r in self.recs}


def family_records(fam, src):
    """the family's records (+ copies of the shared ones it uses) from src -> [(rec, edid override)]"""
    races = {(src.own_idx << 24) | l for l in fam['races']}
    pick = []
    for r in src.recs:
        e = r.edid()
        if r.fid >> 24 != src.own_idx:          # override of a master's record: goes with the family whose races it names
            fams = {f['name'] for f in FAMILIES if src.refs[r.fid] & {(src.own_idx << 24) | l for l in f['races']}}
            assert len(fams) == 1, (hex(r.fid), e, fams)
            if fams == {fam['name']}: pick.append(r)
        elif e not in SHARED and e not in UNUSED and family_of_edid(e) == fam['name']:
            pick.append(r)
    chosen = {r.fid for r in pick}
    assert races <= chosen, (fam['name'], [hex(x) for x in races - chosen])
    need = set().union(*(src.refs[r.fid] for r in pick)) - chosen if pick else set()
    byfid = {r.fid: r for r in src.recs}
    out = [(r, None) for r in pick]
    for f in sorted(need):
        e = byfid[f].edid()
        assert e in SHARED, f'{fam["name"]}: {e} ({f:08X}) belongs to another family'
        out.append((byfid[f], SHARED[e].format(fam['name'])))
    return out


def write_family_records(path, fam, src, recs):
    masters = masters_of(fam)
    assert masters[:src.own_idx] == src.masters, (masters, src.masters)
    new_idx = len(masters)
    own = src.own
    groups = {}; next_id = 0
    empty_old = z(EMPTY_OLD).lower(); empty_new = z(empty_path(fam))
    for r, new_edid in recs:
        subs = []
        for k, v in r.subs():
            if k == 'EDID' and new_edid: v = z(new_edid)
            elif v.lower() == empty_old: v = empty_new
            elif new_idx != src.own_idx and k != 'EDID':
                b = bytearray(v)
                for i in refs_at(v, own): b[i + 3] = new_idx
                v = bytes(b)
            subs.append((k, v))
        fid = r.fid if r.fid >> 24 != src.own_idx else (new_idx << 24) | (r.fid & 0xFFFFFF)
        if fid >> 24 == new_idx: next_id = max(next_id, (fid & 0xFFFFFF) + 1)
        body = b''.join(sub(k, v) for k, v in subs)
        raw = src.p.mm[r.off - 24:r.off]
        groups.setdefault(r.type, []).append(raw[:4] + struct.pack('<II', len(body), r.flags) + struct.pack('<I', fid) + raw[16:24] + body)
    out = b''
    for label in ORDER:
        if label in groups:
            body = b''.join(groups[label])
            out += b'GRUP' + struct.pack('<I4sIIHH', 24 + len(body), label.encode(), 0, 0, 0, 0) + body
    hdr = [('HEDR', struct.pack('<fII', 1.34, len(recs), next_id)), ('CNAM', z('i3ncore'))]
    for m in masters: hdr += [('MAST', z(m)), ('DATA', struct.pack('<Q', 0))]
    body = b''.join(sub(k, v) for k, v in hdr)
    open(path, 'wb').write(b'TES4' + struct.pack('<IIIIHH', len(body), 0, 0, 0, 15, 0) + body + out)


def parse(path):
    """-> (masters, next_id, {label: body bytes}, [(fid, edid, type)])"""
    d = open(path, 'rb').read()
    hsz = struct.unpack_from('<I', d, 4)[0]
    h = d[24:24 + hsz]; i = 0; masters = []; next_id = 0
    while i < len(h):
        t = h[i:i + 4].decode(); n = struct.unpack_from('<H', h, i + 4)[0]; v = h[i + 6:i + 6 + n]; i += 6 + n
        if t == 'MAST': masters.append(v.rstrip(b'\0').decode('latin1'))
        elif t == 'HEDR': next_id = struct.unpack_from('<I', v, 8)[0]
    groups = {}; recs = []
    o = 24 + hsz
    while o < len(d):
        assert d[o:o + 4] == b'GRUP'
        gsz = struct.unpack_from('<I', d, o + 4)[0]; label = d[o + 8:o + 12].decode()
        groups[label] = groups.get(label, b'') + d[o + 24:o + gsz]
        o += gsz
    for r in Plugin(path).recs:
        if r.type != 'TES4': recs.append((r.fid, r.edid(), r.type))
    return masters, next_id, groups, recs


def count(body):
    """records + groups inside a group body (DIAL children included)"""
    n = 0; o = 0
    while o < len(body):
        if body[o:o + 4] == b'GRUP':
            gsz = struct.unpack_from('<I', body, o + 4)[0]; n += 1 + count(body[o + 24:o + gsz]); o += gsz
        else:
            n += 1; o += 24 + struct.unpack_from('<I', body, o + 4)[0]
    return n


def merge(out, masters, desc, parts):
    groups = {}; seen_fid = {}; seen_edid = {}; next_id = 0
    for path in parts:
        m, nid, g, recs = parse(path)
        assert m == masters, (path, m, masters)
        next_id = max(next_id, nid)
        for fid, edid, typ in recs:
            assert fid not in seen_fid, f'duplicate form id {fid:08X} {edid} in {path} and {seen_fid[fid]}'
            seen_fid[fid] = path
            if edid and typ != 'DIAL':
                assert edid not in seen_edid, f'duplicate EDID {edid} in {path} and {seen_edid[edid]}'
                seen_edid[edid] = path
        for label, body in g.items(): groups[label] = groups.get(label, b'') + body
    unknown = set(groups) - set(ORDER); assert not unknown, unknown
    out_groups = b''; nrec = 0
    for label in ORDER:
        if label in groups:
            body = groups[label]
            out_groups += b'GRUP' + struct.pack('<I4sIIHH', 24 + len(body), label.encode(), 0, 0, 0, 0) + body
            nrec += 1 + count(body)
    hdr = [('HEDR', struct.pack('<fII', 1.34, nrec, next_id)), ('CNAM', z('i3ncore')), ('SNAM', z(desc))]
    for mm in masters: hdr += [('MAST', z(mm)), ('DATA', struct.pack('<Q', 0))]
    body = b''.join(sub(k, v) for k, v in hdr)
    open(out, 'wb').write(b'TES4' + struct.pack('<IIIIHH', len(body), 0, 0, 0, 15, 0) + body + out_groups)
    return nrec, len(seen_fid), next_id


DESC = {
    'Zetan': 'Zetan aliens (plain and helmeted)',
    'GhostPeople': 'Ghost People of the Sierra Madre (hooded and unhooded)',
    'FeralGhouls': 'Feral Ghoul and Glowing One',
    'SuperMutants': 'Super Mutant and Nightkin',
    'Tunnelers': 'Tunneler and Spore Carrier',
    'Eyebot': 'Eyebot', 'Securitron': 'Securitron and Securitron Mk II', 'Protectron': 'Protectron', 'Robobrain': 'Robobrain',
    'MisterHandy': 'Mister Handy and Mister Gutsy', 'SentryBot': 'Sentry Bot', 'Deathclaw': 'Deathclaw, Deathclaw Alpha / Mother and Legendary Deathclaw (Young Deathclaw child races)',
    'Lakelurks': 'Lakelurk and Lakelurk Alpha (Young Lakelurk child races)',
    'Mirelurks': 'Mirelurk, Mirelurk Hunter and Nukalurk (Tale of Two Wastelands)',
    'Swampfolk': 'Point Lookout swampfolk (Tale of Two Wastelands)', 'Trogs': 'The Pitt trogs (Tale of Two Wastelands)',
    'SuperMutantsTTW': 'Capital Wasteland super mutants (Tale of Two Wastelands add-on to the Super Mutants plugin)',
    'RobobrainTTW': 'Fallout 3 robobrain voice for female robobrains (Tale of Two Wastelands add-on to the Robobrain plugin)',
}


def main():
    outdir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'build', 'plugins')
    os.makedirs(outdir, exist_ok=True)
    tmp = tempfile.mkdtemp()
    p = lambda n: os.path.join(tmp, n)
    run('build_esp.py', p('nv_races.esp'), {'PC_MASTERS': ','.join(FNV_MASTERS)})
    run('build_esp_ttw.py', p('ttw_races.esp'), {'PC_MASTERS': ','.join(TTW_MASTERS), 'PC_TTW_ID_BASE': TTW_ID_BASE})
    nv, ttw = Src(p('nv_races.esp')), Src(p('ttw_races.esp'))
    placed = {}
    for fam in FAMILIES:
        name = fam['name']; plugin = fam['plugin']; masters = masters_of(fam)
        parts = []
        if fam['races']:
            src = ttw if fam['ttw'] else nv
            recs = family_records(fam, src)
            for r, _ in recs:
                if _ is None: placed.setdefault((src is ttw, r.fid), []).append(name)
            write_family_records(p(name + '_races.esp'), fam, src, recs); parts.append(p(name + '_races.esp'))
        base = BY_NAME[fam['addon_of']] if fam['addon_of'] and not fam['races'] else fam
        voice_races = fam['races'] or base['races']
        env = {'PC_MASTERS': ','.join(masters), 'PC_VOICE_PLUGIN': plugin, 'PC_VOICE_ID_BASE': VOICE_ID_BASE,
               'PC_VOICE_RACES': ','.join('%X' % r for r in voice_races), 'PC_VOICE_TTW': '1' if fam['ttw'] else '0',
               'PC_RACE_PLUGIN': base['plugin'], 'PC_VOICE_QUEST': 'PCVoice' + name,
               'PC_VOICE_PRIORITY': '111' if fam['addon_of'] and not fam['races'] else '110'}
        print(run('build_voices.py', p(name + '_voices.esp'), env, os.path.join(outdir, f'voice_plan_{name}.tsv')).strip().splitlines()[0])
        parts.append(p(name + '_voices.esp'))
        r = merge(os.path.join(outdir, plugin), masters, f'Playable Creatures: {DESC[name]} as playable races. Needs PlayableCreatures.dll (xNVSE).', parts)
        print('%-40s %4d records+groups, %4d forms, next id %X' % ((plugin,) + r))
    # every record of the two builds is in exactly one family plugin (shared copies and the unused ability aside)
    for src, is_ttw in ((nv, False), (ttw, True)):
        for r in src.recs:
            if r.edid() in SHARED or r.edid() in UNUSED: continue
            got = placed.get((is_ttw, r.fid), [])
            assert len(got) == 1, (is_ttw, hex(r.fid), r.edid(), got)
    print('all race records placed once')


if __name__ == '__main__':
    main()
