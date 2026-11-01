"""Race abilities + child races, shared by build_esp.py and build_esp_ttw.py.

Race abilities: TESRace has a TESSpellList (RTTI: TESRace -> TESSpellList at +0x2C) and TESRace's LoadForm reads SPLO
into it (0x610fdf: SPLO -> 0x48d290 on race+0x2C), the same list NPC_ / CREA abilities use. Each creature race lists
one custom ability, "<Race> Physiology", whose effects are the creature's own (copied from the vanilla spells, with
their conditions), plus Radiation Immunity (+100 Rad Resistance) for races the radiation shouldn't hurt (radiation
doesn't damage NPCs, so immunity is the player-side equivalent; PlayableCreatures.dll raises the resistance cap to
100 while the player is such a race - ini RadImmune / ResistCap).

Child races: Tranquility Lane (MQ04) runs player.AgeRace -1 / +1, which follows the race's younger (YNAM) / older
(ONAM) links. Every creature race gets a child race: same record, Child flag (DATA flags 0x4) instead of Playable,
height / weight x 0.8 (the vanilla child races' ratio), ONAM -> the adult race; the adult race gets YNAM -> the child.
The child race lists the same ability. PlayableCreatures.dll treats a profile's ChildRace= like the race itself."""
import struct


def z(s): return s.encode('latin1') + b'\0'
def u32(v): return struct.pack('<I', v)


def parse(rec):
    typ = rec[:4].decode(); size, flags, fid = struct.unpack_from('<III', rec, 4)
    body = rec[24:24 + size]; subs = []; i = 0
    while i < len(body):
        t = body[i:i + 4].decode('latin1'); n = struct.unpack_from('<H', body, i + 4)[0]
        subs.append((t, body[i + 6:i + 6 + n])); i += 6 + n
    return typ, flags, fid, subs


def build(typ, flags, fid, subs):
    body = b''.join(t.encode() + struct.pack('<H', len(v)) + v for t, v in subs)
    return typ.encode() + struct.pack('<IIIIHH', len(body), flags, fid, 0, 15, 0) + body


def effects(spel_rec):
    """the EFID / EFIT / CTDA subrecords of a vanilla SPEL (esm.Rec), verbatim"""
    return [(k, v) for k, v in spel_rec.subs() if k in ('EFID', 'EFIT', 'CTDA')]


SPIT_ABILITY = bytes.fromhex('04000000000000000000000000000000')     # type 4 = Ability (as RadImmunity 060C16)
RAD_IMMUNITY = [('EFID', u32(0x15179)), ('EFIT', struct.pack('<IIIIi', 100, 0, 0, 0, 0x14))]   # +100 Rad Resistance


def ability(fid, edid, full, effs):
    return build('SPEL', 0, fid, [('EDID', z(edid)), ('FULL', z(full)), ('SPIT', SPIT_ABILITY)] + effs)


def add_extras(race_recs, spells_by_edid, new_id):
    """race_recs: RACE record bytes. spells_by_edid: race EDID -> [SPEL fid] (may be empty).
    Returns (adult race records with SPLO + YNAM, child race records, {adult EDID: child fid})"""
    adults, children, child_ids = [], [], {}
    for rec in race_recs:
        typ, flags, fid, subs = parse(rec)
        assert typ == 'RACE'
        edid = subs[0][1].rstrip(b'\0').decode('latin1')
        spells = spells_by_edid.get(edid, [])
        cfid = new_id(); child_ids[edid] = cfid
        a, c = [], []
        for k, v in subs:
            if k in ('ONAM', 'YNAM', 'SPLO'): continue
            if k == 'EDID':
                a.append((k, v)); c.append((k, z(edid[:-4] + 'ChildRace' if edid.endswith('Race') else edid + 'Child')))
                continue
            if k == 'DATA':
                a.append((k, v))
                d = bytearray(v)
                hm, hf, wm, wf = struct.unpack_from('<ffff', d, 16)
                struct.pack_into('<ffff', d, 16, hm * 0.8, hf * 0.8, wm * 0.8, wf * 0.8)
                struct.pack_into('<I', d, 32, (struct.unpack_from('<I', d, 32)[0] & ~0x1) | 0x4)   # Child, not playable
                c.append((k, bytes(d)))
                a.append(('YNAM', u32(cfid))); c.append(('ONAM', u32(fid)))
                continue
            a.append((k, v)); c.append((k, v))
            if k == 'DESC':                                  # abilities after the description (Oblivion RACE order)
                for s in spells: a.append(('SPLO', u32(s))); c.append(('SPLO', u32(s)))
        adults.append(build('RACE', flags, fid, a)); children.append(build('RACE', flags, cfid, c))
    return adults, children, child_ids


# wearable creature armor (super mutant / nightkin armor as items): a copy of FalloutNV ArmorLeather
# (020423) with the model, biped slots, stats replaced. biped: 0x04 UpperBody (whole-body meshes: the race's body is
# hidden), 0x08 LeftHand (the races' "bare" loincloth slot: an armor-only part worn over the body). Ground model = the
# same mesh (shown at its bind pose).
ARMO_TEMPLATE = 0x020423
def armor(src_plugin, fid, edid, name, model, biped, value, health, weight, dt, heavy=False):
    out = []
    for k, v in src_plugin.byfid[ARMO_TEMPLATE].subs():
        if k == 'EDID': v = z(edid)
        elif k == 'FULL': v = z(name)
        elif k == 'BMDT': v = struct.pack('<IB3s', biped, 0x80 if heavy else 0, b'\0\0\0')
        elif k in ('MODL', 'MOD2', 'MOD3', 'MOD4'): v = z(model)
        elif k in ('MODT', 'MO2T', 'MO3T', 'MO4T', 'MODD', 'MOSD', 'BIPL', 'EITM', 'TNAM'): continue
        elif k == 'DATA': v = struct.pack('<IIf', value, health, weight)
        elif k == 'DNAM': d = bytearray(v); struct.pack_into('<f', d, 4, float(dt)); v = bytes(d)
        out.append((k, v))
    return build('ARMO', 0, fid, out)
