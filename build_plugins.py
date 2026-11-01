"""Builds the two Playable Creatures plugins (use one or the other, never both):

  PlayableCreatures.esp     Fallout: New Vegas without TTW: the base-game / DLC races (build_esp.py) + their combat
                            voices (build_voices.py, New Vegas sets). Masters: FalloutNV + the DLC whose quests the
                            voice topics carry.
  PlayableCreaturesTTW.esp  Tale of Two Wastelands: the same base races with the SAME local ids (build_esp.py run with
                            this plugin's masters) + the Fallout 3 creature races (build_esp_ttw.py, ids 0x8800..) +
                            every voice set (ids 0x4800.., identical to PlayableCreatures.esp's). PlayableCreatures.dll
                            resolves any PlayableCreatures.esp|<id> reference to PlayableCreaturesTTW.esp|<id> when only
                            the TTW plugin is loaded, so one ini serves both.

Voice ids: build_voices allocates over all sets from PC_VOICE_ID_BASE, so a line has the same id - and file name - in
both plugins; files live under sound\\voice\\<plugin>\\...
usage: python3 build_plugins.py <out dir>   -> <out>/PlayableCreatures.esp, PlayableCreaturesTTW.esp,
                                               voice_plan_fnv.tsv, voice_plan_ttw.tsv"""
import os, struct, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

FNV_MASTERS = ['FalloutNV.esm', 'DeadMoney.esm', 'HonestHearts.esm', 'LonesomeRoad.esm', 'OldWorldBlues.esm']
TTW_MASTERS = FNV_MASTERS + ['Fallout3.esm', 'Anchorage.esm', 'ThePitt.esm', 'BrokenSteel.esm', 'PointLookout.esm', 'Zeta.esm']
VOICE_ID_BASE = '0x4800'
TTW_ID_BASE = '0x8800'
# vanilla top-group order (FalloutNV.esm)
ORDER = ('GMST TXST MICN GLOB CLAS FACT HDPT HAIR EYES RACE SOUN ASPC MGEF SCPT LTEX ENCH SPEL ACTI TACT TERM ARMO BOOK '
         'CONT DOOR INGR LIGH MISC STAT SCOL MSTT PWAT GRAS TREE FURN WEAP AMMO NPC_ CREA LVLC LVLN KEYM ALCH IDLM NOTE '
         'COBJ PROJ LVLI WTHR CLMT REGN NAVI CELL WRLD DIAL QUST IDLE PACK CSTY LSCR ANIO WATR EFSH EXPL DEBR IMGS IMAD '
         'FLST PERK BPTD ADDN AVIF RADS CAMS CPTH VTYP IPCT IPDS ARMA ECZN MESG RGDL DOBJ LGTM MUSC IMOD REPU RCPE RCCT '
         'CHIP CSNO LSCT MSET ALOC CHAL AMEF CCRD CMNY CDCK DEHY HUNG SLPD').split()


def z(s): return s.encode('latin1') + b'\0'
def sub(t, data): return t.encode() + struct.pack('<H', len(data)) + data


def run(script, out, env, *extra):
    e = dict(os.environ, **env)
    r = subprocess.run([sys.executable, os.path.join(HERE, script), out, *extra], env=e, capture_output=True, text=True, cwd='/tmp')
    if r.returncode: sys.exit(f'{script} failed:\n{r.stdout}\n{r.stderr}')
    return r.stdout


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
    from esm import Plugin
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
            # DIAL overrides of FalloutNV topics appear once (voices part only); everything else must be unique
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
    hdr = [('HEDR', struct.pack('<fII', 1.34, nrec, next_id)), ('CNAM', z('Claude (Playable Creatures project)')), ('SNAM', z(desc))]
    for mm in masters: hdr += [('MAST', z(mm)), ('DATA', struct.pack('<Q', 0))]
    body = b''.join(sub(k, v) for k, v in hdr)
    open(out, 'wb').write(b'TES4' + struct.pack('<IIIIHH', len(body), 0, 0, 0, 15, 0) + body + out_groups)
    return nrec, len(seen_fid), next_id


def main():
    outdir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'build', 'merged')
    os.makedirs(outdir, exist_ok=True)
    tmp = tempfile.mkdtemp()
    p = lambda n: os.path.join(tmp, n)
    # ---- PlayableCreatures.esp (no TTW)
    run('build_esp.py', p('fnv_races.esp'), {'PC_MASTERS': ','.join(FNV_MASTERS)})
    print(run('build_voices.py', p('fnv_voices.esp'), {'PC_MASTERS': ','.join(FNV_MASTERS), 'PC_VOICE_PLUGIN': 'PlayableCreatures.esp',
                                                         'PC_VOICE_SETS': 'fnv', 'PC_VOICE_ID_BASE': VOICE_ID_BASE},
              os.path.join(outdir, 'voice_plan_fnv.tsv')).strip())
    r = merge(os.path.join(outdir, 'PlayableCreatures.esp'), FNV_MASTERS,
              'Playable Creatures (Fallout: New Vegas): Zetan, Ghost People, Feral Ghoul, Glowing One, Super Mutant, Nightkin, '
              'Tunneler, Spore Carrier as playable races, with their combat voices. For Tale of Two Wastelands use '
              'PlayableCreaturesTTW.esp instead (not both).',
              [p('fnv_races.esp'), p('fnv_voices.esp')])
    print('PlayableCreatures.esp: %d records+groups, %d forms, next id %X' % r)
    # ---- PlayableCreaturesTTW.esp (TTW: both race sets + all voices)
    run('build_esp.py', p('ttw_base.esp'), {'PC_MASTERS': ','.join(TTW_MASTERS)})
    run('build_esp_ttw.py', p('ttw_races.esp'), {'PC_MASTERS': ','.join(TTW_MASTERS), 'PC_TTW_ID_BASE': TTW_ID_BASE})
    print(run('build_voices.py', p('ttw_voices.esp'), {'PC_MASTERS': ','.join(TTW_MASTERS), 'PC_VOICE_PLUGIN': 'PlayableCreaturesTTW.esp',
                                                         'PC_VOICE_SETS': 'all', 'PC_VOICE_ID_BASE': VOICE_ID_BASE},
              os.path.join(outdir, 'voice_plan_ttw.tsv')).strip())
    r = merge(os.path.join(outdir, 'PlayableCreaturesTTW.esp'), TTW_MASTERS,
              'Playable Creatures (Tale of Two Wastelands): every Playable Creatures race - Zetan, Ghost People, Feral Ghoul, '
              'Glowing One, Super Mutant, Nightkin, Tunneler, Spore Carrier, Swampfolk, Trogs, Capital Wasteland super '
              'mutants - with their combat voices. Use instead of PlayableCreatures.esp (not both).',
              [p('ttw_base.esp'), p('ttw_races.esp'), p('ttw_voices.esp')])
    print('PlayableCreaturesTTW.esp: %d records+groups, %d forms, next id %X' % r)


if __name__ == '__main__':
    main()
