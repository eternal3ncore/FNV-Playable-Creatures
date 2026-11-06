"""Builds the Fallout 3 creatures of Tale of Two Wastelands as playable races (split into the Swampfolk, Trogs and
SuperMutantsTTW family plugins by build_plugins.py; PlayableCreatures.dll picks the races up from its ini sections).
  Swampfolk (Point Lookout, skeleton PlayableCreatures\\Swampfolk = DLC04 Hillfolk2and3): Brawler, Scrapper, Creeper
  Swampfolk (Point Lookout, skeleton PlayableCreatures\\Hillfolk = DLC04 Hillfolk1): Tracker, Bruiser
  Trogs (The Pitt, skeleton PlayableCreatures\\Trog = DLCPitt StreetTrog): Trog, Trog Brute, Trog Savage
Bodies are the creatures' own meshes from the TTW archives (whole creature in the body slot, head parts empty).
Per-skeleton idle trees (furniture + knock-down get-ups), same structure as the New Vegas races (build_esp.py);
get-ups = the creatures' own vanilla files. Only master: FalloutNV.esm (body / animation paths need TTW's archives).
+ Capital Wasteland super mutants (Super Mutant / Brute / Master) on the Super Mutant set (ids from 0x877).
usage: python3 build_esp_ttw.py <out.esp>"""
import struct, sys
sys.path.insert(0, '/home/claude/fnv')
from esm import Plugin

SRC = Plugin('/home/claude/fnv/FalloutNV.esm')
OUT = sys.argv[1] if len(sys.argv) > 1 else '/home/claude/fnv/build/ttw/PlayableCreaturesTTW.esp'
# masters + id base are parameters (PC_MASTERS, PC_TTW_ID_BASE): build_plugins.py builds these records with the TTW
# master list at ids 0x8800.. (clear of the New Vegas races' ids, so every race id is unique across the families)
import os
MASTERS = os.environ.get('PC_MASTERS', 'FalloutNV.esm').split(',')
assert MASTERS[0] == 'FalloutNV.esm', MASTERS
MOD = len(MASTERS) << 24                                 # our own forms
EMPTY = 'PlayableCreatures\\Zetan\\Empty.nif'   # empty mesh shipped by Playable Creatures
_next = [int(os.environ.get('PC_TTW_ID_BASE', '0x800'), 16)]
def nid():
    v = MOD | _next[0]; _next[0] += 1; return v
def z(s): return s.encode('latin1') + b'\0'
def sub(t, data): return t.encode() + struct.pack('<H', len(data)) + data
def record(t, fid, subs, flags=0):
    body = b''.join(sub(k, v) for k, v in subs)
    return t.encode() + struct.pack('<IIIIHH', len(body), flags, fid, 0, 15, 0) + body
def group(label, recs):
    body = b''.join(recs)
    return b'GRUP' + struct.pack('<I4sIIHH', 24 + len(body), label.encode(), 0, 0, 0, 0) + body
u32 = lambda v: struct.pack('<I', v)

HAIR, EYES = nid(), nid()
hair = record('HAIR', HAIR, [('EDID', z('PCTTWNoHair')), ('FULL', z('None')), ('MODL', z(EMPTY)),
                             ('ICON', z('Characters\\Hair\\HairWavy.dds')), ('DATA', bytes([0x01]))])
eyes = record('EYES', EYES, [('EDID', z('PCTTWEyes')), ('FULL', z('Creature')), ('ICON', z('Characters\\Eyes\\EyeDefault.dds')), ('DATA', bytes([0x01]))])

cauc = SRC.byfid[0x19]
def make_race(fid, edid, full, desc, body):
    """copy of build_esp.make_race (Caucasian template; whole creature in the body slot, empty head / hands)"""
    out = []; section = None; subs = cauc.subs(); i = 0
    while i < len(subs):
        k, v = subs[i]
        if k == 'EDID': out.append((k, z(edid)))
        elif k == 'FULL': out.append((k, z(full)))
        elif k == 'DESC': out.append((k, z(desc)))
        elif k == 'DATA':
            d = bytearray(v); d[0:14] = bytes([0xFF, 0x00] * 7)
            struct.pack_into('<ffff', d, 16, 1.0, 1.0, 1.0, 1.0); struct.pack_into('<I', d, 32, 0x1)
            out.append((k, bytes(d)))
        elif k in ('ONAM', 'YNAM'): pass
        elif k == 'DNAM': out.append((k, u32(HAIR) * 2))
        elif k == 'NAM0': section = 'head'; out.append((k, v))
        elif k == 'NAM1': section = 'body'; out.append((k, v))
        elif k in ('MNAM', 'FNAM') and section: out.append((k, v))
        elif k == 'INDX' and section in ('body', 'head'):
            idx = struct.unpack('<I', v)[0]; j = i + 1; part = []
            while j < len(subs) and subs[j][0] in ('ICON', 'MODL', 'MODT', 'MODD', 'MICO'): part.append(subs[j]); j += 1
            if section == 'body' and idx == 3: i = j; continue          # body FaceGen tint dropped
            out.append((k, v))
            for pk, pv in part:
                if pk == 'MODL': out.append(('MODL', z(body if (section == 'body' and idx == 0) else EMPTY)))
                elif pk in ('MODT', 'MODD'): pass
                else: out.append((pk, pv))
            i = j; continue
        elif k == 'HNAM': out.append((k, u32(HAIR)))
        elif k == 'ENAM': section = None; out.append((k, u32(EYES)))
        else: out.append((k, v))
        i += 1
    return record('RACE', fid, out)

