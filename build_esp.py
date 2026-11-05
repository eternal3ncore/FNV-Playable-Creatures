"""Builds the New Vegas creature races (split into family plugins by build_plugins.py): Zetan race (phase 1) + Ghost People races (hooded / unhooded) + creature sound set
+ Zetan voice type (its combat dialogue lives in PlayableCreaturesVoices.esp, build_voices.py)
+ per-skeleton idle trees (Ghost get-ups = Dead Money revive + emerge vocal): furniture sit / stand / seated idles and knock-down get-ups for each creature skeleton.
+ SPEL PCRadImmunityAbility 0x854: ability, +100 Rad Resistance, given by PlayableCreatures.dll while the player is a
  RadImmune race (FNV RACE records have no spell list).
+ Feral Ghoul / Glowing One (Ghoul skeleton) and Super Mutant / Nightkin (SMSpineBreaker skeleton) races 0x855-0x858,
  presets 0x859-0x860, SOUN PCSuperMutantAttackVox 0x861, their idle trees from 0x862.
+ SPEL PCGhostImmunityAbility 0x8A0: Ghost People's immunities (+100 Rad Resistance, +100 Poison Resistance;
  Ghostification's hazmat suit enchantment values).
+ Ghost moves (Ghostification's ghost features, triggered by PlayableCreatures.dll from the jump key, no hotkey
  item): PCGhostMoveSpell 0x8A3 (hop: Turbo + crit 1 s + SetGhost 1 s via PCGhostMoveEffect 0x8A2 / its script 0x8A1),
  PCGhostScanSpell 0x8A4 (+3 Perception 60 s, AP regeneration 10 s), PCGhostSearchSpell 0x8A7 (PCGhostSearchEffect
  0x8A6 / script 0x8A5: loot after 5 s). Scripts / effects are copies of the compiled GhostTrait.esp records (the
  GhostTrait mod), re-pointed to our ids. Ghost sight: override of FalloutNV's PipBoyLight ability - the lamp effect is
  conditioned to non-ghost races, Dead Money's own GhostSightBaseEffect (ghost-sight imagespace + night eye) to the two
  Ghost races. DeadMoney.esm becomes a master.
+ PCGhostMoveSpell: Turbo and crit effects conditioned IsInCombat == 1 (Ghostification's conditions).
+ IDLE PCGhostMoveIdles (root, never passes) / PCGhostIdleLooking / PCGhostTrashPick: the scan / search idles with
  Ghostification's whole-body section 0x14 + no-attacking flag (0x8A8-0x8AA).
+ scan move removed: PCGhostScanSpell 0x8A4 and PCGhostIdleLooking 0x8A9 dropped.
+ ANIO PCGhostTrashPickSpear 0x8AB: Dead Money's trash-pick spear, tied to PCGhostTrashPick.
+ Tunneler (Lonesome Road): RACE PCTunnelerRace, presets, idle tree PCTunneler* (ids from 0x8AC).
+ Spore Carrier: RACE PCSporeCarrierRace + presets (ids from 0x8CE), Tunneler skeleton folder / idle tree.

Idle trees: the engine picks an actor's idle tree by its *skeleton folder* (IdleManager key "<skeleton folder>\\IdleAnims",
the folder of every root IDLE's MODL). Humans use Characters\\_Male\\IdleAnims, the Zeta aliens DLC05\\Creatures\\Alien\\
IdleAnims, and so on. A creature-race player has the skeleton PlayableCreatures\\<Race>\\Skeleton.nif, so it needs its own
roots under PlayableCreatures\\<Race>\\IdleAnims - without them the sit request finds no entry animation and the engine
leaves the player locked in "want to sit" (the chair freeze). Structure and conditions mirror the vanilla FurnitureIdles /
KnockedDownIdles trees; every sit/stand group ends with an unconditioned entry, so any sit marker finds an animation."""
import struct, sys
sys.path.insert(0, '/home/claude/fnv')
from esm import Plugin, zstr

SRC = Plugin('/home/claude/fnv/FalloutNV.esm')
OUT = sys.argv[1] if len(sys.argv) > 1 else '/home/claude/fnv/build/PlayableCreatures.esp'

# the master list is a parameter: PC_MASTERS (comma separated); build_plugins.py passes the New Vegas family plugins'
# list, and our own forms are index len(masters). Local ids are kept by the family plugins, so the ini and the DLL
# refer to <family plugin>|<local id>.
import os
MASTERS = os.environ.get('PC_MASTERS', 'FalloutNV.esm,DeadMoney.esm').split(',')
assert MASTERS[0] == 'FalloutNV.esm' and MASTERS[1] == 'DeadMoney.esm', MASTERS
MOD = len(MASTERS) << 24  # our own forms
DM = 0x01000000           # DeadMoney.esm forms
FID = dict(RACE=MOD | 0x800, HAIR=MOD | 0x801, EYES=MOD | 0x802, NPCM=MOD | 0x803, NPCF=MOD | 0x804)

EMPTY = 'PlayableCreatures\\Zetan\\Empty.nif'
ZETAN_BODY = 'DLC05\\Creatures\\Alien\\DLC05Alien1.NIF'
GD = 'NVDLC01\\Creatures\\Ghosts\\'
GHOST_HANDS = (GD + 'NVDLC01Glovel.nif', GD + 'NVDLC01Glover.nif')
GHOST_DESC = 'Ghost People of the Sierra Madre: hazmat-suited, near-unkillable scavengers. Playable Creatures.'
# (race fid, EDID, name, body, preset male fid, preset female fid)
GHOSTS = [(MOD | 0x805, 'PCGhostRace', 'Ghost Person', GD + 'NVDLC01Ghost.NIF', MOD | 0x807, MOD | 0x808),
          (MOD | 0x806, 'PCGhostUnhoodedRace', 'Ghost Person (Unhooded)', GD + 'NVDLC01Ghost_hoodless.NIF', MOD | 0x809, MOD | 0x80A)]

def z(s): return s.encode('latin1') + b'\0'
def sub(t, data):
    if len(data) > 0xFFFF:
        return b'XXXX' + struct.pack('<HI', 4, len(data)) + t.encode() + struct.pack('<H', 0) + data
    return t.encode() + struct.pack('<H', len(data)) + data
def record(t, fid, subs, flags=0):
    body = b''.join(sub(k, v) for k, v in subs)
    return t.encode() + struct.pack('<IIIIHH', len(body), flags, fid, 0, 15, 0) + body
def group(label, recs):
    body = b''.join(recs)
    return b'GRUP' + struct.pack('<I4sIIHH', 24 + len(body), label.encode(), 0, 0, 0, 0) + body
u32 = lambda v: struct.pack('<I', v)

# ---------------- HAIR (invisible) / EYES (shared by all creature races) ----------------
hair = record('HAIR', FID['HAIR'], [
    ('EDID', z('PCZetanNoHair')), ('FULL', z('None')), ('MODL', z(EMPTY)),
    ('ICON', z('Characters\\Hair\\HairWavy.dds')), ('DATA', bytes([0x01]))])
eyes = record('EYES', FID['EYES'], [
    ('EDID', z('PCZetanEyes')), ('FULL', z('Zetan')), ('ICON', z('Characters\\Eyes\\EyeDefault.dds')), ('DATA', bytes([0x01]))])

# ---------------- RACE (from Caucasian) ----------------
cauc = SRC.byfid[0x19]
def make_race(fid, edid, full, desc, body, hands=(None, None), voice=None, body_f=None):
    """body_f: the female body model when it differs (deathclaw alpha male / mother)"""
    out = []; section = None; female = False
    subs = cauc.subs(); i = 0
    while i < len(subs):
        k, v = subs[i]
        if k == 'EDID': out.append((k, z(edid)))
        elif k == 'FULL': out.append((k, z(full)))
        elif k == 'DESC': out.append((k, z(desc)))
        elif k == 'DATA':
            d = bytearray(v)
            d[0:14] = bytes([0xFF, 0x00] * 7)                 # no skill boosts
            struct.pack_into('<ffff', d, 16, 1.0, 1.0, 1.0, 1.0)
            struct.pack_into('<I', d, 32, 0x1)                 # playable
            out.append((k, bytes(d)))
        elif k in ('ONAM', 'YNAM'): pass                       # no older/younger variants
        elif k == 'DNAM': out.append((k, u32(FID['HAIR']) * 2))
        elif k == 'NAM0': section = 'head'; out.append((k, v))
        elif k == 'NAM1': section = 'body'; out.append((k, v))
        elif k in ('MNAM', 'FNAM') and section: female = k == 'FNAM'; out.append((k, v))
        elif k == 'INDX' and section == 'body':
            idx = struct.unpack('<I', v)[0]
            j = i + 1; part = []
            while j < len(subs) and subs[j][0] in ('ICON', 'MODL', 'MODT', 'MODD', 'MICO'):
                part.append(subs[j]); j += 1
            if idx == 3:            # body FaceGen tint (.egt) - dropped for creature bodies
                i = j; continue
            out.append((k, v))
            for pk, pv in part:
                if pk == 'MODL':
                    m = (body_f if female and body_f else body) if idx == 0 else (hands[idx - 1] if idx in (1, 2) and hands[idx - 1] else EMPTY)
                    out.append(('MODL', z(m)))
                elif pk in ('MODT', 'MODD'): pass
                else: out.append((pk, pv))
            i = j; continue
        elif k == 'INDX' and section == 'head':
            out.append((k, v))
            j = i + 1
            while j < len(subs) and subs[j][0] in ('ICON', 'MODL', 'MODT', 'MODD', 'MICO'):
                pk, pv = subs[j]
                if pk == 'MODL': out.append(('MODL', z(EMPTY)))
                elif pk in ('MODT', 'MODD'): pass
                else: out.append((pk, pv))
                j += 1
            i = j; continue
        elif k == 'HNAM': out.append((k, u32(FID['HAIR'])))
        elif k == 'VTCK' and voice: out.append((k, u32(voice) * 2))        # default voice (male, female)
        elif k == 'ENAM': section = None; out.append((k, u32(FID['EYES'])))
        else: out.append((k, v))
        i += 1
    return record('RACE', fid, out)

# ---------------- chargen preset NPCs ----------------
def preset(fid, edid, female, race, voice=None):
    tpl = SRC.byfid[0x568F7]
    o = []
    for k, v in tpl.subs():
        if k == 'EDID': o.append((k, z(edid)))
        elif k == 'FULL': o.append((k, z(edid)))
        elif k == 'ACBS':
            a = bytearray(v); fl = struct.unpack_from('<I', a, 0)[0]
            fl = (fl & ~0x1) | 0x4 | (0x1 if female else 0)       # chargen face preset (+female)
            struct.pack_into('<I', a, 0, fl); o.append((k, bytes(a)))
        elif k == 'VTCK': o.append((k, u32(voice or (0x2E if female else 0x2D))))
        elif k == 'RNAM': o.append((k, u32(race)))
        elif k == 'PNAM': pass                                     # no human eyebrow head part
        elif k == 'HNAM': o.append((k, u32(FID['HAIR'])))
        elif k == 'ENAM': o.append((k, u32(FID['EYES'])))
        else: o.append((k, v))
    return record('NPC_', fid, o)

ZETAN_VOICE = MOD | 0x816
vtyp = [record('VTYP', ZETAN_VOICE, [('EDID', z('PCZetanVoice')), ('DNAM', bytes([0]))])]
races = [make_race(FID['RACE'], 'PCZetanRace', 'Zetan', 'Zetan: grey-skinned abductors from Mothership Zeta. Playable Creatures phase 1.', ZETAN_BODY, voice=ZETAN_VOICE)]
npcs = [preset(FID['NPCM'], 'PCZetanPresetMale', False, FID['RACE'], ZETAN_VOICE), preset(FID['NPCF'], 'PCZetanPresetFemale', True, FID['RACE'], ZETAN_VOICE)]
for rfid, edid, full, body, pm, pf in GHOSTS:
    races.append(make_race(rfid, edid, full, GHOST_DESC, body, GHOST_HANDS))
    base = edid[:-4]
    npcs += [preset(pm, base + 'PresetMale', False, rfid), preset(pf, base + 'PresetFemale', True, rfid)]
# Feral Ghouls and Super Mutants: the whole creature is one body model (head included); a Super Mutant's
# outfit (loincloth / boots / trousers) is a second model, carried in the race's left-hand slot.
SM = 'Creatures\\SMSpineBreaker\\'; GH = 'Creatures\\Ghoul\\'
NEW_RACES = [
    (MOD | 0x855, 'PCFeralGhoulRace', 'Feral Ghoul', GH + 'FeralGhoul.NIF', (None, None), MOD | 0x859, MOD | 0x85A,
     'Feral ghouls: radiation-ravaged ghouls of the Mojave, fast and relentless. Immune to radiation. Playable Creatures.'),
    (MOD | 0x856, 'PCGlowingOneRace', 'Glowing One', GH + 'GlowingOne.NIF', (None, None), MOD | 0x85B, MOD | 0x85C,
     'Glowing Ones: feral ghouls saturated with radiation. Immune to radiation. Playable Creatures.'),
    (MOD | 0x857, 'PCSuperMutantRace', 'Super Mutant', SM + 'NV_SM_v2_base.NIF', (SM + 'smspinebreakerbare.nif', None), MOD | 0x85D, MOD | 0x85E,
     'Super Mutants: FEV-made giants of the Master\'s Army. Immune to radiation. Playable Creatures.'),
    (MOD | 0x858, 'PCNightkinRace', 'Nightkin', SM + 'NV_Night_base.NIF', (SM + 'nightkinbare.nif', None), MOD | 0x85F, MOD | 0x860,
     'Nightkin: the Master\'s elite super mutants, worn down by years of Stealth Boys. Immune to radiation. Playable Creatures.'),
]
for rfid, edid, full, body, hands, pm, pf, desc in NEW_RACES:
    races.append(make_race(rfid, edid, full, desc, body, hands))
    base = edid[:-4]
    npcs += [preset(pm, base + 'PresetMale', False, rfid), preset(pf, base + 'PresetFemale', True, rfid)]

# ---------------- SOUN: creature voice set ----------------
# SNDD = 36 bytes: min/max attenuation distance, freq adj, pad, flags, static attenuation (1/100 dB), stop/start,
# attenuation curve, reverb, priority, loop points. Base bytes copied from Dead Money's NPCGhostSpearStabVox
# (creature vox: min 60, max 8, flags 0x1000 mute-when-submerged); per record we set flags / static attenuation.
SNDD_VOX = bytes.fromhex('3c0800000010000056050000640032001400050000005000800000000000000000000000')
def soun(fid, edid, path, static_db=None, flags=None, minmax=None):
    d = bytearray(SNDD_VOX)
    if minmax: d[0], d[1] = minmax
    if flags is not None: struct.pack_into('<I', d, 4, flags)
    if static_db is not None: struct.pack_into('<h', d, 8, int(round(static_db * 100)))
    return record('SOUN', fid, [('EDID', z(edid)), ('OBND', bytes(12)), ('FNAM', z(path)), ('RNAM', b'\0'), ('SNDD', bytes(d))])