def preset(fid, edid, female, race):
    tpl = SRC.byfid[0x568F7]; o = []
    for k, v in tpl.subs():
        if k == 'EDID': o.append((k, z(edid)))
        elif k == 'FULL': o.append((k, z(edid)))
        elif k == 'ACBS':
            a = bytearray(v); fl = struct.unpack_from('<I', a, 0)[0]
            fl = (fl & ~0x1) | 0x4 | (0x1 if female else 0); struct.pack_into('<I', a, 0, fl); o.append((k, bytes(a)))
        elif k == 'VTCK': o.append((k, u32(0x2E if female else 0x2D)))
        elif k == 'RNAM': o.append((k, u32(race)))
        elif k == 'PNAM': pass
        elif k == 'HNAM': o.append((k, u32(HAIR)))
        elif k == 'ENAM': o.append((k, u32(EYES)))
        else: o.append((k, v))
    return record('NPC_', fid, o)

HF23 = 'DLC04\\Creatures\\Hillfolk2and3\\Anims\\'; HF1 = 'DLC04\\Creatures\\Hillfolk1\\'; TROG = 'DLCPitt\\Creatures\\StreetTrog\\'
SWAMP = 'Swampfolk of Point Lookout: inbred, mutated backwoods folk of the Maryland swamps. Playable Creatures (TTW).'
TROGD = 'Trogs of the Pitt: humans twisted by the Pitt\'s mutagenic pollution into feral, light-shy cannibals. Playable Creatures (TTW).'
RACES = [   # (EDID, name, body, description)  -> race ids 0x804.., presets follow
    ('PCSwampfolkBrawlerRace', 'Swampfolk Brawler', HF23 + 'HillFolk2.NIF', SWAMP),
    ('PCSwampfolkScrapperRace', 'Swampfolk Scrapper', HF23 + 'Hillfolk3Scrapper.NIF', SWAMP),
    ('PCSwampfolkCreeperRace', 'Swampfolk Creeper', HF23 + 'Hillfolk3Creeper.NIF', SWAMP),
    ('PCSwampfolkTrackerRace', 'Swampfolk Tracker', HF1 + 'Hillfolk_Skin.NIF', SWAMP),
    ('PCSwampfolkBruiserRace', 'Swampfolk Bruiser', HF1 + 'bruiser.nif', SWAMP),
    ('PCTrogRace', 'Trog', TROG + 'streettrog.nif', TROGD),
    ('PCTrogBruteRace', 'Trog Brute', TROG + 'streettrog2.nif', TROGD),
    ('PCTrogSavageRace', 'Trog Savage', TROG + 'streettrog3.nif', TROGD),
]
races = []; npcs = []; race_ids = {}
for edid, full, body, desc in RACES:
    rid = nid(); race_ids[edid] = rid; races.append(make_race(rid, edid, full, desc, body))
for edid, full, body, desc in RACES:
    base = edid[:-4]; rid = race_ids[edid]
    npcs += [preset(nid(), base + 'PresetMale', False, rid), preset(nid(), base + 'PresetFemale', True, rid)]

# ---------------- IDLE trees (as build_esp.py) ----------------
F_SITTING, F_SLEEPING, F_MARKER, F_ISID, F_PC1ST, F_RANDOM, F_FACEUP, F_KNOCKED, F_HITLOC, F_USEDITEM = 159, 49, 160, 72, 392, 77, 106, 107, 391, 247
def ctda(func, comp, op=0, p1=0, OR=False):
    return struct.pack('<B3sfHHIIII', (op << 5) | (1 if OR else 0), b'\0\0\0', float(comp), func, 0, p1, 0, 0, 0)
IS_1ST_PERSON = [ctda(F_ISID, 1, 0, 0x7), ctda(F_PC1ST, 1)]
HUMAN = 'Characters\\_Male\\IdleAnims\\'
idles = []
IDLE_BY_EDID = {}
def idle(edid, modl, conds, parent, data, prev=0):
    fid = nid(); IDLE_BY_EDID[edid] = fid
    idles.append(record('IDLE', fid, [('EDID', z(edid)), ('MODL', z(modl))] + [('CTDA', c) for c in conds] +
                        [('ANAM', struct.pack('<II', parent, prev)), ('DATA', bytes.fromhex(data))]))
    return fid