PC = 'fx\\npc\\playablecreatures\\'
GP = 'fx\\npc\\ghostpeople\\'                      # Dead Money - Sounds.bsa
SOUNDS = [
    # anim text-key sounds: folders padded with silent files = play chance (the engine picks one file at random)
    (0x80B, 'PCZetanAttackVox', PC + 'zetan\\bark_chance\\', 5.0, None, None),
    (0x80F, 'PCGhostAttackVox', PC + 'ghost\\bark_chance\\', 13.66, None, None),
    (0x810, 'PCGhostThrowVox', PC + 'ghost\\throw_chance\\', 7.93, None, (30, 12)),
    (0x811, 'PCGhostJumpVox', PC + 'ghost\\jump_chance\\', 0.0, None, (30, 12)),
    # played by PlayableCreatures.dll on hit / death / player hits with a ranged weapon (chance + cooldown in the ini)
    (0x80C, 'PCZetanRangedVox', PC + 'zetan\\bark\\', 5.0, None, None),
    (0x80D, 'PCZetanHitVox', PC + 'zetan\\hit\\', 5.0, None, None),
    (0x80E, 'PCZetanDeathVox', PC + 'zetan\\death\\', 3.0, None, (65, 24)),
    (0x812, 'PCGhostRangedVox', GP + 'spear_vox\\', 13.66, None, None),
    (0x813, 'PCGhostHitVox', GP + 'jumpvox\\', 0.0, None, (30, 12)),
    (0x814, 'PCGhostDeathVox', GP + 'death\\', 13.66, None, (65, 24)),
    # Ghost People's native ConsciousLoop wheeze (their CREA sound), looped on the player by the DLL
    (0x815, 'PCGhostBreathLp', GP + 'conscious\\cr_ghostpeople_conscious_lp.wav', 18.0, 0x3090, (55, 22)),
    # Super Mutant / Nightkin melee + throw vocal (anim key): the low-int super mutant Attack / PowerAttack barks,
    # 14 lines padded with 21 silent files = 40 % chance
    (0x861, 'PCSuperMutantAttackVox', PC + 'supermutant\\bark_chance\\', 5.0, None, None),
]
souns = [soun(MOD | f, e, p, sdb, fl, mm) for f, e, p, sdb, fl, mm in sorted(SOUNDS)]


# ---------------- IDLE: per-skeleton idle trees ----------------
# CTDA: type byte = operator << 5 | OR flag; operators 0 ==, 1 !=, 2 >, 3 >=, 4 <, 5 <=
F_SITTING, F_SLEEPING, F_MARKER, F_ISID, F_PC1ST, F_RANDOM, F_FACEUP, F_KNOCKED, F_HITLOC, F_USEDITEM = 159, 49, 160, 72, 392, 77, 106, 107, 391, 247
def ctda(func, comp, op=0, p1=0, OR=False):
    return struct.pack('<B3sfHHIIII', (op << 5) | (1 if OR else 0), b'\0\0\0', float(comp), func, 0, p1, 0, 0, 0)
IS_1ST_PERSON = [ctda(F_ISID, 1, 0, 0x7), ctda(F_PC1ST, 1)]             # GetIsID Player == 1 AND IsPC1stPerson == 1
HUMAN = 'Characters\\_Male\\IdleAnims\\'
ALIEN = 'DLC05\\Creatures\\Alien\\IdleAnims\\'
GHOSTD = 'NVDLC01\\Creatures\\Ghosts\\IdleAnims\\'
_idle_next = [0x817]
RAD_ABILITY = MOD | 0x854
idles = []
IDLE_BY_EDID = {}
def idle(edid, modl, conds, parent, data, prev=0):
    fid = MOD | _idle_next[0]; _idle_next[0] += 1; IDLE_BY_EDID[edid] = fid
    subs = [('EDID', z(edid)), ('MODL', z(modl))] + [('CTDA', c) for c in conds] + \
           [('ANAM', struct.pack('<II', parent, prev)), ('DATA', bytes.fromhex(data))]
    idles.append(record('IDLE', fid, subs))
    return fid
def chain(parent, items):
    """items: (edid, MODL, conds, DATA) in evaluation order; siblings linked through ANAM 'previous sibling'"""
    prev = 0; out = []
    for edid, modl, conds, data in items:
        prev = idle(edid, modl, conds, parent, data, prev); out.append(prev)
    return out
SIDES = (('Left', 11), ('Right', 12), ('Back', 13), ('Front', None))    # GetFurnitureMarkerID of the entry side

def creature_idles(tag, folder, chair_enter, chair_exit, chair_loop, stool_enter, stool_exit, stool_loop, specials, get_up,
                   root=None, root_prev=0):
    """All paths are full MODL paths. folder = the creature's skeleton folder + IdleAnims (the tree key).
    root: an existing FurnitureIdles root to put the Sitting group under (after root_prev)"""
    G = folder                       # group nodes carry the folder as MODL, like vanilla
    if root is None:
        root, = chain(0, [(f'PC{tag}FurnitureIdles', G, [ctda(F_SITTING, 0, 2, OR=True), ctda(F_SLEEPING, 0, 2)], '840000cd0000003c')])
    sitting = idle(f'PC{tag}Sitting', G, [ctda(F_SITTING, 0, 2)], root, '840000cd0000000d', root_prev)
    # stools (marker 15) first; every other sit marker (chairs, benches, couches, ...) is treated as a chair
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
    # the front animation has no marker condition: it is also the fallback for any other entry marker
    chain(c_down, [(f'PC{tag}Chair{s}Sit', chair_enter[s], [ctda(F_MARKER, m)] if m else [], '140000cd00000000') for s, m in SIDES])
    chain(c_up, [(f'PC{tag}Chair{s}Stand', chair_exit[s], [ctda(F_MARKER, m)] if m else [], '140000cd00000000') for s, m in SIDES])
    n = len(specials)            # equal chances: <= 100/n, <= 200/n, ..., last unconditioned
    chain(c_sp, [(f'PC{tag}SittingSpecial{chr(65 + i)}', f, [ctda(F_RANDOM, 100 * (i + 1) // n, 5)] if i < n - 1 else [], '070000cd00000000')
                 for i, f in enumerate(specials)])
    chain(c_idle, [(f'PC{tag}ChairDynamicIdle1stPerson', HUMAN + '1stP_ChairDynamicIdle.kf', IS_1ST_PERSON, '000000cd00000000'),
                   (f'PC{tag}ChairDynamicIdle', chair_loop, [], '000000cd00000000')])
    # knock-down get-ups (vanilla KnockedDownIdles conditions: GetHitLocation == -1 AND GetKnockedState != 0)
    if get_up is None: return                # the race's get-up tree is built on its own (Eyebot, Protectron)
    knocked, = chain(0, [(f'PC{tag}KnockedDownIdles', G, [ctda(F_HITLOC, -1), ctda(F_KNOCKED, 0, 1)], '040000cd0000000d')])
    chain(knocked, [(f'PC{tag}GetUpFaceUp', get_up[0], [ctda(F_FACEUP, 1)], '070000cd00000000'),
                    (f'PC{tag}GetUpFaceDown', get_up[1], [], '070000cd00000000')])

ZI = 'PlayableCreatures\\Zetan\\IdleAnims'
Z = ZI + '\\'
creature_idles('Zetan', ZI,          # enters/exits/stool retargeted from the human set (anim/retarget_idle.py), seated = alien's own
    {'Left': Z + 'Chair_LeftEnter.kf', 'Right': Z + 'Chair_RightEnter.kf', 'Back': Z + 'Chair_BackEnter.kf', 'Front': Z + 'Chair_ForwardEnter.kf'},
    {'Left': Z + 'Chair_LeftExit.kf', 'Right': Z + 'Chair_RightExit.kf', 'Back': Z + 'Chair_BackExit.kf', 'Front': Z + 'Chair_ForwardExit.kf'},
    ALIEN + 'DynamicIdle_AliensSit.kf',
    Z + 'StoolEnter.kf', Z + 'StoolExit.kf', Z + 'DynamicIdle_SitStool.kf',
    [ALIEN + 'SpecialIdle_AliensSitA.kf', ALIEN + 'SpecialIdle_AliensSitB.kf'],
    (ALIEN + 'SpecialIdle_GetUpFaceUp.kf', ALIEN + 'SpecialIdle_GetUpFaceDown.kf'))
creature_idles('Ghost', 'PlayableCreatures\\Ghost\\IdleAnims',     # Ghost People skeleton = the human one: vanilla files fit as-is
    {'Left': HUMAN + 'Chair_LeftEnter.kf', 'Right': HUMAN + 'Chair_RightEnter.kf', 'Back': HUMAN + 'Chair_BackEnter.kf', 'Front': HUMAN + 'Chair_ForwardEnter.kf'},
    {'Left': HUMAN + 'Chair_LeftExit.kf', 'Right': HUMAN + 'Chair_RightExit.kf', 'Back': HUMAN + 'Chair_BackExit.kf', 'Front': HUMAN + 'Chair_ForwardExit.kf'},
    HUMAN + 'DynamicIdle_ChairSit.kf',
    HUMAN + 'StoolEnter.kf', HUMAN + 'StoolExit.kf', HUMAN + 'dynamicidle_sitstool.kf',
    [HUMAN + 'SitChairRelaxA.kf', HUMAN + 'SitChairRelaxB.kf', HUMAN + 'SitChairRelaxC.kf'],
    # Dead Money's own revive get-ups (the "semi-dead" ghost rising, 2.8 s) + their emerge vocal as a text key;
    # copies of NVDLC01\\Creatures\\Ghosts\\IdleAnims\\mt_KnockDown*.kf with 'Sound: NPCGhostEmergeVox' at t=0
    ('PlayableCreatures\\Ghost\\IdleAnims\\mt_KnockDownFaceUp.kf', 'PlayableCreatures\\Ghost\\IdleAnims\\mt_KnockDownFaceDown.kf'))

# ---------------- SPEL: radiation immunity ability ----------------
# SPIT: type 4 = Ability; EFID IncreaseRadiationResistance (FalloutNV 0x15179); EFIT magnitude 100, area 0, duration 0,
# range Self, actor value 0x14 RadiationResistance - the layout of vanilla abilities such as MS03PerkSurvivalAssistant.
spels = [record('SPEL', RAD_ABILITY, [('EDID', z('PCRadImmunityAbility')), ('FULL', z('Radiation Immunity')),
                                      ('SPIT', bytes.fromhex('04000000000000000000000000cdcdcd')),
                                      ('EFID', u32(0x15179)), ('EFIT', struct.pack('<IIIIi', 100, 0, 0, 0, 0x14))])]
GHOST_ABILITY = MOD | 0x8A0
# the Ghost People's race ability: + the creature's own Fire Immunity (FalloutNV FireImmunity 0B7CC9, Fire
# Resistance 85) next to the radiation / poison immunity (Dead Money cloud rules)
spels.append(record('SPEL', GHOST_ABILITY, [('EDID', z('PCGhostImmunityAbility')), ('FULL', z('Ghost Person Physiology')),
                                            ('SPIT', bytes.fromhex('04000000000000000000000000cdcdcd')),
                                            ('EFID', u32(0x15179)), ('EFIT', struct.pack('<IIIIi', 100, 0, 0, 0, 0x14)),
                                            ('EFID', u32(0x31D79)), ('EFIT', struct.pack('<IIIIi', 100, 0, 0, 0, 0x13))]
                                           + [(k, v) for k, v in SRC.byfid[0xB7CC9].subs() if k in ('EFID', 'EFIT', 'CTDA')]))
_next_id = max(_idle_next[0], (RAD_ABILITY & 0xFFFFFF) + 1)

# idle trees for the new skeletons: chair / stool enter + exit, seated loop and relax specials retargeted from
# the human set (anim/retarget_idle_creature.py); get-ups = the creatures' own vanilla files
_idle_next[0] = 0x862
GI = 'PlayableCreatures\\Ghoul\\IdleAnims'; G_ = GI + '\\'
SI = 'PlayableCreatures\\SuperMutant\\IdleAnims'; S_ = SI + '\\'
def _human_set(F):
    return ({'Left': F + 'Chair_LeftEnter.kf', 'Right': F + 'Chair_RightEnter.kf', 'Back': F + 'Chair_BackEnter.kf', 'Front': F + 'Chair_ForwardEnter.kf'},
            {'Left': F + 'Chair_LeftExit.kf', 'Right': F + 'Chair_RightExit.kf', 'Back': F + 'Chair_BackExit.kf', 'Front': F + 'Chair_ForwardExit.kf'},
            F + 'DynamicIdle_ChairSit.kf', F + 'StoolEnter.kf', F + 'StoolExit.kf', F + 'DynamicIdle_SitStool.kf',
            [F + 'SitChairRelaxA.kf', F + 'SitChairRelaxB.kf', F + 'SitChairRelaxC.kf'])
creature_idles('FeralGhoul', GI, *_human_set(G_),
               (GH + 'IdleAnims\\specialidle_getupfaceup.kf', GH + 'IdleAnims\\specialidle_getupfacedown.kf'))
creature_idles('SuperMutant', SI, *_human_set(S_),
               (SM + 'IdleAnims\\specialidle_getupfaceup.kf', SM + 'IdleAnims\\specialidle_getupfacedown.kf'))
_next_id = max(_next_id, _idle_next[0], (GHOST_ABILITY & 0xFFFFFF) + 1)

# ---------------- ghost moves + ghost sight ----------------
GT = Plugin('/home/claude/fnv/ghostif/GhostTrait.esp')          # Ghostification (masters FalloutNV, DeadMoney, OWB)
gt = {r.edid(): r for r in GT.recs if r.type != 'TES4'}
def copy_rec(src, fid, edid, full=None, patch=None):
    out = []
    for k, v in src.subs():
        if k == 'EDID': v = z(edid)
        elif k == 'FULL' and full: v = z(full)
        if patch: v = patch(k, v)
        out.append((k, v))
    return record(src.type, fid, out)
def scro_ok(r):                                                  # compiled scripts may only reference FalloutNV forms
    for k, v in r.subs():
        if k == 'SCRO': assert struct.unpack('<I', v)[0] >> 24 == 0, (r, hex(struct.unpack('<I', v)[0]))
MOVE_SCPT, MOVE_MGEF, MOVE_SPEL, SCAN_SPEL = MOD | 0x8A1, MOD | 0x8A2, MOD | 0x8A3, MOD | 0x8A4
SEARCH_SCPT, SEARCH_MGEF, SEARCH_SPEL = MOD | 0x8A5, MOD | 0x8A6, MOD | 0x8A7
for n in ('zGhostDodgeEffectSCRIPT', 'zGhastlySearchSCRIPT'): scro_ok(gt[n])
scpts = [copy_rec(gt['zGhostDodgeEffectSCRIPT'], MOVE_SCPT, 'PCGhostMoveEffectSCRIPT'),
         copy_rec(gt['zGhastlySearchSCRIPT'], SEARCH_SCPT, 'PCGhostSearchSCRIPT')]
def assoc(fid):
    def f(k, v):
        if k == 'DATA': v = bytearray(v); struct.pack_into('<I', v, 8, fid); v = bytes(v)
        return v
    return f
mgefs = [copy_rec(gt['zGhostDodgeEffect'], MOVE_MGEF, 'PCGhostMoveEffect', patch=assoc(MOVE_SCPT)),
         copy_rec(gt['zGhostSearch'], SEARCH_MGEF, 'PCGhostSearchEffect', patch=assoc(SEARCH_SCPT))]
efit = lambda mag, dur, av: struct.pack('<IIIIi', mag, 0, dur, 0, av)
spels.append(record('SPEL', MOVE_SPEL, [('EDID', z('PCGhostMoveSpell')), ('FULL', z('Ghastly Visage')),
    ('SPIT', gt['zzGhostMove'].get('SPIT')),
    # Turbo (slow motion) and the crit bonus only in combat, as in Ghostification's zzGhostMove
    # (each effect conditioned IsInCombat == 1, function 289)
    ('EFID', u32(0x120D80)), ('EFIT', efit(1, 1, 51)), ('CTDA', ctda(289, 1)),      # TurboEffect 1 s
    ('EFID', u32(0x6AA5D)), ('EFIT', efit(50, 1, 14)), ('CTDA', ctda(289, 1)),      # IncreaseCritChance +50, 1 s
    ('EFID', u32(MOVE_MGEF)), ('EFIT', efit(0, 1, -1))]))         # SetGhost 1 s
# the scan move is removed: PCGhostScanSpell 0x8A4 is no longer built
se = gt['zzGhastlySearch']
spels.append(record('SPEL', SEARCH_SPEL, [('EDID', z('PCGhostSearchSpell')), ('FULL', z('Ghastly Search')),
    ('SPIT', se.get('SPIT')), ('EFID', u32(SEARCH_MGEF)), ('EFIT', se.get('EFIT'))]))
# PipBoyLight override: lamp for everyone but Ghost People, Dead Money's ghost sight for Ghost People
pbl = SRC.byfid[0x147]
GR = [MOD | 0x805, MOD | 0x806]
not_ghost = [ctda(69, 0, 0, GR[0]), ctda(69, 0, 0, GR[1])]              # GetIsRace PCGhostRace == 0 AND ... == 0
is_ghost = [ctda(69, 1, 0, GR[0], OR=True), ctda(69, 1, 0, GR[1])]      # GetIsRace PCGhostRace == 1 OR ... == 1
pbl_subs = []
for k, v in pbl.subs():
    pbl_subs.append((k, v))
    if k == 'EFIT': pbl_subs += [('CTDA', c) for c in not_ghost]
pbl_subs += [('EFID', u32(DM | 0x012C3B)), ('EFIT', efit(0, 0, -1))] + [('CTDA', c) for c in is_ghost]
spels.append(record('SPEL', 0x147, pbl_subs))
_next_id = max(_next_id, (SEARCH_SPEL & 0xFFFFFF) + 1)

# the scan / search idles as Ghostification plays them: its copies of Dead Money's GhostsIdleLooking /
# HarvesterTrashPick (GhostsIdleLookingCOPY0000 / HarvesterTrashPickCOPY0000) use animation section 0x14 (whole body)
# and flag 0x01 (no attacking); Dead Money's originals are section 7, which the player's movement / jump groups replace.
# Played by the DLL with the PlayIdle mechanism (no idle-tree lookup); they still sit under a root in the Ghost tree,
# conditioned never to pass (GetRandomPercent < 0), so the engine never picks them on its own.
_idle_next[0] = _next_id
GD = 'NVDLC01\\Creatures\\Ghosts\\IdleAnims\\'
gm_root, = chain(0, [('PCGhostMoveIdles', 'PlayableCreatures\\Ghost\\IdleAnims', [ctda(F_RANDOM, 0, 4)], '1400000000000000')])
# scan removed: PCGhostIdleLooking 0x8A9 no longer built; the trash pick keeps its id 0x8AA
_idle_next[0] = (MOD | 0x8AA) & 0xFFFFFF
GHOST_TRASH, = chain(gm_root, [('PCGhostTrashPick', GD + 'mt_SpecialIdle_TrashPick.kf', [], '1400020000000100')])
_next_id = _idle_next[0]

# the trash pick's spear: an animation object is tied to its idle by the ANIO's DATA ("unload event" = IDLE;
# the idle-play object 0x4965D0 looks up the idle's anim objects through 0x46FD50). Dead Money's
# NVDLC01HarvesterTrashPickSpear points at its own HarvesterTrashPick, so our copy of the idle had no spear.
# Copy of it pointed at PCGhostTrashPick (Ghostification does the same with zNVDLC01HarvesterTrashPickSpear).
dm_spear = [r for r in Plugin('/home/claude/fnv/DeadMoney.esm').recs if r.type == 'ANIO' and (r.fid & 0xFFFFFF) == 0x008EDF][0]
anios = [copy_rec(dm_spear, MOD | _next_id, 'PCGhostTrashPickSpear', patch=lambda k, v: u32(GHOST_TRASH) if k == 'DATA' else v)]
_next_id += 1

# Lonesome Road Tunneler (PlayableCreatures\\Tunneler: the Spore Carrier / Tunneler skeleton = the street trog's,
# built on the finished trog set by anim/build_tunneler.py). Melee only (ini). New ids follow everything above.
TUN_RACE = MOD | _next_id; _next_id += 1
races.append(make_race(TUN_RACE, 'PCTunnelerRace', 'Tunneler', 'Tunnelers: burrowing, pack-hunting mutants of the Divide. Playable Creatures.',
                       'Creatures\\NVSporeCarrier\\NVDLC04_Tunneler.NIF'))
npcs += [preset(MOD | _next_id, 'PCTunnelerPresetMale', False, TUN_RACE), preset(MOD | (_next_id + 1), 'PCTunnelerPresetFemale', True, TUN_RACE)]
_next_id += 2
_idle_next[0] = _next_id
TI = 'PlayableCreatures\\Tunneler\\IdleAnims'; SC = 'Creatures\\NVSporeCarrier\\IdleAnims\\'
creature_idles('Tunneler', TI, *_human_set(TI + '\\'), (SC + 'specialidle_getupfaceup.kf', SC + 'specialidle_getupfacedown.kf'))
_next_id = _idle_next[0]

# Spore Carrier (base game): same skeleton folder as the Tunneler (PlayableCreatures\\Tunneler = the spore
# carrier's own animation set + the trog extras), so it shares the PCTunneler idle tree; only race + presets.
SPORE_RACE = MOD | _next_id; _next_id += 1
races.append(make_race(SPORE_RACE, 'PCSporeCarrierRace', 'Spore Carrier', 'Spore Carriers: humans overgrown by the Mojave\'s spore plants, fast and resistant to poison. Playable Creatures.',
                       'Creatures\\NVSporeCarrier\\SporeCarrier.NIF'))
npcs += [preset(MOD | _next_id, 'PCSporeCarrierPresetMale', False, SPORE_RACE), preset(MOD | (_next_id + 1), 'PCSporeCarrierPresetFemale', True, SPORE_RACE)]
_next_id += 2

# ---------------- race abilities + child races (race_extras.py) ----------------
# One custom ability per race = the creature's own abilities (vanilla spell effects copied with their conditions) +
# Radiation Immunity where radiation shouldn't hurt the race; listed on the RACE (SPLO). Every race gets a child race
# (Tranquility Lane's AgeRace -1). New ids follow everything above.
import race_extras as RX
def _eff(fid): return RX.effects(SRC.byfid[fid])
def _new():
    global _next_id
    v = MOD | _next_id; _next_id += 1; return v
PHYS = [  # (race EDID, ability EDID, name, effects)
    ('PCFeralGhoulRace', 'PCFeralGhoulPhysiology', 'Feral Ghoul Physiology', RX.RAD_IMMUNITY + _eff(0x617BE)),          # + GhoulRadHeal
    ('PCGlowingOneRace', 'PCGlowingOnePhysiology', 'Glowing One Physiology', RX.RAD_IMMUNITY + _eff(0x617BE) + _eff(0x8AF5C)),   # + glow
    ('PCSuperMutantRace', 'PCSuperMutantPhysiology', 'Super Mutant Physiology', RX.RAD_IMMUNITY + _eff(0x12B895)),     # SuperMutantDT +15
    # the Stealth Boy's own
    # effects (ALCH StealthBoy 043E94): StealthBoyInvis 043E95 (Chameleon 75, its refraction shimmer) + StealthField
    # 052117 (its stop-combat script), each conditioned IsSneaking == 1 (function 286) - on while sneaking, off when not.
    ('PCNightkinRace', 'PCNightkinPhysiology', 'Nightkin Physiology', RX.RAD_IMMUNITY + _eff(0xCE556) + _eff(0x7B201)  # DR +15, Ninja crit
        + [('EFID', u32(0x43E95)), ('EFIT', struct.pack('<IIIIi', 75, 0, 0, 0, 49)), ('CTDA', ctda(286, 1))]
        + [('EFID', u32(0x52117)), ('EFIT', struct.pack('<IIIIi', 0, 0, 0, 0, -1)), ('CTDA', ctda(286, 1))]),
    ('PCTunnelerRace', 'PCTunnelerPhysiology', 'Tunneler Physiology',
     [('EFID', u32(0x1630EF)), ('EFIT', struct.pack('<IIIIi', 2, 0, 0, 0, 0x4C))]),                                  # NVDLC04TunnelerDT +2
    ('PCSporeCarrierRace', 'PCSporeCarrierPhysiology', 'Spore Carrier Physiology', _eff(0xFCD7C)),                    # poison immunity
]
race_spells = {'PCGhostRace': [GHOST_ABILITY], 'PCGhostUnhoodedRace': [GHOST_ABILITY]}
for redid, aedid, full, effs in PHYS:
    fid = _new(); spels.append(RX.ability(fid, aedid, full, effs)); race_spells[redid] = [fid]
races, child_races, CHILD_IDS = RX.add_extras(races, race_spells, _new)
races += child_races
for e, c in CHILD_IDS.items(): print('  child race', e, '%06X' % (c & 0xFFFFFF))

# ---------------- Zetan (Helmet) ----------------
# Mothership Zeta's space-suit + helmet alien body (DLC05Alien3.NIF: suit and helmet parts, DLC05Alien2 /
# DLC05alienhelmet textures). It ships in FalloutNV's own Fallout - Meshes.bsa / Fallout - Textures.bsa but New Vegas
# never places it (CrAlien / CrAlienCaptain use DLC05Alien1). Same skeleton as the Zetan, so it shares the Zetan's
# folder, animations, idle tree, voice type and combat lines; own race (the body model is on the race), presets and
# child race. New ids after everything above, so no existing form id moves.
ZETAN_HELMET_RACE = _new()
zh = make_race(ZETAN_HELMET_RACE, 'PCZetanHelmetRace', 'Zetan (Helmet)',
               'Zetan in a space suit and helmet, from Mothership Zeta. Playable Creatures.',
               'DLC05\\Creatures\\Alien\\DLC05Alien3.NIF', voice=ZETAN_VOICE)
npcs += [preset(_new(), 'PCZetanHelmetPresetMale', False, ZETAN_HELMET_RACE, ZETAN_VOICE),
         preset(_new(), 'PCZetanHelmetPresetFemale', True, ZETAN_HELMET_RACE, ZETAN_VOICE)]
zh_adult, zh_child, zh_ids = RX.add_extras([zh], {}, _new)
races += zh_adult + zh_child
print('  race PCZetanHelmetRace %06X, child %06X' % (ZETAN_HELMET_RACE & 0xFFFFFF, zh_ids['PCZetanHelmetRace'] & 0xFFFFFF))

# ---------------- Eyebot ----------------
# Creatures\Eyebot (FalloutNV CrEyebot*: models brain.nif + eyebot.nif on Creatures\Eyebot\Skeleton.nif; spells
# PoisonImmunity 07D4F3 + RadImmunity 060C16; RobotFaction). Skeleton / animations in PlayableCreatures\Eyebot
# (build_skel_eyebot.py, anim/build_eyebot.py). Body = eyebot.nif, the brain in the left-hand slot (as the Super Mutant
# outfit). Ability = Radiation Immunity + its vanilla PoisonImmunity effects. Idle tree: get-up only (it can't sit).
EYEBOT_RACE = _new()
eb = make_race(EYEBOT_RACE, 'PCEyebotRace', 'Eyebot',
               'Eyebots: floating Enclave reconnaissance robots armed with a small laser. Immune to radiation and poison. Playable Creatures.',
               'Creatures\\Eyebot\\Eyebot.NIF', ('Creatures\\Eyebot\\brain.nif', None))
npcs += [preset(_new(), 'PCEyebotPresetMale', False, EYEBOT_RACE), preset(_new(), 'PCEyebotPresetFemale', True, EYEBOT_RACE)]
eb_ab = _new(); spels.append(RX.ability(eb_ab, 'PCEyebotPhysiology', 'Eyebot Physiology', RX.RAD_IMMUNITY + _eff(0x7D4F3)))
eb_adult, eb_child, eb_ids = RX.add_extras([eb], {'PCEyebotRace': [eb_ab]}, _new)
races += eb_adult + eb_child
_idle_next[0] = _next_id
EI = 'PlayableCreatures\\Eyebot\\IdleAnims'; EGU = 'Creatures\\Eyebot\\IdleAnims\\specialidle_getup.kf'
eb_knocked, = chain(0, [('PCEyebotKnockedDownIdles', EI, [ctda(F_HITLOC, -1), ctda(F_KNOCKED, 0, 1)], '040000cd0000000d')])
chain(eb_knocked, [('PCEyebotGetUpFaceUp', EGU, [ctda(F_FACEUP, 1)], '070000cd00000000'),
                   ('PCEyebotGetUpFaceDown', EGU, [], '070000cd00000000')])
_next_id = _idle_next[0]
print('  race PCEyebotRace %06X, child %06X, ability %06X' % (EYEBOT_RACE & 0xFFFFFF, eb_ids['PCEyebotRace'] & 0xFFFFFF, eb_ab & 0xFFFFFF))

# ---------------- robots' own weapons ----------------
# Robots fight with built-in WEAPs that are flagged non-playable (DNAM flags1 0x80). Each playable robot gets a copy:
# non-playable cleared, Can't Drop (0x08) and Embedded (0x20, fires from its NNAM node on the body - the eyebot's
# ProjectileNode_HeadLaser; no model) kept; ammo = the matching common ammo list. PlayableCreatures.dll hands it over at
# race-menu close (ini GiveItems=; not equipped).
weaps = []
def robot_weapon(src_fid, edid, ammo, regen=None, ammo_use=None, attack_mult=None):
    out = []
    for k, v in SRC.byfid[src_fid].subs():
        if k == 'EDID': v = z(edid)
        elif k == 'NAM0': v = u32(ammo)
        elif k == 'DNAM':
            d = bytearray(v); d[12] &= ~0x80 & 0xFF; d[12] |= 0x08
            if regen is not None: struct.pack_into('<f', d, 176, regen)   # DNAM Regen Rate (Recharger weapons)
            if ammo_use is not None: d[14] = ammo_use                         # DNAM Ammo Use (rounds per shot)
            if attack_mult is not None:                                      # faster semi-automatic fire: the attack
                old_mult = struct.unpack_from('<f', d, 60)[0]                 # animation's speed (DNAM Animation Attack Mult)
                struct.pack_into('<f', d, 60, attack_mult)                    # and Attack Shots/Sec scaled with it
                struct.pack_into('<f', d, 88, struct.unpack_from('<f', d, 88)[0] * attack_mult / old_mult)
            v = bytes(d)
        out.append((k, v))
    fid = _new(); weaps.append(record('WEAP', fid, out)); return fid
EYEBOT_ZAP = robot_weapon(0x22FF1, 'PCEyebotZap', 0x121155, 1.0)  # EyeBot1HP; recharging (AmmoMicroBreeder, 1 s per round); renamed Eyebot Laser + damage: see the end
print('  weapon PCEyebotZap %06X' % (EYEBOT_ZAP & 0xFFFFFF))

# ---------------- Securitron Mk I / Mk II ----------------
# Creatures\NVSecuritron (FalloutNV VSecuritronMk1TEMPLATE 158646 / Mk2TEMPLATE 158647: NVSecuritron.NIF + a face
# screen + screen static + smoke trail + voice box on Creatures\NVSecuritron\Skeleton.nif; spells RadImmunity 060C16,
# PoisonImmunity 07D4F3, SecuritronDT 12B891 (DT +20) / SecuritronMk2DT 160140 (DT +30); impact Metal; voice
# RobotVictor). Body = NVSecuritron.NIF; the face screen / static / voice box are grafted into the race's skeleton
# (build_skel_securitron.py: Skeleton.nif police face, SkeletonMkII.nif infantry face), animations in
# PlayableCreatures\Securitron (anim/build_securitron.py). Idle tree: get-ups only.
SECURITRON_RACE = _new()
sc1 = make_race(SECURITRON_RACE, 'PCSecuritronRace', 'Securitron',
                'Securitron: Mr. House\'s robots, rolling on one wheel; machine gun right arm, laser and grenade launcher left arm, shoulder missiles. Face screen: Eyes. Immune to radiation and poison, DT +20; once the Securitrons are upgraded (Fortification Hill), DT +30, Health +55 and auto-repair; its missiles and grenade launcher need that upgrade. Playable Creatures.',
                'Creatures\\NVSecuritron\\NVSecuritron.NIF')
npcs += [preset(_new(), 'PCSecuritronPresetMale', False, SECURITRON_RACE), preset(_new(), 'PCSecuritronPresetFemale', True, SECURITRON_RACE)]
# The Mk I's
# effects, plus the Mk II's extra over it while the global VStoryEventSecuritronsUpgraded (FalloutNV 120F2F) is 1 - the
# global the Lucky 38 upgrade sequence sets after the Fortification Hill bunker console, which every vanilla securitron
# script checks (VFSSecuritronSCRIPT, VStreetSecuritronScript...): DT +10 (SecuritronMk2DT 30 - SecuritronDT 20) and
# Health +55 (Mk2 template 175 - Mk1 120). The conditions are the engine's (GetGlobalValue, function 74).
SEC_UPGRADED = [ctda(74, 1, 0, 0x120F2F)]
sc1_ab = _new(); spels.append(RX.ability(sc1_ab, 'PCSecuritronPhysiology', 'Securitron Physiology', RX.RAD_IMMUNITY + _eff(0x7D4F3) + _eff(0x12B891)
    + [('EFID', u32(0x1630EF)), ('EFIT', struct.pack('<IIIIi', 10, 0, 0, 0, 0x4C))] + [('CTDA', c) for c in SEC_UPGRADED]      # IncreaseDamageThreshold +10
    + [('EFID', u32(0x31D78)), ('EFIT', struct.pack('<IIIIi', 55, 0, 0, 0, 0x10))] + [('CTDA', c) for c in SEC_UPGRADED]      # IncreaseHealth +55
    # "drivers for the Securitrons' onboard auto-repair systems": health regeneration, the vanilla RegenLow ability's
    # effect (Regen F3D42, magnitude 3), on the same upgrade condition
    + [('EFID', u32(0xF3D42)), ('EFIT', struct.pack('<IIIIi', 3, 0, 0, 0, 0x10))] + [('CTDA', c) for c in SEC_UPGRADED]))
SECURITRON2_RACE = _new()
sc2 = make_race(SECURITRON2_RACE, 'PCSecuritronMkIIRace', 'Securitron Mk II',
                'Securitron Mk II: the upgraded army model with the infantry face; same body and weapons. Immune to radiation and poison, DT +30. Playable Creatures.',
                'Creatures\\NVSecuritron\\NVSecuritron.NIF')
npcs += [preset(_new(), 'PCSecuritronMkIIPresetMale', False, SECURITRON2_RACE), preset(_new(), 'PCSecuritronMkIIPresetFemale', True, SECURITRON2_RACE)]
sc2_ab = _new(); spels.append(RX.ability(sc2_ab, 'PCSecuritronMkIIPhysiology', 'Securitron Mk II Physiology', RX.RAD_IMMUNITY + _eff(0x7D4F3) + _eff(0x160140)))
sc_adult, sc_child, sc_ids = RX.add_extras([sc1, sc2], {'PCSecuritronRace': [sc1_ab], 'PCSecuritronMkIIRace': [sc2_ab]}, _new)
races += sc_adult + sc_child
_idle_next[0] = _next_id
SI = 'PlayableCreatures\\Securitron\\IdleAnims'; SGU = 'Creatures\\NVSecuritron\\IdleAnims\\specialidle_getupface'
sc_knocked, = chain(0, [('PCSecuritronKnockedDownIdles', SI, [ctda(F_HITLOC, -1), ctda(F_KNOCKED, 0, 1)], '040000cd0000000d')])
chain(sc_knocked, [('PCSecuritronGetUpFaceUp', SGU + 'up.kf', [ctda(F_FACEUP, 1)], '070000cd00000000'),
                   ('PCSecuritronGetUpFaceDown', SGU + 'down.kf', [], '070000cd00000000')])
_next_id = _idle_next[0]
# its own weapons (as the eyebot's). (after the basement demonstration lines: Mk I = gatling laser + 9mm
# SMG, the Mark II OS adds drivers for the missile launcher and the grenade launcher) All four recharge like the Recharger
# weapons (ammo AmmoMicroBreeder 121155, nothing to carry; DNAM Regen Rate = seconds per round). The grenade launcher and
# missiles are refused by PlayableCreatures.dll until the securitrons are upgraded ("firmware missing").
# the laser is semi-automatic 2HR; its attack
# plays 2.2x faster (Animation Attack Mult 1.13 -> 2.5, Attack Shots/Sec 2.42 -> 5.35).
#   SMG      clip 60, 30 shots/s (vanilla automatic)
#   laser    clip 40, semi-automatic ~5.3 shots/s
#   grenades clip 5
#   missiles clip 6, 2 rounds per shot
# DNAM Regen Rate is seconds per round (vanilla Recharger Pistol 1.0: one round per second, 20 rounds in 20 s; a higher value recharges slower). The
# robot / securitron weapons refill a full clip in ~10-30 s and regenerate well below their fire rate:
# SMG 60 rounds 0.5 (30 s), laser 40 0.75 (30 s), grenade launcher 5 6.0, missiles 6 5.0; protectron hand / head laser
# 5 rounds 2.0 / 3.0; robobrain laser 6 2.0, mesmetron 1 5.0; flamers 24 / 10 rounds 1.0 / 1.5; gutsy plasma 6 2.0;
# sentry gatling laser 40 0.75 (30 s), missile launcher 1 6.0
SEC_SMG = robot_weapon(0x10A709, 'PCSecuritronSMG', 0x121155, 0.5)                   # WeapNVSecuritronSubmachineGun
SEC_GL = robot_weapon(0x10A70A, 'PCSecuritronGrenadeLauncher', 0x121155, 6.0)        # WeapNVSecuritronLauncher
SEC_LASER = robot_weapon(0x10A70B, 'PCSecuritronLaser', 0x121155, 0.75, attack_mult=2.5)   # WeapNVSecuritronLaser
SEC_MISSILE = robot_weapon(0x10BA90, 'PCSecuritronMissiles', 0x121155, 5.0, 2)       # WeapNVSecuritronMissile
print('  race PCSecuritronRace %06X (child %06X, ability %06X), PCSecuritronMkIIRace %06X (child %06X, ability %06X)' % (
    SECURITRON_RACE & 0xFFFFFF, sc_ids['PCSecuritronRace'] & 0xFFFFFF, sc1_ab & 0xFFFFFF,
    SECURITRON2_RACE & 0xFFFFFF, sc_ids['PCSecuritronMkIIRace'] & 0xFFFFFF, sc2_ab & 0xFFFFFF))
print('  weapons SMG %06X, grenade launcher %06X, laser %06X, missiles %06X' % tuple(x & 0xFFFFFF for x in (SEC_SMG, SEC_GL, SEC_LASER, SEC_MISSILE)))

# Securitron face screens = Eyes choices (both securitron races and their children); the skeletons carry every
# screen ('PCFace:<name>', build_skel_securitron.py) and PlayableCreatures.dll shows the one of the player's Eyes.
# Ids after everything else; the presets start on the race's default face (Mk I police, Mk II infantry).
SEC_FACES = [('Police', 'police_Neutral'), ('Infantry', 'infantry_Neutral'), ('Victor', 'Victor_Neutral'), ('Yes Man', 'YesMan_Neutral'),
             ('Mr. House', 'MrHouse_Neutral'), ('Jane', 'jane_Neutral'), ('Marilyn', 'marilyn_Neutral'), ('Blank', 'BlackTron')]
sec_eyes = []
for name, tex in SEC_FACES:
    fid = _new(); sec_eyes.append(fid)
    eyes_extra = globals().setdefault('eyes_extra', [])
    eyes_extra.append(record('EYES', fid, [('EDID', z('PCSecuritronFace' + name.replace(' ', '').replace('.', ''))), ('FULL', z(name)),
                                          ('ICON', z('Creatures\\Securitron\\%s.dds' % tex)), ('DATA', bytes([0x01]))]))
sec_races = {SECURITRON_RACE, SECURITRON2_RACE, sc_ids['PCSecuritronRace'], sc_ids['PCSecuritronMkIIRace']}
def _patch(rec, fn):
    typ, flags, fid, subs = RX.parse(rec); return RX.build(typ, flags, fid, fn(fid, subs))
races = [_patch(r, lambda fid, subs: [(k, b''.join(u32(e) for e in sec_eyes) if k == 'ENAM' else v) for k, v in subs])
         if RX.parse(r)[2] in sec_races else r for r in races]
def _preset_eyes(fid, subs):
    race = next(struct.unpack('<I', v)[0] for k, v in subs if k == 'RNAM')
    if race not in sec_races: return subs
    face = sec_eyes[1] if race in (SECURITRON2_RACE, sc_ids['PCSecuritronMkIIRace']) else sec_eyes[0]
    return [(k, u32(face) if k == 'ENAM' else v) for k, v in subs]
npcs = [_patch(r, _preset_eyes) for r in npcs]
print('  securitron faces (EYES) %s' % ', '.join('%s %06X' % (n, f & 0xFFFFFF) for (n, _), f in zip(SEC_FACES, sec_eyes)))

# The
# super mutant / nightkin armor of the vanilla creatures (armor-only parts worn over the base body, NIFZ of the
# smspinebreaker CREA) as wearable items in the races' loincloth slot (LeftHand, replacing smspinebreakerbare /
# nightkinbare); given at race-menu close (ini GiveItems) and drawn despite ArmorVisuals=0 (ini ShowForms).
SMA = 'Creatures\\SMSpineBreaker\\'
armors = []
SM_ARMOR = {}
for edid, name, model, val, hp, wt, dt, heavy in (
        ('PCSuperMutantLightArmor', 'Super Mutant Light Armor', 'smspinebreakerlight.nif', 100, 150, 15.0, 6, False),
        ('PCSuperMutantMediumArmor', 'Super Mutant Medium Armor', 'smspinebreakermedium.nif', 200, 250, 25.0, 10, False),
        ('PCSuperMutantHeavyArmor', 'Super Mutant Heavy Armor', 'smspinebreakerheavy.nif', 300, 350, 35.0, 14, True),
        ('PCNightkinArmor', 'Nightkin Armor', 'nightkinlead.nif', 200, 250, 20.0, 10, False)):
    fid = _new(); SM_ARMOR[edid] = fid
    armors.append(RX.armor(SRC, fid, edid, name, SMA + model, 0x08, val, hp, wt, dt, heavy))
print('  armor %s' % ', '.join('%s %06X' % (e, f & 0xFFFFFF) for e, f in SM_ARMOR.items()))

# The player's ragdoll sets up its pose matching from the body
# part data's first part with the "IK Data - Headtracking" flag (BPND flags 0x20; 0x87E4E0..0x87E575: part +0x60 & 0x20,
# its IK start node BPNI -> 0xC7DE60). Dead Money's NVDLC01GhostBodyPartData has no such part (Head flags 0x5B), so the
# pose was never set (the DLL's eye-position guard covered it). The ghost skeleton is fine (Bip01 Head is a ragdoll
# bone under Neck1). PCGhostBodyPartData = that BPTD verbatim with the Head part's headtracking flag set (BPNI is
# already Bip01 Head); PlayableCreatures.dll gives it to the ghost races.
DMP = Plugin('/home/claude/fnv/DeadMoney.esm')
GHOST_BPTD = _new()
_gb = []; _part = None
for k, v in DMP.byfid[0x01001AB5].subs():
    if k == 'EDID': v = z('PCGhostBodyPartData')
    elif k == 'BPTN': _part = v.rstrip(b'\0').decode('latin1')
    elif k == 'BPND' and _part == 'Head': d = bytearray(v); d[4] |= 0x20; v = bytes(d)
    _gb.append((k, v))
bptds = [record('BPTD', GHOST_BPTD, _gb)]
print('  body part data PCGhostBodyPartData %06X' % (GHOST_BPTD & 0xFFFFFF))

# own skeleton folders for the Glowing One (the Feral Ghoul set with the vanilla resurrect / radiation-burst cast
# as its unarmed back power attack) and the Nightkin (the Super Mutant set with every sneak file = its standing one,
# they sneak upright under the Stealth Boy); each folder needs its own idle tree (furniture + get-ups), copied from the
# Ghoul / Super Mutant trees. Ids after everything else.
_idle_next[0] = _next_id
creature_idles('GlowingOne', 'PlayableCreatures\\GlowingOne\\IdleAnims', *_human_set('PlayableCreatures\\GlowingOne\\IdleAnims\\'),
               (GH + 'IdleAnims\\specialidle_getupfaceup.kf', GH + 'IdleAnims\\specialidle_getupfacedown.kf'))
creature_idles('Nightkin', 'PlayableCreatures\\Nightkin\\IdleAnims', *_human_set('PlayableCreatures\\Nightkin\\IdleAnims\\'),
               (SM + 'IdleAnims\\specialidle_getupfaceup.kf', SM + 'IdleAnims\\specialidle_getupfacedown.kf'))
_next_id = _idle_next[0]

# ---------------- robots: Protectron (Robobrain, Mister Handy / Gutsy, Sentry Bot next) ----------------
#. Each robot as the Securitron: body = its skinned model in the race's body slot, its
# rigid parts (weapon emitters, brain, dome...) grafted into the race's skeleton (build_skel_robot.py), animations in
# PlayableCreatures\<Robot> (anim/build_robot.py), a physiology ability (radiation + poison immunity + its vanilla DT
# spell), a child race, an idle tree (get-ups), its own weapons as recharging copies (robot_weapon: AmmoMicroBreeder,
# DNAM Regen Rate) given at race-menu close (ini GiveItems), and its body part data with the head part flagged for
# head tracking (the ragdoll pose reference, as PCGhostBodyPartData; BPNI = the head bone - vanilla robot BPTDs carry
# a file path there).
_FULL_DNAM = SRC.byfid[0x18B9E].get('DNAM')                  # a 204-byte New Vegas DNAM (ProtectronHandLaser1HP)
_robot_weapon_v40 = robot_weapon
def robot_weapon(src_fid, edid, ammo, regen=None, ammo_use=None, attack_mult=None, nnam=None, anim=None, attack_anim=None):
    """Fallout 3-era WEAPs (sentry bot guns) have a 136-byte DNAM: padded with a New Vegas tail first;
    nnam: the embedded weapon's emitter node"""
    d = SRC.byfid[src_fid].get('DNAM')
    if len(d) < len(_FULL_DNAM):
        SRC.byfid[src_fid]._subs = [(k, (v + _FULL_DNAM[len(v):]) if k == 'DNAM' else v) for k, v in SRC.byfid[src_fid].subs()]
    fid = _robot_weapon_v40(src_fid, edid, ammo, regen, ammo_use, attack_mult)
    if nnam or anim is not None or attack_anim is not None:
        typ, fl, _f, subs = RX.parse(weaps[-1])
        def _f(k, v):
            if k == 'NNAM' and nnam: return z(nnam)
            if k == 'DNAM':
                d = bytearray(v)
                if anim is not None: d[0] = anim
                # DNAM Attack Animation (74 AttackLoop, 80 AttackSpin, 86 AttackSpin2)
                if attack_anim is not None: d[41] = attack_anim
                return bytes(d)
            return v
        weaps[-1] = record('WEAP', fid, [(k, _f(k, v)) for k, v in subs], fl)
    return fid

def robot_bptd(src_fid, edid, head_part, head_node, headtrack=True):
    """the head part's IK node = head_node (a ragdoll bone) and, with headtrack, flags 'IK Data' + 'IK Data -
    Headtracking': the player's ragdoll sets up its head pose from that part (0x87E130). headtrack=False keeps the
    vanilla flags (unused now: the Mister Handy / Gutsy body bending blamed on head tracking was the unkeyed Spine /
    Pelvis / Neck1, pinned in every file since robot anims v5)"""
    out = []; part = None; done = False
    for k, v in SRC.byfid[src_fid].subs():
        if k == 'EDID': v = z(edid)
        elif k == 'BPTN': part = v.rstrip(b'\0').decode('latin1'); cur = (part == head_part and not done)
        elif k == 'BPNI' and cur: v = z(head_node)
        elif k == 'BPND' and cur:
            d = bytearray(v)
            if headtrack: d[4] |= 0x22                  # IK data + headtracking: the ragdoll's head pose needs both
            v = bytes(d); done = True
        out.append((k, v))
    assert done, edid
    fid = _new(); bptds.append(record('BPTD', fid, out)); return fid

ROBOTS = {}
def robot_race(key, name, desc, body, hands, dt_spell, getups, getup_data='070000cd00000000', height=1.0, folder=None):
    """race + presets + physiology + child race + get-up idle tree; returns the race id (ROBOTS[key] has the rest).
    height: the race's height (the robobrain's rig is 3x size, CREA base scale 0.33)"""
    global races, npcs, _next_id
    rf = _new()
    r = make_race(rf, 'PC%sRace' % key, name, desc, body, hands)
    if height != 1.0:
        typ, fl, _f, subs = RX.parse(r)
        def _h(k, v):
            if k != 'DATA': return v
            d = bytearray(v); struct.pack_into('<ff', d, 16, height, height); return bytes(d)
        r = record('RACE', rf, [(k, _h(k, v)) for k, v in subs], fl)
    npcs += [preset(_new(), 'PC%sPresetMale' % key, False, rf), preset(_new(), 'PC%sPresetFemale' % key, True, rf)]
    # a race height other than 1 (the robobrain, 0.33): measured in game, Robobrain Forward 32 units/s (anim 273 skeleton units = 90 x 1/0.33) - the engine applies the ref
    # scale (ref scale x race height) to the player's root motion twice (0.33^2 = 0.11). Native fix: the physiology
    # ability raises SpeedMult by 1/height (IncreaseSpeedMult 031D7A on SpeedMult, AV 21): 100 -> ~300
    spd = []
    if height != 1.0:
        spd = [('EFID', u32(0x31D7A)), ('EFIT', struct.pack('<IIIIi', int(round(100 / height - 100)), 0, 0, 0, 21))]
    ab = _new(); spels.append(RX.ability(ab, 'PC%sPhysiology' % key, '%s Physiology' % name, RX.RAD_IMMUNITY + _eff(0x7D4F3) + _eff(dt_spell) + spd))
    adult, child, ids = RX.add_extras([r], {'PC%sRace' % key: [ab]}, _new)
    races += adult + child
    if folder:                    # shares another robot's skeleton folder, so its idle tree too (Mister Gutsy)
        ROBOTS[key] = dict(race=rf, child=ids['PC%sRace' % key], ability=ab); return rf
    _idle_next[0] = _next_id
    folder = 'PlayableCreatures\\%s\\IdleAnims' % key
    kn, = chain(0, [('PC%sKnockedDownIdles' % key, folder, [ctda(F_HITLOC, -1), ctda(F_KNOCKED, 0, 1)], '040000cd0000000d')])
    chain(kn, [('PC%sGetUpFaceUp' % key, getups[0], [ctda(F_FACEUP, 1)], getup_data),
               ('PC%sGetUpFaceDown' % key, getups[1], [], getup_data)])
    _next_id = _idle_next[0]
    ROBOTS[key] = dict(race=rf, child=ids['PC%sRace' % key], ability=ab)
    return rf

# Protectron (FalloutNV CrProtectron 01CF8F: protectron.nif + hand laser / head laser emitters, brain, dome on
# Creatures\Protectron\skeleton.nif; spells ProtectronDT 12B88E, RadImmunity, PoisonImmunity; voice RobotProtectron;
# get-ups MTSpecialIdle_KnockDownFaceUp / FaceDown). Weapons: Hand Laser (1HP, ProjectileNode_RHandLaser) and Head
# Laser (2HL, ProjectileNode_HeadLaser), recharging.
PRA = 'Creatures\\Protectron\\'
robot_race('Protectron', 'Protectron',
           'Protectron: RobCo\'s ubiquitous utility and security robot, a hand laser in its right arm and a laser in its head; a back jet for running. Immune to radiation and poison. Playable Creatures.',
           PRA + 'Protectron.NIF', (None, None), 0x12B88E,
           (PRA + 'IdleAnims\\MTSpecialIdle_KnockDownFaceUp.kf', PRA + 'IdleAnims\\MTSpecialIdle_KnockDownFaceDown.kf'), '140000cd00000000')
ROBOTS['Protectron']['weapons'] = [robot_weapon(0x18B9E, 'PCProtectronHandLaser', 0x121155, 2.0),      # ProtectronHandLaser1HP
                                   robot_weapon(0x18B9F, 'PCProtectronHeadLaser', 0x121155, 3.0)]      # ProtectronHeadLaser2HL
ROBOTS['Protectron']['bptd'] = robot_bptd(0x17F2C, 'PCProtectronBodyPartData', 'Head', 'Bip01 Head')

# Robobrain (CrRobobrain 01CF89: Robobrian.NIF + Brain / BrainTalk / LeftTrack / RightTrack on
# Creatures\Robobrain\skeleton.nif at base scale 0.33; RobobrainDT 12B88F; get-up SpecialIdle_KnockDownGetUp).
# Weapon: its Laser (1HP, ProjectileNode_Right), recharging. (Its Mesmetron is not given -; the head beam still serves the player's launchers.)
RBA = 'Creatures\\Robobrain\\'
robot_race('Robobrain', 'Robobrain',
           'Robobrain: a human brain in a tracked military chassis, a laser in its right arm. Immune to radiation and poison. Playable Creatures.',
           RBA + 'Robobrian.NIF', (None, None), 0x12B88F,
           (RBA + 'IdleAnims\\SpecialIdle_KnockDownGetUp.kf', RBA + 'IdleAnims\\SpecialIdle_KnockDownGetUp.kf'), height=0.33)
ROBOTS['Robobrain']['weapons'] = [robot_weapon(0x50ED0, 'PCRobobrainLaser', 0x121155, 2.0)]           # RobobrainLaser1HPRight
ROBOTS['Robobrain']['bptd'] = robot_bptd(0x2E7AF, 'PCRobobrainBodyPartData', 'Head', 'Bip01 Head')

# Mister Handy / Mister Gutsy (CrMisterHandy 02977A / CrMisterGutsy 021EBD: MisterHandy.NIF / MisterGutsy.NIF + front
# claw (skinned: the race's left-hand slot) + brain, jets, flamer tank / flamer, buzzsaw or plasma gun + pack (grafted:
# PlayableCreatures\MisterHandy\Skeleton.nif / SkeletonGutsy.nif); MrHandyDT 12B88B / MrGutsyDT 12B88C; get-up
# SpecialIdle_KnockDownGetUp). Weapon: its flamer (2HL, ProjectileNode_HeadLaser), recharging. It flies (ini NoFallDamage).
MGA = 'Creatures\\MisterGutsy\\'
robot_race('MisterHandy', 'Mister Handy',
           'Mister Handy: the General Atomics household robot, hovering on its jets; a flamer, a buzzsaw and a claw for arms. Immune to radiation and poison. Playable Creatures.',
           MGA + 'MisterHandy.NIF', (MGA + 'HandyFrontClaw.NIF', None), 0x12B88B,
           (MGA + 'IdleAnims\\SpecialIdle_KnockDownGetUp.kf', MGA + 'IdleAnims\\SpecialIdle_KnockDownGetUp.kf'))
# (the flamers still don't fire for the player, with the AttackLoop rebuilt) an automatic Launcher
# (2HL) never fires for the player; the player's own Flamer is a Two-Hand Handle weapon (2HH, DNAM anim type 8), as is
# the sentry bot's gatling laser, which fires -> both robot flamers are 2HH (its animations: the flamer arm as for 2HL)
# (firing the flamer turned the whole robot over - the in-game anim debug showed
# AnimGroupOverride\TNW_MinigunFire_TTW\_male\2hhattackspin(up / down).kf playing: Titans of the New West's JSON gives
# every actor with GetIsCreature == 0 - the player in any race - its human minigun spin; Enhanced Animations'
# EnhancedAnimations_TTW folder (GetCreatureType == -1) does the same) the flamers' Attack Animation AttackSpin (the
# creature flamers') -> AttackLoop, the vanilla Incinerator's / Gatling Laser's (the sentry bot's laser gatling fires so)
ROBOTS['MisterHandy']['weapons'] = [robot_weapon(0xA0C02, 'PCMisterHandyFlamer', 0x121155, 1.0, anim=8, attack_anim=74)]   # MisterHandyFlamer2HL
ROBOTS['MisterHandy']['bptd'] = robot_bptd(0x36C18, 'PCMisterHandyBodyPartData', 'Tracking Sensor', 'Bip01 Head')
robot_race('MisterGutsy', 'Mister Gutsy',
           'Mister Gutsy: the military Mister Handy, a flamer and a plasma gun for arms. Immune to radiation and poison. Playable Creatures.',
           MGA + 'MisterGutsy.NIF', (MGA + 'GutsyFrontClaw.NIF', None), 0x12B88C,
           (MGA + 'IdleAnims\\SpecialIdle_KnockDownGetUp.kf', MGA + 'IdleAnims\\SpecialIdle_KnockDownGetUp.kf'), folder='MisterHandy')
ROBOTS['MisterGutsy']['weapons'] = [robot_weapon(0x39550, 'PCMisterGutsyFlamer', 0x121155, 1.5, anim=8, attack_anim=74)]   # MisterGutsyFlamer2HL
ROBOTS['MisterGutsy']['bptd'] = robot_bptd(0x36C17, 'PCMisterGutsyBodyPartData', 'Tracking Sensor', 'Bip01 Head')

# Sentry Bot (CrSentryBotGL 01CF8A: SentryBotLaserGatling.NIF (the gatling-laser arm) + missile pod on
# Creatures\SentryBot\Skeleton.nif; SentryBotDT 12B88D; get-ups SpecialIdle_GetUpLeft / Right). Weapons: its Laser
# Gatling (2HH) and Minigun (2HR, the CrSentryBotMG arm's gun - fired from the same arm), both recharging. Their
# Fallout 3-era DNAM is padded to the New Vegas size first (robot_weapon).
SBA = 'Creatures\\SentryBot\\'
robot_race('SentryBot', 'Sentry Bot',
           'Sentry Bot: the heavy military robot on three wheels, a gatling laser arm and a missile pod. Immune to radiation and poison. Playable Creatures.',
           SBA + 'SentryBotLaserGatling.NIF', (None, None), 0x12B88D,
           (SBA + 'IdleAnims\\SpecialIdle_GetUpLeft.kf', SBA + 'IdleAnims\\SpecialIdle_GetUpRight.kf'))
# (CrSentryBotGL carries SentryBotGatling2HH + SentryBotMissileLauncher2HL) the minigun
# (CrSentryBotMG's) is replaced by the missile launcher, fired from the missile pod (vanilla NNAM = the gatling's node).
ROBOTS['SentryBot']['weapons'] = [robot_weapon(0x389AF, 'PCSentryBotLaserGatling', 0x121155, 0.75),     # SentryBotGatling2HH
                                  robot_weapon(0x57E8F, 'PCSentryBotMissileLauncher', 0x121155, 6.0, nnam='PCMissileEmitter')]
ROBOTS['SentryBot']['bptd'] = robot_bptd(0x31C61, 'PCSentryBotBodyPartData', 'Head', 'Bip01 Head')

# appended after the robot ids above, so those stay put:
#  * Robobrain: its Mesmetron - its head beam (2HL, one round, EnchRobobrainAttack), the same
#    embedded-launcher setup as the Lakelurk's shriek;
#  * Mister Handy: its vanilla buzzsaw (1HM, melee - no ammo);
#  * Mister Gutsy: its plasma gun (1HP, right arm); and its own skeleton folder
#    PlayableCreatures\MisterGutsy (claw melee animations), so its own get-up idle tree.
ROBOTS['Robobrain']['weapons'].append(robot_weapon(0xBF5A4, 'PCRobobrainMesmetron', 0x121155, 5.0))      # RobobrainMesmetron
ROBOTS['MisterHandy']['weapons'].append(robot_weapon(0x3BC6F, 'PCMisterHandyBuzzsaw', 0x121155))          # MisterHandyBuzzsaw
ROBOTS['MisterGutsy']['weapons'].append(robot_weapon(0x3954F, 'PCMisterGutsyPlasma', 0x121155, 2.0))      # MisterGutsyPlasma1HP
_idle_next[0] = _next_id
_gk, = chain(0, [('PCMisterGutsyKnockedDownIdles', 'PlayableCreatures\\MisterGutsy\\IdleAnims', [ctda(F_HITLOC, -1), ctda(F_KNOCKED, 0, 1)], '040000cd0000000d')])
chain(_gk, [('PCMisterGutsyGetUpFaceUp', MGA + 'IdleAnims\\SpecialIdle_KnockDownGetUp.kf', [ctda(F_FACEUP, 1)], '070000cd00000000'),
            ('PCMisterGutsyGetUpFaceDown', MGA + 'IdleAnims\\SpecialIdle_KnockDownGetUp.kf', [], '070000cd00000000')])
_next_id = _idle_next[0]
for k, v in ROBOTS.items():
    print('  robot %s: race %06X child %06X ability %06X weapons %s bptd %06X' % (k, v['race'] & 0xFFFFFF, v['child'] & 0xFFFFFF, v['ability'] & 0xFFFFFF,
          ', '.join('%06X' % (w & 0xFFFFFF) for w in v['weapons']), v['bptd'] & 0xFFFFFF))

# ---------------- Deathclaw ----------------
# Creatures\DeathClaw (FalloutNV CrDeathClaw 01CF9A deathclaw.nif, CrDeathClawAlpha 0E584F deathclaw_AlphaMale.nif,
# CrDeathClawMother 0E5851 deathclaw_Mother.nif, the Legendary Deathclaw / dark alpha males deathclaw_AM_G.nif
# (CrDeathClawAlphaVariant 0E62FB), CrDeathClawBaby 0E5850 "Young Deathclaw" = deathclaw.nif at base scale 0.75 - all on
# Creatures\DeathClaw\Skeleton.nif). Skeleton / animations in PlayableCreatures\Deathclaw (build_skel_creature.py,
# anim/creatures/deathclaw.py + assemble_deathclaw.py): it holds and uses every weapon (melee weapons swing with its own
# claw attacks), sits on chairs and stools. Races: Deathclaw (both sexes deathclaw.nif), Deathclaw Alpha (male: alpha
# male, female: mother), Legendary Deathclaw; each one's child race is the Young Deathclaw (deathclaw.nif, height 0.75).
# Abilities = their vanilla DT spells (DeathclawDT 12B892, AlphaMotherDeathclawDT 12B894, young: BabyDeathclawDT
# 12B893). Body part data = their CREA PNAM SupermutantrBodyPartData 02026E (ini BodyPartData=).
DCA = 'Creatures\\DeathClaw\\'
DEATHCLAWS = {}
DC_YOUNG_H = 0.75
_dc_young_ab = None
def deathclaw_race(key, name, desc, body, body_f, dt_spell):
    """race + presets + physiology + the Young Deathclaw child race"""
    global races, npcs, _dc_young_ab
    rf = _new()
    r = make_race(rf, 'PC%sRace' % key, name, desc, DCA + body, body_f=DCA + body_f if body_f else None)
    npcs += [preset(_new(), 'PC%sPresetMale' % key, False, rf), preset(_new(), 'PC%sPresetFemale' % key, True, rf)]
    ab = _new(); spels.append(RX.ability(ab, 'PC%sPhysiology' % key, '%s Physiology' % name, _eff(dt_spell)))
    if _dc_young_ab is None:
        # a race height below 1 slows the player's root motion twice (see robot_race): SpeedMult + 1/height
        _dc_young_ab = _new()
        spels.append(RX.ability(_dc_young_ab, 'PCDeathclawYoungPhysiology', 'Young Deathclaw Physiology', _eff(0x12B893)
                                + [('EFID', u32(0x31D7A)), ('EFIT', struct.pack('<IIIIi', int(round(100 / DC_YOUNG_H - 100)), 0, 0, 0, 21))]))
    adult, child, ids = RX.add_extras([r], {'PC%sRace' % key: [ab]}, _new)
    typ, fl, cf, subs = RX.parse(child[0])
    young = []
    for k, v in subs:
        if k == 'FULL': v = z('Young ' + name)
        elif k == 'MODL' and v.rstrip(b'\0').decode('latin1') in (DCA + body, DCA + (body_f or body)): v = z(DCA + 'deathclaw.nif')
        elif k == 'SPLO': v = u32(_dc_young_ab)
        elif k == 'DATA':
            d = bytearray(v); struct.pack_into('<ff', d, 16, DC_YOUNG_H, DC_YOUNG_H); v = bytes(d)
        young.append((k, v))
    races += adult + [record('RACE', cf, young, fl)]
    DEATHCLAWS[key] = dict(race=rf, child=cf, ability=ab)
    return rf
deathclaw_race('Deathclaw', 'Deathclaw',
               'Deathclaws: towering, horned predators bred from chameleons, the deadliest animals of the Mojave. Playable Creatures.',
               'deathclaw.nif', None, 0x12B892)
deathclaw_race('DeathclawAlpha', 'Deathclaw Alpha',
               'Deathclaw alpha males and mothers: the largest and most savage of the pack. Playable Creatures.',
               'deathclaw_AlphaMale.nif', 'deathclaw_Mother.nif', 0x12B894)
deathclaw_race('DeathclawLegendary', 'Legendary Deathclaw',
               'The Legendary Deathclaw: a dark, scarred alpha male, the pack leader of the Mojave. Playable Creatures.',
               'deathclaw_AM_G.nif', None, 0x12B894)
_idle_next[0] = _next_id
DI = 'PlayableCreatures\\Deathclaw\\IdleAnims'
creature_idles('Deathclaw', DI, *_human_set(DI + '\\'),
               (DCA + 'IdleAnims\\specialidle_getupfaceup.kf', DCA + 'IdleAnims\\specialidle_getupfacedown.kf'))
_next_id = _idle_next[0]
for k, v in DEATHCLAWS.items():
    print('  deathclaw %s: race %06X child %06X ability %06X' % (k, v['race'] & 0xFFFFFF, v['child'] & 0xFFFFFF, v['ability'] & 0xFFFFFF))
print('  young deathclaw ability %06X' % (_dc_young_ab & 0xFFFFFF))

# ---------------- Eyebot / Protectron furniture ----------------
# Their chairs and stools: the Eyebot settles onto the seat and rests there unanimated (anim/eyebot_furniture.py: the
# human entry path and heading, its hover height mapped onto the seat), the Protectron sits like a toddler on its short
# legs (retarget_idle_creature.py, creatures/protectron_sit.py). Furniture trees only - their get-up trees stay as built
# above. Ids after everything else.
_idle_next[0] = _next_id
creature_idles('Eyebot', EI, *_human_set(EI + '\\'), None)
_PI = 'PlayableCreatures\\Protectron\\IdleAnims'
creature_idles('Protectron', _PI, *_human_set(_PI + '\\'), None)
_next_id = _idle_next[0]

# ---------------- Eyebot laser ----------------
# (user: eyebots attack with a laser; ED-E's zapper is only its commissary trick; the vanilla eyebot's 5 damage is too
# little.) PCEyebotZap keeps its form id: vanilla EyeBot1HP's red laser beam (BeamLaserProjectile 014B0F, its own impact
# / muzzle flash), named "Eyebot Laser", ED-E's damage (EDEZapGun: 25), recharging as before (1 s per round, clip 12).
projs = []
EYEBOT_LASER_DAMAGE = 25
for i, w in enumerate(weaps):
    typ, fl, fid, subs = RX.parse(w)
    if fid != EYEBOT_ZAP: continue
    def _w(k, v):
        if k == 'EDID': return z('PCEyebotLaser')
        if k == 'FULL': return z('Eyebot Laser')
        if k == 'DATA': d = bytearray(v); struct.pack_into('<h', d, 12, EYEBOT_LASER_DAMAGE); return bytes(d)
        return v
    weaps[i] = record('WEAP', fid, [(k, _w(k, v)) for k, v in subs], fl)
print('  eyebot laser %06X, damage %d' % (EYEBOT_ZAP & 0xFFFFFF, EYEBOT_LASER_DAMAGE))

# ---------------- Ghost Gas ----------------
# Ghost People's own heavy weapon: the vanilla Flamer (WeapFlamer 00432D: 2HH, AttackLoop, flame-type projectile) spraying
# the Sierra Madre gas from the palm (their 2HH animations cast from the open hand, the gun model hidden there). Changes
# from the Flamer: projectile PCGhostGasProjectile (FlameProjectile's flight, model = the ghost leg gas spray as a flame
# projectile, tools/build_ghost_gas_nif.py; no muzzle flash, no fire light), enchantment PCGhostGasEnch (the vanilla
# Poison effect 031851 - Damage Health over time, resisted by Poison Resistance - 2 pts for 5 s, as the Flamer's burn),
# no burn critical spell, gas-puff impacts instead of scorch marks (PCGhostGasImpactSet, below), the Flamer's own fire
# loop as its spray sound, no pilot-light idle loop; recharging like the robots' weapons
# (AmmoMicroBreeder, nothing to carry; clip 60, 0.5 s per round = 30 s), Can't Drop, weightless, worth nothing, no
# weapon mods; the Flamer's Hide Backpack flag cleared (the race's own backpack / gear stays drawn while it is out).
# Given at race-menu close (ini GiveItems), not equipped.
GHOST_GAS_MODEL = 'PlayableCreatures\\Ghost\\GhostGasProjectile.nif'
gas_snd = _new()        # (id kept, no record: the toxic-cloud loop played nothing as a weapon loop; the Flamer's own
                        # fire loop WPNFlamerFire3DLPM is used)
gas_ench = _new()
enchs = [record('ENCH', gas_ench, [('EDID', z('PCGhostGasEnch')), ('FULL', z('Ghost Gas')),
                                   ('ENIT', bytes.fromhex('02000000000000000000000002cdcdcd')),     # weapon enchantment (as EnchFlamerEffect)
                                   ('EFID', u32(0x31851)), ('EFIT', struct.pack('<IIIIi', 2, 0, 5, 1, 16))])]   # Poison 2 / 5 s
gas_proj = _new()
def _gp(k, v):
    if k == 'EDID': return z('PCGhostGasProjectile')
    if k == 'FULL': return z('Ghost Gas')
    if k == 'MODL': return z(GHOST_GAS_MODEL)
    if k == 'DATA':
        d = bytearray(v); struct.pack_into('<H', d, 0, struct.unpack_from('<H', d, 0)[0] & ~0x08)  # no muzzle flash
        struct.pack_into('<II', d, 16, 0, 0); return bytes(d)                                      # no light, no muzzle flash light
    return v
projs.append(record('PROJ', gas_proj, [(k, _gp(k, v)) for k, v in SRC.byfid[0x3BF0B].subs() if k not in ('MODT', 'NAM1', 'NAM2')]))
_NO_IMPACT = [r for r in SRC.recs if r.type == 'IPDS' and r.edid() == 'NoImpactSet'][0].fid
GHOST_GAS = _new()
def _gw(k, v):
    if k == 'EDID': return z('PCGhostGas')
    if k == 'FULL': return z('Ghost Gas')
    if k == 'EITM': return u32(gas_ench)
    if k == 'NAM0': return u32(0x121155)                                        # AmmoMicroBreeder
    if k == 'INAM': return u32(_NO_IMPACT)                                     # no flame scorch decals; -> PCGhostGasImpactSet below
    if k == 'DATA': d = bytearray(v); struct.pack_into('<iif', d, 0, 0, 200, 0.0); return bytes(d)    # value 0, health, weight 0
    if k == 'DNAM':
        d = bytearray(v); d[12] = (d[12] | 0x08) & ~0x10 & 0xFF                # Can't Drop; not Hide Backpack (the Flamer's)
        struct.pack_into('<I', d, 36, gas_proj); struct.pack_into('<f', d, 176, 0.5); return bytes(d)
    if k == 'CRDT': d = bytearray(v); struct.pack_into('<I', d, 12, 0); return bytes(d)   # no FlamerCritEffect02
    return v
weaps.append(record('WEAP', GHOST_GAS, [(k, _gw(k, v)) for k, v in SRC.byfid[0x432D].subs()
                                        if k not in ('UNAM', 'MOD4', 'MWD1', 'WNM1', 'WMI1')]))        # no idle loop, no mods
print('  ghost gas %06X (projectile %06X, enchantment %06X)' % (GHOST_GAS & 0xFFFFFF, gas_proj & 0xFFFFFF, gas_ench & 0xFFFFFF))

# ---------------- Ghost knife spear ----------------
# Ghost People's thrown knife spear: Dead Money's best one, NVDLC01WeapThrowingSpearGhost50 (0117FC: the level-50 ghost's
# Throwing Knife Spear, damage 145), made playable (non-playable flag cleared), Can't Drop, worth nothing, weightless,
# and bottomless the way Ghostification's zNVDLC01WeapThrowingSpearGhost50 is: Ammo Use 0, so a throw never uses the
# spear up (no script). Its critical hits knock the target down: PCGhostSpearKnockdownSpell (on every critical hit, not
# only killing ones) -> PCGhostSpearKnockdownEffect (script effect, as the vanilla MaulerKnockdownEffect) ->
# PCGhostSpearKnockdownScript = the vanilla knockdown scripts' compiled code (VictoryRifle / Mauler / MissFortune:
# "if the target lacks Stonewall, player.PushActorAway target <force>, else ShowMessage StonewallMessage") with its own
# force. Given at race-menu close (ini GiveItems), not equipped.
SPEAR_KNOCK_FORCE = 15
_mauler_scpt = SRC.byfid[0x10F0A1]                          # MaulerKnockdownScript (force 15 at the 6E int literal)
scro_ok(_mauler_scpt)
_sk_scpt, _sk_mgef, _sk_spel = _new(), _new(), _new()
def _sks(k, v):
    if k == 'SCDA':
        i = v.index(bytes.fromhex('6e0f000000')); v = v[:i + 1] + struct.pack('<i', SPEAR_KNOCK_FORCE) + v[i + 5:]
    if k == 'SCTX':
        v = (b'scn PCGhostSpearKnockdownScript\r\n\r\nref myself\r\n\r\nBegin ScriptEffectStart\r\n\r\nIf myself.HasPerk Stonewall != 1\r\n'
             b'\tset myself to GetSelf\r\n\tplayer.pushactoraway myself %d\r\nElse\r\n\tShowMessage StonewallMessage\r\nEndIf\r\n\r\nEnd\r\n' % SPEAR_KNOCK_FORCE)
    return v
scpts.append(copy_rec(_mauler_scpt, _sk_scpt, 'PCGhostSpearKnockdownScript', patch=_sks))
mgefs.append(copy_rec(SRC.byfid[0x10F0A0], _sk_mgef, 'PCGhostSpearKnockdownEffect', full='Knife Spear Knockdown', patch=assoc(_sk_scpt)))   # MaulerKnockdownEffect
spels.append(record('SPEL', _sk_spel, [('EDID', z('PCGhostSpearKnockdownSpell')), ('FULL', z('Knife Spear Knockdown')),
    ('SPIT', SRC.byfid[0x10F09F].get('SPIT')), ('EFID', u32(_sk_mgef)), ('EFIT', SRC.byfid[0x10F09F].get('EFIT'))]))   # as MaulerKnockdownSpell
GHOST_SPEAR = _new()
def _gs(k, v):
    if k == 'EDID': return z('PCGhostKnifeSpear')
    if k == 'DATA': d = bytearray(v); struct.pack_into('<i', d, 0, 0); struct.pack_into('<f', d, 8, 0.0); return bytes(d)   # value 0, weight 0
    if k == 'DNAM':
        d = bytearray(v); d[12] = (d[12] & ~0x80 & 0xFF) | 0x08                   # playable, Can't Drop
        d[14] = 0; return bytes(d)                                             # Ammo Use 0: bottomless
    if k == 'CRDT': d = bytearray(v); d[8] = 0; struct.pack_into('<I', d, 12, _sk_spel); return bytes(d)   # knockdown on every crit
    return v
weaps.append(record('WEAP', GHOST_SPEAR, [(k, _gs(k, v)) for k, v in DMP.byfid[0x010117FC].subs()]))
print('  ghost knife spear %06X (knockdown spell %06X, effect %06X, script %06X)' % (GHOST_SPEAR & 0xFFFFFF, _sk_spel & 0xFFFFFF, _sk_mgef & 0xFFFFFF, _sk_scpt & 0xFFFFFF))

# ---------------- Ghost Gas impacts ----------------
# Where Ghost Gas hits (actors, ground, walls - every material but water) a slow green puff of the same gas billows out:
# IPCT PCGhostGasImpact (model PlayableCreatures\Ghost\GhostGasImpact.nif = build_ghost_gas_nif.py --impact; no decal,
# no sound - the Flamer's fire loop plays) in IPDS PCGhostGasImpactSet (water: NoImpact 0686ED), the Ghost Gas WEAP's
# impact data set. Ids after everything else.
_GAS_IMPACT, _GAS_IMPACT_SET = _new(), _new()
ipcts = [record('IPCT', _GAS_IMPACT, [('EDID', z('PCGhostGasImpact')), ('MODL', z('PlayableCreatures\\Ghost\\GhostGasImpact.nif')),
    ('DATA', struct.pack('<fIffII', 1.6, 0, 45.0, 16.0, 1, 1))])]       # duration, surface normal, angle, radius, sound level, no decal
ipdss = [record('IPDS', _GAS_IMPACT_SET, [('EDID', z('PCGhostGasImpactSet')),
    ('DATA', struct.pack('<12I', *[0x686ED if m == 'Water' else _GAS_IMPACT for m in
        ('Stone', 'Dirt', 'Grass', 'Glass', 'Metal', 'Wood', 'Organic', 'Cloth', 'Water', 'HollowMetal', 'OrganicBug', 'OrganicGlow')]))])]
for i, w in enumerate(weaps):
    typ, fl, fid, subs = RX.parse(w)
    if fid == GHOST_GAS: weaps[i] = record('WEAP', fid, [(k, u32(_GAS_IMPACT_SET) if k == 'INAM' else v) for k, v in subs], fl)
print('  ghost gas impact %06X, set %06X' % (_GAS_IMPACT & 0xFFFFFF, _GAS_IMPACT_SET & 0xFFFFFF))

# ---------------- Lakelurk ----------------
# Creatures\MirelurkKing (FalloutNV NVCrLakelurk 14F44B lakelurk.NIF, NVCrLakelurkKing 14F44C "Alpha Male Lakelurk"
# lakelurkking.NIF, both on Creatures\MirelurkKing\Skeleton.nif - the Mirelurk King's skeleton and animations; spell
# LakelurkWaterBreathing 14F448; body part data MirelurkKingBodyPartData 05362D; no DT spell). Skeleton / animations in
# PlayableCreatures\Lakelurk (build_skel_creature.py, anim/creatures/lakelurk.py + assemble_lakelurk.py): melee weapons
# swing with its own claw attacks (weapon unseen), every gun fires as its own shriek from the mouth (gun unseen), thrown
# weapons and mines in its claw; sits on chairs and stools. Races: Lakelurk (both sexes lakelurk.nif), Lakelurk Alpha
# (both sexes lakelurkking.nif); each one's child race is the Young Lakelurk (lakelurk.nif, height 0.75).
# Abilities: its water breathing. Weapon: its Shriek (LakelurkSonic2HL 14F449: 2HL, embedded, the sonic projectile from
# ProjectileNode_Sonic on its head, LakelurkShriek enchantment - Perception -10 for 10 s and 50 damage), recharging like
# the robots' weapons (AmmoMicroBreeder, nothing to carry; clip 1, 3 s per round), Can't Drop, weightless, worth nothing.
# Given at race-menu close (ini GiveItems), not equipped.
LKA = 'Creatures\\MirelurkKing\\'
LAKELURKS = {}
LK_YOUNG_H = 0.75
_lk_young_ab = None
def lakelurk_race(key, name, desc, body):
    global races, npcs, _lk_young_ab
    rf = _new()
    r = make_race(rf, 'PC%sRace' % key, name, desc, LKA + body)
    npcs += [preset(_new(), 'PC%sPresetMale' % key, False, rf), preset(_new(), 'PC%sPresetFemale' % key, True, rf)]
    ab = _new(); spels.append(RX.ability(ab, 'PC%sPhysiology' % key, '%s Physiology' % name, _eff(0x14F448)))
    if _lk_young_ab is None:
        # a race height below 1 slows the player's root motion twice (see robot_race): SpeedMult + 1/height
        _lk_young_ab = _new()
        spels.append(RX.ability(_lk_young_ab, 'PCLakelurkYoungPhysiology', 'Young Lakelurk Physiology', _eff(0x14F448)
                                + [('EFID', u32(0x31D7A)), ('EFIT', struct.pack('<IIIIi', int(round(100 / LK_YOUNG_H - 100)), 0, 0, 0, 21))]))
    adult, child, ids = RX.add_extras([r], {'PC%sRace' % key: [ab]}, _new)
    typ, fl, cf, subs = RX.parse(child[0])
    young = []
    for k, v in subs:
        if k == 'FULL': v = z('Young ' + name)
        elif k == 'MODL' and v.rstrip(b'\0').decode('latin1') == LKA + body: v = z(LKA + 'lakelurk.nif')
        elif k == 'SPLO': v = u32(_lk_young_ab)
        elif k == 'DATA':
            d = bytearray(v); struct.pack_into('<ff', d, 16, LK_YOUNG_H, LK_YOUNG_H); v = bytes(d)
        young.append((k, v))
    races += adult + [record('RACE', cf, young, fl)]
    LAKELURKS[key] = dict(race=rf, child=cf, ability=ab)
    return rf
lakelurk_race('Lakelurk', 'Lakelurk',
              'Lakelurks: the Mojave\'s freshwater mirelurks, hulking shelled hunters of Lake Mead that stun their prey with a sonic shriek. Breathe underwater. Playable Creatures.',
              'lakelurk.nif')
lakelurk_race('LakelurkAlpha', 'Lakelurk Alpha',
              'Lakelurk alpha males: the darker, tougher leaders of the lakelurk nests. Breathe underwater. Playable Creatures.',
              'lakelurkking.nif')
_idle_next[0] = _next_id
LI = 'PlayableCreatures\\Lakelurk\\IdleAnims'
creature_idles('Lakelurk', LI, *_human_set(LI + '\\'),
               (LKA + 'IdleAnims\\specialidle_getupfaceup.kf', LKA + 'IdleAnims\\specialidle_getupfacedown.kf'))
_next_id = _idle_next[0]
LAKELURK_SHRIEK = robot_weapon(0x14F449, 'PCLakelurkShriek', 0x121155, 3.0)      # LakelurkSonic2HL
_lt, _lf, _lfid, _ls = RX.parse(weaps[-1]); assert _lfid == LAKELURK_SHRIEK
weaps[-1] = record('WEAP', _lfid, [(k, (lambda d: (struct.pack_into('<i', d, 0, 0), struct.pack_into('<f', d, 8, 0.0), bytes(d))[-1])(bytearray(v))
                                    if k == 'DATA' else v) for k, v in _ls], _lf)       # worth nothing, weightless
# The player's ragdoll sets up its pose matching from the body part data's headtracking part's IK node (see the ghost BPTD
# above): MirelurkKingBodyPartData's Head part (node Bip01 Neck1, flags with headtracking) names the skeleton file as its
# IK node, not a bone, so the pose was never set up - the eye-position code read an empty pose and the game crashed on a
# save load. PCLakelurkBodyPartData = that BPTD with the Head part's IK node Bip01 Neck1 (its ragdoll top bone: Bip01 Head
# has no body). Its neck is also the head-tracking bone - tested: the lakelurk faces its target (unlike Hillfolk1, whose
# neck tracking tipped the head up; those keep Bip01 Head, the DLL takes the pose from the ragdoll ancestor). Ids after
# everything else.
LAKELURK_BPTD = robot_bptd(0x5362D, 'PCLakelurkBodyPartData', 'Head', 'Bip01 Neck1')
# The same ragdoll head pose for every other robot / creature whose vanilla body part data has no part with both 'IK Data'
# (0x02) and 'IK Data - Headtracking' (0x20) on a ragdoll bone (tools/bptd_audit.py): Securitron (Head flags 0x49, IK node
# = the skeleton file), Eyebot (no head part: its Combat Inhibitor - the brain, Bip01 Spine Brain - takes the flags),
# Tunneler / Spore Carrier (DLCPittTrogBodyPartData: Head 0x09). Ids after everything else.
SECURITRON_BPTD = robot_bptd(0x10699E, 'PCSecuritronBodyPartData', 'Head', 'Bip01 Screen01')
EYEBOT_BPTD = robot_bptd(0x2F870, 'PCEyebotBodyPartData', 'Combat Inhibitor', 'Bip01 Spine Brain')
TUNNELER_BPTD = robot_bptd(0x945BB, 'PCTunnelerBodyPartData', 'Head', 'Bip01 Head')
print('  body part data: securitron %06X, eyebot %06X, tunneler %06X' % (SECURITRON_BPTD & 0xFFFFFF, EYEBOT_BPTD & 0xFFFFFF, TUNNELER_BPTD & 0xFFFFFF))

# The player's action idles (vanilla ActivateIdles / StartCannibal of the human tree): the engine plays them from the
# actor's own idle tree and the action waits for them - with none, drinking from a water source only played the activate
# sound. Per skeleton folder: ActivateIdles > ActWaterSource (drink) / ActStimpakSource (stimpak), and StartCannibal;
# conditions and DATA copied from the vanilla records; the files are anim/act_idles.py's. Ids after everything else.
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
_idle_next[0] = _next_id
for _tag, _f in (('Zetan', 'Zetan'), ('Ghost', 'Ghost'), ('FeralGhoul', 'Ghoul'), ('GlowingOne', 'GlowingOne'), ('SuperMutant', 'SuperMutant'),
                 ('Nightkin', 'Nightkin'), ('Tunneler', 'Tunneler'), ('Eyebot', 'Eyebot'), ('Securitron', 'Securitron'),
                 ('Protectron', 'Protectron'), ('Robobrain', 'Robobrain'), ('MisterHandy', 'MisterHandy'), ('MisterGutsy', 'MisterGutsy'),
                 ('SentryBot', 'SentryBot'), ('Deathclaw', 'Deathclaw'), ('Lakelurk', 'Lakelurk')):
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
for _tag, _f in (('Zetan', 'Zetan'), ('Ghost', 'Ghost'), ('FeralGhoul', 'Ghoul'), ('GlowingOne', 'GlowingOne'), ('SuperMutant', 'SuperMutant'),
                 ('Nightkin', 'Nightkin'), ('Tunneler', 'Tunneler'), ('Eyebot', 'Eyebot'), ('Securitron', 'Securitron'),
                 ('Protectron', 'Protectron'), ('Robobrain', 'Robobrain'), ('MisterHandy', 'MisterHandy'), ('MisterGutsy', 'MisterGutsy'),
                 ('SentryBot', 'SentryBot'), ('Deathclaw', 'Deathclaw'), ('Lakelurk', 'Lakelurk')):
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
for _tag, _f in (('Zetan', 'Zetan'), ('FeralGhoul', 'Ghoul'), ('GlowingOne', 'GlowingOne'), ('SuperMutant', 'SuperMutant'),
                 ('Nightkin', 'Nightkin'), ('Deathclaw', 'Deathclaw'), ('Lakelurk', 'Lakelurk')):
    pod_idles(_tag, 'PlayableCreatures\\%s\\IdleAnims' % _f)
pod_idles('Ghost', 'PlayableCreatures\\Ghost\\IdleAnims', {'PodEnter.kf': HUMAN + 'SitTranquilityChairEnter.kf',
          'PodExit.kf': HUMAN + 'SitTranquilityChairExit.kf', 'PodIdle.kf': HUMAN + 'SitTranquilityChairIdle.kf'})
# Robots without a seated pose (Robobrain, Securitron, Sentry Bot, Mister Handy / Gutsy): the chair / stool tree with
# placeholder files (their own idle; anim/pod.py --robot) under the FurnitureIdles root sandman_idles made for them
for _tag, _f in (('Robobrain', 'Robobrain'), ('Securitron', 'Securitron'), ('SentryBot', 'SentryBot'), ('MisterHandy', 'MisterHandy'), ('MisterGutsy', 'MisterGutsy')):
    _F = 'PlayableCreatures\\%s\\IdleAnims' % _f
    creature_idles(_tag, _F, *_human_set(_F + '\\'), None, root=IDLE_BY_EDID[f'PC{_tag}FurnitureIdles'], root_prev=IDLE_BY_EDID[f'PC{_tag}Sleeping'])
_next_id = _idle_next[0]
# ---------------- Ghost gas spray (the Ghost's unarmed forward power attack) ----------------
# anim/ghost_spray.py: the Ghost steps in and sprays gas from its respirator (the skeleton's PCGhostMaskSpray particles,
# switched on by the attack file). What it does to the one target the attack lands on: the race's unarmed attack effect
# (ini UnarmedEffect / UnarmedEffectAnim = 0x5D AttackForwardPower; the DLL puts them on the player's base as a creature's
# EITM / EAMT). The engine casts it from the attacker's MagicCaster on the actor the attack hit, and only when the
# playing attack's group is the EAMT one (0x8C2387 .. 0x8C248E); its Touch effect lands on that target alone - no area,
# unlike the Glowing One's burst (a Self script that explodes around the caster).
#   PCGhostGasSpray (SPEL, actor effect, Touch, 1 s) -> PCGhostGasKnockdownEffect (MGEF, script effect as the vanilla
#   MaulerKnockdownEffect; hit shader PCGhostGasHitShader) -> PCGhostGasKnockdownScript: the target's fatigue taken to
#   GAS_KO_SECONDS below zero. Below zero an actor is knocked out and lies there until its fatigue is back above zero;
#   it returns at fFatigueReturnBase (1.0) + fFatigueReturnMult (0) x ... a second while below zero (engine defaults,
#   0x648050 / 0x88B5A0, called from the actor update only while fatigue < 0; no plugin overrides them), so every
#   target - whatever its fatigue - goes down and stays down GAS_KO_SECONDS before it gets up.
#   PCGhostGasHitShader (EFSH): the vanilla PuffOfSmoke with the ghosts' gas texture (their leg spray's) - a puff of
#   the gas round the target. PCGhostGasSprayHiss (SOUN): the spray's hiss (anim text key), vanilla steam-release one-shots.
GAS_KO_SECONDS = 4
GAS_PUFF_SCALE = (5.0, 26.0)    # gas hit shader particle size, birth -> death (PuffOfSmoke 15 -> 75)
GAS_PUFF_LIFE = 1.4
_gk_scpt, _gk_mgef, _gk_spel, _gk_efsh = _new(), _new(), _new(), _new()
GHOST_GAS_SPRAY_SOUND = _new()
_gk_src = ('scn PCGhostGasKnockdownScript\r\n\r\n'
           '; Ghost People gas spray (their unarmed forward power attack): knocks the target out for a few seconds -\r\n'
           '; its fatigue taken to %d below zero (fatigue returns at 1 a second while below zero).\r\n\r\n'
           'float fFatigue\r\n\r\nBegin ScriptEffectStart\r\n'
           '\tset fFatigue to GetAV Fatigue + %d\r\n\tif fFatigue > 0\r\n\t\tDamageAV Fatigue fFatigue\r\n\tendif\r\nEnd\r\n'
           % (GAS_KO_SECONDS, GAS_KO_SECONDS)).encode('latin1')
def _st(op, data): return struct.pack('<HH', op, len(data)) + data
_ko = str(GAS_KO_SECONDS).encode()
_expr = b' X' + struct.pack('<HHHH', 0x100E, 4, 1, 0x16) + b' ' + _ko + b' +'           # GetActorValue Fatigue + K
_body = (_st(0x15, b'f\x01\x00' + struct.pack('<H', len(_expr)) + _expr) +                 # set fFatigue to ...
         _st(0x16, struct.pack('<HH', 1, 8) + b' f\x01\x00 0 >') +                          # if fFatigue > 0 (1 statement)
         _st(0x1181, struct.pack('<HH', 2, 0x16) + b'f\x01\x00') +                          # DamageActorValue Fatigue fFatigue
         _st(0x19, b'') + _st(0x11, b''))                                                    # endif, End
_scda = _st(0x1D, b'') + _st(0x10, struct.pack('<HI', 0x11, len(_body))) + _body          # scn, Begin ScriptEffectStart
scpts.append(record('SCPT', _gk_scpt, [('EDID', z('PCGhostGasKnockdownScript')),
    ('SCHR', struct.pack('<IIIIHH', 0, 0, len(_scda), 1, 0x100, 1)), ('SCDA', _scda), ('SCTX', _gk_src),
    ('SLSD', struct.pack('<I', 1) + bytes(20)), ('SCVR', z('fFatigue'))]))
_puff = SRC.byfid[0x0C1126]                                                                 # PuffOfSmoke
def _efsh(k, v):
    if k == 'ICO2': return z('nvdlc01\\effects\\FXGhostLegFX.dds')
    if k == 'DATA':
        d = bytearray(v); d[16:19] = bytes((70, 96, 40))                                    # membrane fill: the gas's green
        for o in (188, 192, 196): d[o:o + 3] = b'\xff\xff\xff'                               # particle colour keys white:
                                                                                             # the texture's own colour
        # the gas texture is one cloud, not PuffOfSmoke's 2 x 2 sheet of puffs: texture count U / V 1 (with 2 each
        # particle showed a quarter of the cloud, cut off with straight hard edges); particle size keys 15 -> 75
        # (PuffOfSmoke's) down to GAS_PUFF_SCALE, lifetime 2.25 -> GAS_PUFF_LIFE s
        struct.pack_into('<II', d, 276, 1, 1)
        struct.pack_into('<ff', d, 172, *GAS_PUFF_SCALE)
        struct.pack_into('<f', d, 132, GAS_PUFF_LIFE)
        return bytes(d)
    return v
efshs = [copy_rec(_puff, _gk_efsh, 'PCGhostGasHitShader', patch=_efsh)]
def _gkm(k, v):
    if k == 'DESC': return z('Knocked out by Ghost gas.')
    if k == 'DATA':
        d = bytearray(v); struct.pack_into('<I', d, 0, 0x175)                               # Mauler's 0x170 + hostile, detrimental
        struct.pack_into('<I', d, 8, _gk_scpt); struct.pack_into('<I', d, 0x20, _gk_efsh); return bytes(d)
    return v
mgefs.append(copy_rec(SRC.byfid[0x10F0A0], _gk_mgef, 'PCGhostGasKnockdownEffect', full='Ghost Gas', patch=_gkm))
spels.append(record('SPEL', _gk_spel, [('EDID', z('PCGhostGasSpray')), ('FULL', z('Ghost Gas')),
    ('SPIT', struct.pack('<IIIB3s', 0, 0, 0, 0x7B, b'\0\0\0')),                             # actor effect, no auto-calc (Mauler's flags + 1)
    ('EFID', u32(_gk_mgef)), ('EFIT', struct.pack('<IIIIi', 0, 0, 1, 1, -1))]))             # magnitude 0, area 0, 1 s, Touch
souns.append(soun(GHOST_GAS_SPRAY_SOUND, 'PCGhostGasSprayHiss', 'fx\\amb\\cistern\\oneshots\\steamrelease\\', 0.0, 0x1001, (30, 15)))
print('  ghost gas spray: spell %06X, effect %06X, script %06X (%d bytes), hit shader %06X, sound %06X'
      % (_gk_spel & 0xFFFFFF, _gk_mgef & 0xFFFFFF, _gk_scpt & 0xFFFFFF, len(_scda), _gk_efsh & 0xFFFFFF, GHOST_GAS_SPRAY_SOUND & 0xFFFFFF))

for k, v in LAKELURKS.items():
    print('  lakelurk %s: race %06X child %06X ability %06X' % (k, v['race'] & 0xFFFFFF, v['child'] & 0xFFFFFF, v['ability'] & 0xFFFFFF))
print('  young lakelurk ability %06X, shriek %06X, body part data %06X' % (_lk_young_ab & 0xFFFFFF, LAKELURK_SHRIEK & 0xFFFFFF, LAKELURK_BPTD & 0xFFFFFF))

# Ghost People back dodge (Core: back + jump with a weapon out, the 6th GhostMoveForms form): the body shrinks out of sight
# in a thick cloud of its gas and slips back, its own root motion (anim/ghost_dodge.py; the cloud = the skeleton's
# PCGhostDodgeCloud). DATA = Dead Money's HopLeft's (section 7, no attacking: an idle played this way moves the player by its
# root motion, as the hops do); under PCGhostMoveIdles (never passes) after the trash pick, so the engine never picks it
# on its own - Core plays it as it plays the hops. New id after everything else.
GHOST_DODGE = _new()
idles.append(record('IDLE', GHOST_DODGE, [('EDID', z('PCGhostDodgeBack')),
    ('MODL', z('PlayableCreatures\\Ghost\\IdleAnims\\PCGhostDodgeBack.kf')),
    ('ANAM', struct.pack('<II', gm_root, GHOST_TRASH)), ('DATA', bytes.fromhex('070000ff00000100'))]))
# Its spell (the 7th GhostMoveForms form, cast by Core in place of the hop's): the hop's effects + IncreaseSpeedMult
# (vanilla 031D7A, Speed Multiplier +DODGE_SPEED for 1 s). A special idle's root motion moves the player no faster than
# the player's own movement speed (the hops go ~4 ft running, less walking, whatever their keys say), so the dodge raises
# that speed for its length; the idle's own slide still sets direction and timing.
DODGE_SPEED = 300
GHOST_DODGE_SPEL = _new()
spels.append(record('SPEL', GHOST_DODGE_SPEL, [('EDID', z('PCGhostDodgeSpell')), ('FULL', z('Ghastly Visage')),
    ('SPIT', gt['zzGhostMove'].get('SPIT')),
    ('EFID', u32(0x120D80)), ('EFIT', efit(1, 1, 51)), ('CTDA', ctda(289, 1)),      # TurboEffect 1 s, in combat
    ('EFID', u32(0x6AA5D)), ('EFIT', efit(50, 1, 14)), ('CTDA', ctda(289, 1)),      # IncreaseCritChance +50, 1 s, in combat
    ('EFID', u32(MOVE_MGEF)), ('EFIT', efit(0, 1, -1)),                              # SetGhost 1 s
    ('EFID', u32(0x31D7A)), ('EFIT', efit(DODGE_SPEED, 1, 21))]))                   # IncreaseSpeedMult +DODGE_SPEED, 1 s
print('  ghost back dodge idle %06X, spell %06X' % (GHOST_DODGE & 0xFFFFFF, GHOST_DODGE_SPEL & 0xFFFFFF))

groups = [group('HAIR', [hair]), group('EYES', [eyes] + eyes_extra), group('RACE', races), group('SOUN', souns), group('MGEF', mgefs), group('SCPT', scpts), group('ENCH', enchs), group('SPEL', spels), group('ARMO', armors), group('WEAP', weaps), group('NPC_', npcs), group('IDLE', idles)] + ([group('PROJ', projs)] if projs else []) + [group('ANIO', anios), group('EFSH', efshs), group('BPTD', bptds), group('VTYP', vtyp), group('IPCT', ipcts), group('IPDS', ipdss)]   # vanilla group order
nrec = 2 + len(efshs) + len(ipcts) + len(ipdss) + len(enchs) + len(projs) + len(eyes_extra) + len(armors) + len(bptds) + len(races) + len(weaps) + len(npcs) + len(souns) + len(mgefs) + len(scpts) + len(spels) + len(vtyp) + len(idles) + len(anios) + len(groups)
tes4 = record('TES4', 0, [
    ('HEDR', struct.pack('<fII', 1.34, nrec, _next_id)),
    ('CNAM', z('i3ncore')),
    ('SNAM', z('Playable Creatures: Zetan (+ helmeted), Ghost People (hooded / unhooded), Feral Ghoul, Glowing One, Super Mutant, Nightkin, Tunneler, Spore Carrier, Eyebot, Securitron Mk I / II, robots, Deathclaws, Lakelurks; creature voices, idle trees, radiation immunity')),
    *[x for m in MASTERS for x in (('MAST', z(m)), ('DATA', struct.pack('<Q', 0)))]])
open(OUT, 'wb').write(tes4 + b''.join(groups))
print('wrote', OUT, len(races), 'races', len(npcs), 'presets')