def chain(parent, items):
    prev = 0; out = []
    for edid, modl, conds, data in items: prev = idle(edid, modl, conds, parent, data, prev); out.append(prev)
    return out
SIDES = (('Left', 11), ('Right', 12), ('Back', 13), ('Front', None))
def creature_idles(tag, folder, chair_enter, chair_exit, chair_loop, stool_enter, stool_exit, stool_loop, specials, get_up):
    G = folder
    root, = chain(0, [(f'PC{tag}FurnitureIdles', G, [ctda(F_SITTING, 0, 2, OR=True), ctda(F_SLEEPING, 0, 2)], '840000cd0000003c')])
    sitting, = chain(root, [(f'PC{tag}Sitting', G, [ctda(F_SITTING, 0, 2)], '840000cd0000000d')])
    stool, chair = chain(sitting, [(f'PC{tag}StoolSitting', G, [ctda(F_MARKER, 15)], '870000cd0000000c'),
                                   (f'PC{tag}ChairSitting', G, [], '070000cd00000000')])
    s_down, s_up, s_idle = chain(stool, [(f'PC{tag}SitDownStool', G, [ctda(F_SITTING, 2)], '840000cd00000016'),
                                         (f'PC{tag}StandUpStool', G, [ctda(F_SITTING, 4)], '940000cd00000015'),
                                         (f'PC{tag}DefaultSitIdleStool', G, [ctda(F_SITTING, 1)], '040000cd00000016')])
    chain(s_down, [(f'PC{tag}StoolEnter', stool_enter, [], '140000cd00000000')])
    chain(s_up, [(f'PC{tag}StoolExit', stool_exit, [], '140000cd00000000')])
    chain(s_idle, [(f'PC{tag}StoolDynamicIdle1stPerson', HUMAN + '1stP_StoolDynamicIdle.kf', IS_1ST_PERSON, '000000cd00000000'),
                   (f'PC{tag}StoolDynamicIdle', stool_loop, [], '000000cd00000000')])
    c_down, c_up, c_sp, c_idle = chain(chair, [
        (f'PC{tag}SitDown', G, [ctda(F_SITTING, 2)], '840000cd00000016'),
        (f'PC{tag}StandUp', G, [ctda(F_SITTING, 4)], '940000cd00000015'),
        (f'PC{tag}SittingChairIdles', G, [ctda(F_USEDITEM, 1, 1, 0x15), ctda(F_SITTING, 3)], '070000cd00000016'),
        (f'PC{tag}DefaultSitIdle', G, [ctda(F_SITTING, 1)], '040000cd00000016')])
    chain(c_down, [(f'PC{tag}Chair{s}Sit', chair_enter[s], [ctda(F_MARKER, m)] if m else [], '140000cd00000000') for s, m in SIDES])
    chain(c_up, [(f'PC{tag}Chair{s}Stand', chair_exit[s], [ctda(F_MARKER, m)] if m else [], '140000cd00000000') for s, m in SIDES])
    n = len(specials)
    chain(c_sp, [(f'PC{tag}SittingSpecial{chr(65 + i)}', f, [ctda(F_RANDOM, 100 * (i + 1) // n, 5)] if i < n - 1 else [], '070000cd00000000')
                 for i, f in enumerate(specials)])
    chain(c_idle, [(f'PC{tag}ChairDynamicIdle1stPerson', HUMAN + '1stP_ChairDynamicIdle.kf', IS_1ST_PERSON, '000000cd00000000'),
                   (f'PC{tag}ChairDynamicIdle', chair_loop, [], '000000cd00000000')])
    knocked, = chain(0, [(f'PC{tag}KnockedDownIdles', G, [ctda(F_HITLOC, -1), ctda(F_KNOCKED, 0, 1)], '040000cd0000000d')])
    chain(knocked, [(f'PC{tag}GetUpFaceUp', get_up[0], [ctda(F_FACEUP, 1)], '070000cd00000000'),
                    (f'PC{tag}GetUpFaceDown', get_up[1], [], '070000cd00000000')])
def human_set(F):
    return ({'Left': F + 'Chair_LeftEnter.kf', 'Right': F + 'Chair_RightEnter.kf', 'Back': F + 'Chair_BackEnter.kf', 'Front': F + 'Chair_ForwardEnter.kf'},
            {'Left': F + 'Chair_LeftExit.kf', 'Right': F + 'Chair_RightExit.kf', 'Back': F + 'Chair_BackExit.kf', 'Front': F + 'Chair_ForwardExit.kf'},
            F + 'DynamicIdle_ChairSit.kf', F + 'StoolEnter.kf', F + 'StoolExit.kf', F + 'DynamicIdle_SitStool.kf',
            [F + 'SitChairRelaxA.kf', F + 'SitChairRelaxB.kf', F + 'SitChairRelaxC.kf'])
for tag, folder, own in (('Swampfolk', 'Swampfolk', HF23 + 'IdleAnims\\'), ('Hillfolk', 'Hillfolk', HF1 + 'IdleAnims\\'), ('Trog', 'Trog', TROG + 'IdleAnims\\')):
    F = f'PlayableCreatures\\{folder}\\IdleAnims'
    creature_idles(tag, F, *human_set(F + '\\'), (own + 'specialidle_getupfaceup.kf', own + 'specialidle_getupfacedown.kf'))

# Capital Wasteland super mutants (TTW: creatures\\smspinebreakerdc = FNV's smspinebreaker skeleton, identical
# bones / hierarchy / bind - verified). They use the finished Playable Creatures Super Mutant set (skeleton
# folder PlayableCreatures\\SuperMutant and its idle tree in PlayableCreatures_SuperMutants.esp); each FO3 armor mesh is a whole body.
# One race per FO3 rank (all scale 1.0). New ids follow everything above.
DC = 'Creatures\\SMSpineBreakerDC\\'
SMDESC = 'Super mutants of the Capital Wasteland: FEV giants out of Vault 87. Immune to radiation. Playable Creatures (TTW).'
# Yes: Fallout3.esm's smspinebreakerdc\\smspinebreakerbare.nif (each FO3 super mutant mesh is a whole
# body). The Capital race gets the bare body; the armored bodies are wearable armor (UpperBody, below). Brute / Master
# races stay (old saves) but leave the race menu (ini ShowInRaceMenu=0).
for edid, full, body in (('PCSuperMutantDCRace', 'Super Mutant (Capital)', DC + 'SMSpineBreakerBare.NIF'),
                         ('PCSuperMutantBruteDCRace', 'Super Mutant Brute (Capital)', DC + 'SMSpineBreakerHeavy.NIF'),
                         ('PCSuperMutantMasterDCRace', 'Super Mutant Master (Capital)', DC + 'SMCaptain.NIF')):
    rid = nid(); race_ids[edid] = rid; races.append(make_race(rid, edid, full, SMDESC, body))
    base = edid[:-4]
    npcs += [preset(nid(), base + 'PresetMale', False, rid), preset(nid(), base + 'PresetFemale', True, rid)]

# race abilities + child races (race_extras.py; see build_esp.py). Swampfolk: Point Lookout's swampfolk carry
# RadImmunity (every variant); Capital super mutants: RadImmunity + SuperMutantDT (FalloutNV 12B895). Trogs: none.
import race_extras as RX
spels = []
SWAMP_ABIL = nid(); spels.append(RX.ability(SWAMP_ABIL, 'PCSwampfolkPhysiology', 'Swampfolk Physiology', RX.RAD_IMMUNITY))
SMDC_ABIL = nid(); spels.append(RX.ability(SMDC_ABIL, 'PCSuperMutantDCPhysiology', 'Super Mutant Physiology',
                                           RX.RAD_IMMUNITY + RX.effects(SRC.byfid[0x12B895])))
race_spells = {e: [SWAMP_ABIL] for e in race_ids if e.startswith('PCSwampfolk')}
race_spells.update({e: [SMDC_ABIL] for e in race_ids if e.startswith('PCSuperMutant')})
races, child_races, CHILD_IDS = RX.add_extras(races, race_spells, nid)
races += child_races
for e, c in CHILD_IDS.items(): print('  child race', e, '%06X' % (c & 0xFFFFFF))

# the Capital super mutants' armored bodies as wearable armor: whole-body meshes in UpperBody (the race's bare body
# is hidden while worn); given at race-menu close, drawn despite ArmorVisuals=0 (ini GiveItems / ShowForms). Ids follow.
armors = []
for edid, name, model, val, hp, wt, dt, heavy in (
        ('PCSuperMutantDCLightArmor', 'Super Mutant Light Armor (Capital)', 'SMSpineBreakerLight.NIF', 100, 150, 15.0, 6, False),
        ('PCSuperMutantDCMediumArmor', 'Super Mutant Medium Armor (Capital)', 'SMSpineBreakerMedium.NIF', 200, 250, 25.0, 10, False),
        ('PCSuperMutantDCHeavyArmor', 'Super Mutant Heavy Armor (Capital)', 'SMSpineBreakerHeavy.NIF', 300, 350, 35.0, 14, True),
        ('PCSuperMutantDCMasterArmor', 'Super Mutant Master Armor (Capital)', 'SMCaptain.NIF', 400, 450, 40.0, 18, True)):
    fid = nid(); armors.append(RX.armor(SRC, fid, edid, name, DC + model, 0x04, val, hp, wt, dt, heavy))
    print('  armor %-28s %06X' % (edid, fid & 0xFFFFFF))
# Mirelurks (Fallout 3: Creatures\\Mirelurk\\Skeleton.nif - CrMirelurk1 "Mirelurk" hatchling.nif at base scale 0.75,
# CrMirelurk2 "Mirelurk Hunter" mirelurk.nif, MS05NukaColaMireLurk1 / 2 "Nukalurk" mirelurknukacola.nif; the meshes
# are in New Vegas' archives, their textures only in TTW's Fallout3 - Textures.bsa). Skeleton / animations in
# PlayableCreatures\\Mirelurk (anim/creatures/mirelurk.py + assemble_mirelurk.py): melee only (claw attacks, melee
# weapons unseen). Physiology = their water breathing (MirklurkWaterBreathing 05876C) + TTW's MirelurkDT (DT +5; its
# effects copied, TaleOfTwoWastelands.esm is no master); the Mirelurk's race height 0.75 also raises SpeedMult by
# 1/height (a race height below 1 slows the player's root motion twice, see build_esp.py robot_race). The Nukalurk's
# radiation attack (FalloutNV NukalurkAttack 09ADE8 "Rad Poisoning") is its unarmed effect via the ini
# (UnarmedEffect=). Furniture / get-up idle tree under PlayableCreatures\\Mirelurk\\IdleAnims. New ids follow everything above.
MLK = 'Creatures\\Mirelurk\\'
MLDESC = 'Mirelurks: giant mutated crabs of the Capital Wasteland\'s waters, armored in thick shells. Breathe underwater, DT +5. Playable Creatures (TTW).'
MIRELURK_SMALL_H = 0.75
_ml_effs = RX.effects(SRC.byfid[0x5876C]) + [('EFID', u32(0x1630EF)), ('EFIT', struct.pack('<IIIIi', 5, 0, 0, 0, 0x4C))]   # + MirelurkDT
ML_ABIL, ML_SMALL_ABIL = nid(), nid()
spels.append(RX.ability(ML_ABIL, 'PCMirelurkPhysiology', 'Mirelurk Physiology', _ml_effs))
spels.append(RX.ability(ML_SMALL_ABIL, 'PCMirelurkSmallPhysiology', 'Mirelurk Physiology', _ml_effs
                        + [('EFID', u32(0x31D7A)), ('EFIT', struct.pack('<IIIIi', int(round(100 / MIRELURK_SMALL_H - 100)), 0, 0, 0, 21))]))
_ml = []
for edid, full, body, h, ab in (('PCMirelurkRace', 'Mirelurk', 'hatchling.nif', MIRELURK_SMALL_H, ML_SMALL_ABIL),
                                ('PCMirelurkHunterRace', 'Mirelurk Hunter', 'mirelurk.nif', 1.0, ML_ABIL),
                                ('PCMirelurkNukalurkRace', 'Nukalurk', 'mirelurknukacola.nif', 1.0, ML_ABIL)):
    rid = nid(); race_ids[edid] = rid
    t, fl, _f, subs = RX.parse(make_race(rid, edid, full, MLDESC.replace('Mirelurks:', 'Nukalurks: Nuka-Cola Quantum-glowing mirelurks of the Nuka-Cola plant; their claws carry radiation.') if 'Nuka' in full else MLDESC, MLK + body))
    subs = [(k, (lambda d: (struct.pack_into('<ff', d, 16, h, h), bytes(d))[-1])(bytearray(v)) if k == 'DATA' else v) for k, v in subs]
    _ml.append((record('RACE', rid, subs, fl), edid, ab))
    npcs += [preset(nid(), edid[:-4] + 'PresetMale', False, rid), preset(nid(), edid[:-4] + 'PresetFemale', True, rid)]
_mla, _mlc, _mlids = RX.add_extras([r for r, _, _ in _ml], {e: [a] for _, e, a in _ml}, nid)
races += _mla + _mlc
for e, c in _mlids.items(): print('  child race', e, '%06X' % (c & 0xFFFFFF))
# body part data: MirelurkBodyPartData's Face part (Bip01 Head) has neither the IK data nor the headtracking flag (0x49) -
# the player's ragdoll sets up its head pose only from a part with both, its IK start node a ragdoll bone (diagnostic
# log: the lakelurk's part, flags 0x2F, reached the setup; the mirelurk's never did): PCMirelurkBodyPartData = it with
# the Face part's flags | 0x22 and its IK node Bip01 Head, a bone of its ragdoll (ini BodyPartData).
bptds = []
def _bptd(src_fid, edid, part, node):
    out = []; cur = None; done = False
    for k, v in SRC.byfid[src_fid].subs():
        if k == 'EDID': v = z(edid)
        elif k == 'BPTN': cur = v.rstrip(b'\0').decode('latin1') == part and not done
        elif k == 'BPNI' and cur: v = z(node)
        elif k == 'BPND' and cur: d = bytearray(v); d[4] |= 0x22; v = bytes(d); done = True      # IK data + headtracking
        out.append((k, v))
    assert done, edid
    fid = nid(); bptds.append(record('BPTD', fid, out)); return fid
MIRELURK_BPTD = _bptd(0x354E3, 'PCMirelurkBodyPartData', 'Face', 'Bip01 Head')
print('  mirelurk body part data %06X' % (MIRELURK_BPTD & 0xFFFFFF))
F = 'PlayableCreatures\\Mirelurk\\IdleAnims'
creature_idles('Mirelurk', F, *human_set(F + '\\'), (MLK + 'IdleAnims\\specialidle_getupfaceup.kf', MLK + 'IdleAnims\\specialidle_getupfacedown.kf'))

# The Capital super mutants' own skeleton folder PlayableCreatures\\SuperMutantDC (anim/assemble_smdc.py: the New Vegas set
# with Fallout 3's own animations where they differ) has its own idle tree: the New Vegas furniture set, Fallout 3's own
# get-ups (Creatures\\SMSpineBreakerDC\\IdleAnims). New ids follow everything above.
F = 'PlayableCreatures\\SuperMutantDC\\IdleAnims'
creature_idles('SuperMutantDC', F, *human_set(F + '\\'), (DC + 'IdleAnims\\specialidle_getupfaceup.kf', DC + 'IdleAnims\\specialidle_getupfacedown.kf'))

# The same head pose fix for The Pitt's trogs (DLCPittTrogBodyPartDataDC: Head flags 0x09, IK node = the skeleton file;
# tools/bptd_audit.py), copied from its own master, form ids moved to our master list (BPND debris / explosions / impact
# data sets, RAGA). Point Lookout's Tracker / Bruiser (DLC04Hillfolk1BodyPartData): head tracking off - its Head part
# without 'IK Data' / 'IK Data - Headtracking' (0x3B -> 0x19). Their ragdoll has no body on the head, and their neck
# juts forward: tracking on the neck (the only ragdoll bone it could use) tipped the head up. Ids after everything else.
BPND_FORMS = (12, 16, 32, 36, 68, 72)
def _bptd_from(path, src_fid, edid, part, node, clear=0):
    p = Plugin(path)
    pm = [v.rstrip(b'\0').decode('latin1') for k, v in p.recs[0].subs() if k == 'MAST']
    own = os.path.basename(path)
    lower = [m.lower() for m in MASTERS]
    def remap(f):
        if f == 0: return 0
        i = f >> 24; name = pm[i] if i < len(pm) else own
        return (lower.index(name.lower()) << 24) | (f & 0xFFFFFF)
    out = []; cur = None; done = False
    for k, v in p.byfid[(len(pm) << 24) | src_fid].subs():
        if k == 'EDID': v = z(edid)
        elif k == 'BPTN': cur = v.rstrip(b'\0').decode('latin1') == part and not done
        elif k == 'BPNI' and cur: v = z(node)
        elif k == 'RAGA': v = u32(remap(struct.unpack('<I', v)[0]))
        elif k == 'BPND':
            d = bytearray(v)
            for o in BPND_FORMS:
                if o + 4 <= len(d): struct.pack_into('<I', d, o, remap(struct.unpack_from('<I', d, o)[0]))
            if cur: d[4] = (d[4] & ~clear) if clear else (d[4] | 0x22); done = True
            v = bytes(d)
        out.append((k, v))
    assert done, edid
    fid = nid(); bptds.append(record('BPTD', fid, out)); return fid
if 'ThePitt.esm' in MASTERS:            # the TTW master list (build_plugins.py); a plain build has FalloutNV.esm only
    TROG_BPTD = _bptd_from('/home/claude/fnv/ttw/ThePitt.esm', 0x003CEA, 'PCTrogBodyPartData', 'Head', 'Bip01 Head')
    HILLFOLK_BPTD = _bptd_from('/home/claude/fnv/ttw/PointLookout.esm', 0x010C37, 'PCHillfolkBodyPartData', 'Head', 'Bip01 Head', clear=0x22)
    print('  body part data: trog %06X, hillfolk (tracker / bruiser, no head tracking) %06X' % (TROG_BPTD & 0xFFFFFF, HILLFOLK_BPTD & 0xFFFFFF))


# The player's action idles per skeleton folder (as build_esp.py act_idles): ActivateIdles > ActWaterSource /
# ActStimpakSource, StartCannibal; vanilla conditions / DATA; files from anim/act_idles.py. Ids after everything else.
def _vanilla_idle(fid):
    r = SRC.byfid[fid]
    return [v for k, v in r.subs() if k == 'CTDA'], dict(r.subs())['DATA'].hex()
_AC = {f: _vanilla_idle(f) for f in (0x3BDC, 0x221B4, 0x23035, 0x7D409)}
def act_idles(tag, folder):
    act, = chain(0, [(f'PC{tag}ActivateIdles', folder, *_AC[0x3BDC])])
    water, stim = chain(act, [(f'PC{tag}ActWaterSource', folder, *_AC[0x221B4]), (f'PC{tag}ActStimpakSource', folder, *_AC[0x23035])])
    chain(water, [(f'PC{tag}ActWater', folder + '\\ActWaterSource.kf', [], '070000cd0000')])
    chain(stim, [(f'PC{tag}ActStimpak', folder + '\\Stimpak.kf', [], '070000cd0000')])
    chain(0, [(f'PC{tag}StartCannibal', folder + '\\Cannibal.kf', *_AC[0x7D409])])
for _tag, _f in (('Swampfolk', 'Swampfolk'), ('Hillfolk', 'Hillfolk'), ('Trog', 'Trog'), ('Mirelurk', 'Mirelurk'), ('SuperMutantDC', 'SuperMutantDC')):
    act_idles(_tag, 'PlayableCreatures\\%s\\IdleAnims' % _f)

# The Mister Sandman kill (StartMisterSandman: FurnitureIdles > Sleeping > SandMan / SandManFloor, by the victim's
# bed marker 1 / 2 / 3 / 4; vanilla conditions / DATA): a Sleeping group under the race's FurnitureIdles root (after its
# Sitting group), or a FurnitureIdles root with only Sleeping for races without furniture. Files from anim/act_idles.py.
_SM = {f: _vanilla_idle(f) for f in (0x3AEF, 0x3AFF, 0x79F16, 0x7C6CD, 0x79F17, 0x79F18, 0x7C6CE, 0x7C6CF)}
def sandman_idles(tag, folder):
    root = IDLE_BY_EDID.get(f'PC{tag}FurnitureIdles'); prev = IDLE_BY_EDID.get(f'PC{tag}Sitting', 0)
    if root is None: root, = chain(0, [(f'PC{tag}FurnitureIdles', folder, *_SM[0x3AEF])]); prev = 0
    sleeping = idle(f'PC{tag}Sleeping', folder, _SM[0x3AFF][0], root, _SM[0x3AFF][1], prev)
    bed, floor = chain(sleeping, [(f'PC{tag}SandMan', folder, *_SM[0x79F16]), (f'PC{tag}SandManFloor', folder, *_SM[0x7C6CD])])
    chain(bed, [(f'PC{tag}SandManBedLeft', folder + '\\SandManBedLeft.kf', *_SM[0x79F17]),
                (f'PC{tag}SandManBedRight', folder + '\\SandManBedRight.kf', *_SM[0x79F18])])
    chain(floor, [(f'PC{tag}SandManFlrLeft', folder + '\\SandManFlrLeft.kf', *_SM[0x7C6CE]),
                  (f'PC{tag}SandManFlrRight', folder + '\\SandManFlrRight.kf', *_SM[0x7C6CF])])
for _tag, _f in (('Swampfolk', 'Swampfolk'), ('Hillfolk', 'Hillfolk'), ('Trog', 'Trog'), ('Mirelurk', 'Mirelurk'), ('SuperMutantDC', 'SuperMutantDC')):
    sandman_idles(_tag, 'PlayableCreatures\\%s\\IdleAnims' % _f)

# Tranquility Lane / Vault 112 pods (FurnitureIdles > Sitting > POD, marker 16; vanilla conditions / DATA): a Pod group
# under the race's Sitting group, evaluated before ChairSitting (that fallback has no condition, so its 'previous
# sibling' link is moved to the pod). Files from anim/pod.py; the Ghost (human skeleton) uses the vanilla files.
def set_prev(fid, prev):
    for i, r in enumerate(idles):
        if struct.unpack_from('<I', r, 12)[0] == fid:
            j = r.index(b'ANAM\x08\x00'); idles[i] = r[:j + 10] + struct.pack('<I', prev) + r[j + 14:]; return
    raise KeyError(hex(fid))
_POD = {f: _vanilla_idle(f) for f in (0x926C2, 0x926C3, 0x93A64, 0x93A65, 0x926C4, 0x926C5)}
def pod_idles(tag, folder, files=None):
    f = files or {k: folder + '\\' + k for k in ('PodEnter.kf', 'PodExit.kf', 'PodIdle.kf')}
    sitting = IDLE_BY_EDID[f'PC{tag}Sitting']; stool = IDLE_BY_EDID[f'PC{tag}StoolSitting']
    pod = idle(f'PC{tag}Pod', folder, _POD[0x926C2][0], sitting, _POD[0x926C2][1], stool)
    set_prev(IDLE_BY_EDID[f'PC{tag}ChairSitting'], pod)
    sit, = chain(pod, [(f'PC{tag}PodSitIdle', folder, *_POD[0x926C3])])
    chain(sit, [(f'PC{tag}PodSitIdle1stPerson', HUMAN + '1stP_PodDynamicIdle.kf', *_POD[0x93A64]),
                (f'PC{tag}PodSitIdle3rdPerson', f['PodIdle.kf'], *_POD[0x93A65])])
    idle(f'PC{tag}PodEnter', f['PodEnter.kf'], _POD[0x926C4][0], pod, _POD[0x926C4][1], sit)
    idle(f'PC{tag}PodExit', f['PodExit.kf'], _POD[0x926C5][0], pod, _POD[0x926C5][1], IDLE_BY_EDID[f'PC{tag}PodEnter'])
for _tag, _f in (('Swampfolk', 'Swampfolk'), ('Hillfolk', 'Hillfolk'), ('SuperMutantDC', 'SuperMutantDC')):
    pod_idles(_tag, 'PlayableCreatures\\%s\\IdleAnims' % _f)

# Capital super mutant taunts (Core TauntIdles= / TauntSound=, as build_esp.py's PCSuperMutantTaunt*): Fallout 3's super
# mutant intimidation idles (creatures\\smspinebreakerdc\\idleanims in TTW), the ones without Weapon keys; section Special Idle
# (as the vanilla records; Whole Body cleared the weapon-ready state) + no attacking; under a root that never passes
# (PCSuperMutantDCTauntIdles). Their voices, played by Core (anim/sm_taunt.py): combat barks and the gloat after a kill. SNDD as build_esp.py's voice sounds.
# New ids after everything else (the root after the ids the taunts / voice already had).
SMDC_TAUNTS = [nid() for _ in range(3)]
SMDC_TAUNT_SOUN = nid()
_sndd = bytearray(bytes.fromhex('3c0800000010000056050000640032001400050000005000800000000000000000000000')); struct.pack_into('<h', _sndd, 8, 500)
souns = [record('SOUN', SMDC_TAUNT_SOUN, [('EDID', z('PCSuperMutantDCTauntVox')), ('OBND', bytes(12)),
    ('FNAM', z('fx\\npc\\playablecreatures\\supermutantdc\\taunt\\')), ('RNAM', b'\0'), ('SNDD', bytes(_sndd))])]
SMDC_TAUNT_ROOT = nid()
idles.append(record('IDLE', SMDC_TAUNT_ROOT, [('EDID', z('PCSuperMutantDCTauntIdles')), ('MODL', z('Creatures\\SMSpineBreakerDC\\IdleAnims')),
    ('CTDA', ctda(F_RANDOM, 0, 4)), ('ANAM', struct.pack('<II', 0, 0)), ('DATA', bytes.fromhex('0700000000000000'))]))
_prev = 0
for _i, (_fid, _fn) in enumerate(zip(SMDC_TAUNTS, ('SpecialIdle_2HAIntimidate.kf', 'SpecialIdle_2HAIntimidate2.kf', 'SpecialIdle_2HAIntimidate4.kf')), 1):
    idles.append(record('IDLE', _fid, [('EDID', z('PCSuperMutantDCTaunt%d' % _i)), ('MODL', z('Creatures\\SMSpineBreakerDC\\IdleAnims\\' + _fn)),
        ('ANAM', struct.pack('<II', SMDC_TAUNT_ROOT, _prev)), ('DATA', bytes.fromhex('0700000000000100'))]))
    _prev = _fid
SMDC_TAUNTKILL_SOUN = nid()                     # TauntKillSound=: the gloat for the first taunt soon after a kill
souns.append(record('SOUN', SMDC_TAUNTKILL_SOUN, [('EDID', z('PCSuperMutantDCTauntKillVox')), ('OBND', bytes(12)),
    ('FNAM', z('fx\\npc\\playablecreatures\\supermutantdc\\tauntkill\\')), ('RNAM', b'\0'), ('SNDD', bytes(_sndd))]))
print('  capital super mutant kill voice %06X' % (SMDC_TAUNTKILL_SOUN & 0xFFFFFF))
print('  capital super mutant taunts', ' '.join('%06X' % (f & 0xFFFFFF) for f in SMDC_TAUNTS), 'voice %06X root %06X' % (SMDC_TAUNT_SOUN & 0xFFFFFF, SMDC_TAUNT_ROOT & 0xFFFFFF))

groups = [group('HAIR', [hair]), group('EYES', [eyes]), group('RACE', races), group('SOUN', souns), group('SPEL', spels), group('ARMO', armors), group('NPC_', npcs), group('IDLE', idles), group('BPTD', bptds)]
nrec = 2 + len(races) + len(souns) + len(spels) + len(armors) + len(npcs) + len(idles) + len(bptds) + len(groups)
tes4 = record('TES4', 0, [
    ('HEDR', struct.pack('<fII', 1.34, nrec, _next[0])), ('CNAM', z('i3ncore')),
    ('SNAM', z('Playable Creatures (TTW add-on): Swampfolk (Brawler, Scrapper, Creeper, Tracker, Bruiser), Trogs, Capital Wasteland super mutants (Super Mutant, Brute, Master) as playable races; idle trees. Needs Tale of Two Wastelands and PlayableCreatures.dll.')),
    *[x for m in MASTERS for x in (('MAST', z(m)), ('DATA', struct.pack('<Q', 0)))]])
open(OUT, 'wb').write(tes4 + b''.join(groups))
print('wrote', OUT, len(races), 'races', len(npcs), 'presets', len(idles), 'idles, next id %03X' % _next[0])
for edid, rid in race_ids.items(): print(f'  {edid:26s} {rid & 0xFFFFFF:06X}')
