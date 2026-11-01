"""Builds PlayableCreaturesVoices.esp: creature voice sets as ordinary combat dialogue (no DLL involvement).

  QUST  PCVoice (start game enabled) owns every line.
  DIAL  overrides of FalloutNV.esm's combat topics Attack / Hit / PowerAttack / Death. In FO3/FNV a topic's quest
        list (QSTI) is taken from the last plugin that overrides the topic, so each override carries the union of
        the quest lists of every plugin in the load order that touches the topic (voice_topics.json, scanned
        on the game PC) plus PCVoice. Masters = every plugin those quests come from + PlayableCreatures.esp.
  INFO  one per voice file, "Random" flag (last one "Random End"), condition GetIsRace <race> == 1 on the subject,
        blank subtitle. Quest priority 110 so it wins over FalloutNV's GenericPlayer (101, unconditioned player
        grunts whose voice files were never shipped). Files go to PlayerVoiceMale/Female (the player's voice) and
        to the race's own voice type folder (NPCs of the race). Voice files: sound\\voice\\<this esp>\\<voice type>\\<quest>_<topic>_<info id>_1.ogg
usage: python3 build_voices.py <out.esp> <copy-plan.tsv>
Re-run (after re-scanning voice_topics.json) whenever a mod that adds combat dialogue is added to the load order."""
import json, struct, sys
sys.path.insert(0, '/home/claude/fnv')
def z(s): return s.encode('latin1') + b'\0'
def sub(t, data): return t.encode() + struct.pack('<H', len(data)) + data
def record(t, fid, subs, flags=0):
    body = b''.join(sub(k, v) for k, v in subs)
    return t.encode() + struct.pack('<IIIIHH', len(body), flags, fid, 0, 15, 0) + body
def group(label, recs):
    body = b''.join(recs)
    return b'GRUP' + struct.pack('<I4sIIHH', 24 + len(body), label.encode(), 0, 0, 0, 0) + body
u32 = lambda v: struct.pack('<I', v)

OUT = sys.argv[1] if len(sys.argv) > 1 else '/home/claude/fnv/build/PlayableCreaturesVoices.esp'
PLAN = sys.argv[2] if len(sys.argv) > 2 else '/home/claude/fnv/build/voice_copy_plan.tsv'
# merged mode: the voice records go into a race plugin instead of their own plugin.
#   PC_MASTERS        master list of the target plugin -> its own forms (races, voice types, quest) are index len(masters);
#                     topic quest lists keep only quests from those masters
#   PC_VOICE_PLUGIN   target plugin name (voice file folder sound\\voice\\<plugin>\\...)
#   PC_VOICE_SETS     'fnv' = sets for PlayableCreatures.esp's races only, 'all' = every set (TTW plugin)
#   PC_VOICE_ID_BASE  first id (default 0x800); ids are allocated over ALL sets whatever the filter, so a line has
#                     the same id (and file name) in both plugins
import os
MERGED = 'PC_MASTERS' in os.environ
ESP_NAME = os.environ.get('PC_VOICE_PLUGIN', 'PlayableCreaturesVoices.esp')
SETS = os.environ.get('PC_VOICE_SETS', 'all')
ID_BASE = int(os.environ.get('PC_VOICE_ID_BASE', '0x800'), 16)
T = json.load(open('/home/claude/fnv/voice_topics.json'))
TOPICS = {'Attack': 0xDC, 'Hit': 0xDD, 'PowerAttack': 0xE6, 'Death': 0xEF}
QUEST_EDID = 'PCVoice'
GET_IS_VOICE_TYPE = 427
GET_IS_RACE = 69
GET_IS_SEX = 70                                    # param 0 male / 1 female

# ---- voice sets: voice type (in PlayableCreatures.esp) -> topic -> source files (relative to _PCWork\sound_src\sound)
ZD = 'voice\\zeta.esm\\dlc05creaturealien\\dlc05aliendialogue_'
ZATK = [ZD + f'attack_{i}_1' for i in ('000036fc', '000036fd', '000036fe', '000036ff', '00003700', '000076b9')]
# races: every race (local id in PlayableCreatures.esp) that uses the set (conditions OR'ed); npc_folder: voice type
# folder for NPCs of the race (None = player folders only); ext: file extension of the sources (.ogg voice / .wav fx)
GD = 'fx\\npc\\ghostpeople\\'
FG = 'fx\\npc\\feralghoul\\'
SMV = 'voice\\falloutnv.esm\\creaturelowintsm\\'
NKV = 'voice\\falloutnv.esm\\creaturesupermutant\\'
YK = 'voice\\pointlookout.esm\\'                                                    # PointLookout - Main.bsa
TV = 'voice\\thepitt.esm\\dlc01uniquetrogvoice\\'                                  # ThePitt - Main.bsa
SDC = 'voice\\fallout3.esm\\creaturesupermutantdc\\'                              # TTW Fallout3 - Voices.bsa
ED = 'fx\\npc\\ed_e\\'                                                               # ED-E beeps
RV = 'voice\\falloutnv.esm\\robotvictor\\'                                      # securitron lines
def GR(folder, topic, iid): return f'voice\\falloutnv.esm\\{folder}\\genericrobot_{topic}_{iid}_1'   # robots
SM_PWR = ['0015cd8f', '0015cd90', '0015cd91', '0015cd92', '0015cd93']                 # CreatureLowIntSM VDialogueS PowerAttack lines
# voice-type sets also ship their files in the voice type's own folder: PlayableCreatures.dll gives
# the player that voice type, and the engine looks a line's file up under sound\\voice\\<plugin>\\<speaker's voice type>\\
# - with only the PlayerVoiceMale / Female copies the Capital super mutants, swampfolk, trogs and tunnelers were silent.
VOICES = [
    # 0x8E0 = Zetan (Helmet), same voice
    dict(vtype_local=0x816, races=[0x800, 0x8E0], npc_folder='pczetanvoice', ext='.ogg', topics={
        'Attack': ZATK,
        'PowerAttack': ZATK,
        'Hit': [ZD + f'hit_{i}_1' for i in ('000036f7', '0000798d', '0000798e', '0000798f', '00007990', '00007991', '00007992', '00007993', '00007994')],
        'Death': [ZD + f'death_{i}_1' for i in ('000036e5', '000036e6', '000036e7', '000036e8', '000036e9', '000036ea', '000036eb')],
    }),
    # Ghost People (hooded 805 / unhooded 806): Dead Money has no pain sound for them -> short jump grunts on Hit,
    # their CREA Death sound on Death. The engine only voices the player's Hit and Death topics.
    dict(races=[0x805, 0x806], npc_folder=None, ext='.wav', topics={
        'Hit': [GD + f'jumpvox\\cr_ghostpeople_jumpvox_0{i}' for i in (1, 2, 3)],
        'Death': [GD + f'death\\cr_ghostpeople_death_0{i}' for i in (1, 2)],
    }),
    # Feral Ghoul / Glowing One (855 / 856): their CREA Hit (NPCFeralGhoulInjured) and Death sounds
    dict(races=[0x855, 0x856], npc_folder=None, ext='.wav', topics={
        'Hit': [FG + f'injured\\npc_feralghoul_injured_0{i}' for i in (1, 2, 3)],
        'Death': [FG + f'death\\npc_feralghoul_death_0{i}' for i in (1, 2, 3, 4)],
    }),
    # Super Mutant (857): FalloutNV's own super mutant Hit / Death lines (VDialogueSuperMutant, voice CreatureLowIntSM)
    dict(races=[0x857], npc_folder=None, ext='.ogg', topics={
        'Hit': [SMV + f'vdialoguesupermutant_hit_0015cd{i:02x}_1' for i in range(0x5C, 0x67)],
        'Death': [SMV + f'vdialoguesupermutant_death_0015cd{i:02x}_1' for i in range(0x27, 0x30)],
    }),
    # Nightkin (858): VDialogueNightkin Hit / Death lines (voice CreatureSuperMutant)
    dict(races=[0x858], npc_folder=None, ext='.ogg', topics={
        'Hit': [NKV + f'vdialoguenightkin_hit_00152b{i:02x}_1' for i in range(0x84, 0x8A)],
        'Death': [NKV + f'vdialoguenightkin_death_00152b{i:02x}_1' for i in range(0x81, 0x84)],
    }),
    # PowerAttack: the engine also voices the player's PowerAttack topic (FalloutNV GenericPlayer has 6 lines,
    # "Haargh!" etc., subtitles only - Ghostification / Mute Player Voice ship empty files for them). Every creature race
    # gets its own lines so no human shout/subtitle appears. Appended as separate sets so existing INFO ids stay put.
    dict(races=[0x805, 0x806], npc_folder=None, ext='.wav', topics={
        'PowerAttack': [GD + f'atk_right_pwr_vox\\cr_ghostpeople_atk_right_vox_0{i}' for i in (1, 2, 3)]}),
    dict(races=[0x855, 0x856], npc_folder=None, ext='.wav', topics={
        'PowerAttack': [FG + f'vox_atk2\\npc_feralghoul_voxatk2_0{i}' for i in range(1, 8)]}),
    dict(races=[0x857], npc_folder=None, ext='.ogg', topics={
        'PowerAttack': [SMV + f'vdialogues_powerattack_{n}_1' for n in SM_PWR]}),
    dict(races=[0x858], npc_folder=None, ext='.ogg', topics={
        'PowerAttack': [NKV + f'vdialoguenightkin_attack_00152b{i:02x}_1' for i in range(0x67, 0x6A)]}),
] + [
    # TTW add-on races (PlayableCreaturesTTW.esp). Conditioned on a voice type defined HERE (GetIsVoiceType), not
    # on the race, so this plugin does not need PlayableCreaturesTTW.esp as a master; PlayableCreatures.dll gives the
    # player that voice type while in the race (ini VoiceType=PlayableCreaturesVoices.esp|<id>). Lines = the creatures'
    # own combat dialogue: Point Lookout's yokel voices (swampfolk), The Pitt's trog voice.
    dict(ttw=True, vtype=vt, races=rc, npc_folder=vt.lower(), ext='.ogg', topics={
        'Hit': [YK + vt_dir + f'dlc04genericswampfolk_hit_0000d9{i:02x}_1' for i in range(0x49, 0x5B)],
        'Death': [YK + vt_dir + f'dlc04gener_death_0000d8{i:02x}_1' for i in range(0xF5, 0xFD)],
        'PowerAttack': [YK + vt_dir + 'dlc04gener_powerattack_00011234_1', YK + vt_dir + 'dlc04gener_powerattack_00011235_1'],
        'Attack': [YK + vt_dir + f'dlc04gener_attack_0000d9{i:02x}_1' for i in range(0x14, 0x20)],
    }) for vt, vt_dir, rc in (('PCSwampfolkSmallVoice', 'dlc04maleyokelsmall\\', [0x8803, 0x8804]),       # Scrapper, Creeper
                              ('PCSwampfolkMediumVoice', 'dlc04maleyokelmedium\\', [0x8802]),             # Brawler
                              ('PCSwampfolkLargeVoice', 'dlc04maleyokellarge\\', [0x8805, 0x8806]))      # Tracker, Bruiser
] + [
    dict(ttw=True, vtype='PCTrogVoice', races=[0x8807, 0x8808, 0x8809], npc_folder='pctrogvoice', ext='.ogg', topics={
        'Hit': [TV + f'dlc01generictrog_hit_000080{i:02x}_1' for i in range(0x13, 0x21)],
        'Death': [TV + f'dlc01generictrog_death_000080{i:02x}_1' for i in range(0x77, 0x85)],
        'PowerAttack': [TV + f'dlc01generictrog_attack_000080{i:02x}_1' for i in range(0x42, 0x48)],
        'Attack': [TV + f'dlc01generictrog_attack_000080{i:02x}_1' for i in range(0x48, 0x54)],
    }),

] + [
    # Lonesome Road tunneler (PlayableCreatures.esp PCTunnelerRace): its CREA audio template (AudioTemplateSporeCarrier)
    # Hit / Death = the feral ghoul's injured / death sounds; PowerAttack = the spore carrier attack vocal
    dict(gen=7, vtype='PCTunnelerVoice', races=[0x8AC, 0x8CE], npc_folder='pctunnelervoice', ext='.wav', topics={
        'Hit': [FG + f'injured\\npc_feralghoul_injured_0{i}' for i in (1, 2, 3)],
        'Death': [FG + f'death\\npc_feralghoul_death_0{i}' for i in (1, 2, 3, 4)],
        'PowerAttack': [f'fx\\npc\\sporecarrier\\atk_vox\\npc_sporecarrier_atkvox_0{i}' for i in range(1, 8)],
    }),
] + [
    # Capital Wasteland super mutants (PlayableCreaturesTTW.esp): Fallout 3's own generic super mutant combat
    # lines (voice CreatureSuperMutantDC, TTW Fallout3 - Voices.bsa); Fawkes' companion lines left out
    dict(gen=8, ttw=True, vtype='PCSuperMutantDCVoice', races=[0x8877, 0x887A, 0x887D], npc_folder='pcsupermutantdcvoice', ext='.ogg', topics={
        'Hit': [SDC + 'genericsupermutant_hit_' + n + '_1' for n in ('0001f932', '0001f933', '0001f934', '0001f935', '0001f936', '000217f1', '000217f2',
                                                                    '000629b3', '000629b5', '000629b8', '000629bd', '000c73c2', '000c73c3', '000c73c4', '000c73c5')],
        'Death': [SDC + 'genericsupermutant_death_' + n + '_1' for n in ('000198a9', '000198ab', '00021804', '00021805', '00021806', '00029583', '00029584',
                                                                        '000629a2', '000629a3', '0009fa53', '000c73bd', '000c73be', '000c73bf', '000c73c0')],
        'PowerAttack': [SDC + 'genericsup_powerattack_' + n + '_1' for n in ('00021808', '00021809', '00062975', '00062976', '0006297b', '0006297c')],
        'Attack': [SDC + 'genericsupermutant_attack_' + n + '_1' for n in ('000198cd', '000198ce', '000198cf', '0001efae', '0001efaf', '0001f937', '0001f938',
                                                                          '000217f7', '000217f8', '000217f9', '00029585', '00029586', '00029587', '00029588')],
    }),
] + [
    # Eyebot (PlayableCreatures.esp PCEyebotRace 0x8E4): ED-E's beeps (vDialogueEDE's own combat lines use these
    # sounds: Attack = NPCRobotEdEAlertThreat, Hit = NPCRobotEdEAlertLowHealth); FalloutNV Fallout - Sound.bsa
    dict(gen=9, races=[0x8E4], npc_folder=None, ext='.wav', topics={
        'Hit': [ED + 'alert_lowhealth\\npc_ede_alert_lowhealth', ED + 'denied\\npc_ede_denied', ED + 'anger\\npc_ede_anger_01'],
        'Death': [ED + 'fail\\npc_ede_fail', ED + 'sad\\npc_ede_sad_01', ED + 'sad\\npc_ede_sad_02'],
        'PowerAttack': [ED + 'anger\\npc_ede_anger_01', ED + 'anger\\npc_ede_anger_02'],
        'Attack': [ED + 'confirmed\\npc_ede_confirmed_01', ED + 'confirmed\\npc_ede_confirmed_02', ED + 'seeking\\npc_ede_seeking'],
    }),    # Securitron Mk I / Mk II (PCSecuritronRace 0x8ED / PCSecuritronMkIIRace 0x8F1): FalloutNV's own securitron
    # combat lines (VDialogueSecuritron, voice RobotVictor; Fallout - Voices1.bsa). It has no PowerAttack lines -> its
    # Attack lines ("Hostile detected..."), which the engine doesn't voice for the player otherwise
    dict(gen=10, races=[0x8ED, 0x8F1], npc_folder=None, ext='.ogg', topics={
        'Hit': [RV + f'vdialoguesecuritron_hit_0015ef{i:02x}_1' for i in range(0x19, 0x1F)],
        'Death': [RV + f'vdialoguesecuritron_death_0015ef{i:02x}_1' for i in range(0x14, 0x17)],
        'PowerAttack': [RV + f'vdialoguesecuritron_attack_0015ee{i}_1' for i in ('df', 'e0', 'e1')],
        'Attack': [RV + f'vdialoguesecuritron_attack_0015ee{i}_1' for i in ('df', 'e0', 'e1')],
    }),
] + [
    # robots: FalloutNV's GenericRobot combat lines of each robot's voice type (Fallout - Voices1.bsa).
    # Hit = the shared "Bzzt" / "Vvvvzzz" lines (the protectron's own folder has no copy: the eyebot folder's); PowerAttack =
    # a few of its Attack lines (the engine voices the player's power attacks, not ordinary attacks).
    dict(gen=11, races=[race], npc_folder=None, ext='.ogg', **({'sex_ttw': 0} if race == 0x954 else {}), topics={
        'Hit': [GR(hit_folder, 'hit', i) for i in ('00080dde', '00080ddf', '00080de0', '00080de1', '00080de2', '00080de3')],
        'Death': [GR(folder, 'death', i) for i in death] + ([GR('roboteyebot', 'death', '00080dae')] if folder == 'robotprotectron' else []),
        'PowerAttack': [GR(folder, 'attack', i) for i in power],
        'Attack': [GR(folder, 'attack', i) for i in attack],
    }) for race, folder, hit_folder, death, power, attack in (
        (0x949, 'robotprotectron', 'roboteyebot', ('00081995', '00081996', '00081997'),
         ('00015a36', '0008199d', '000819b4', '000819a9'),
         ('00015a36', '0008199d', '000819a0', '000819a9', '000819aa', '000819ab', '000819ad', '000819b1', '000819b3', '000819b4')),
        (0x954, 'robotrobobrain', 'robotrobobrain', ('0008195a', '0008195b', '0008195c', '00080dae'),
         ('00081971', '0008196a', '00081968'),
         ('00081965', '00081966', '00081967', '00081969', '0008196a', '0008196b', '0008196d', '00081971', '00081973', '00081977')),
        (0x95E, 'robotmisterhandy', 'robotmisterhandy', ('000819d1', '000819d2', '000819d3'),
         ('00093622', '00093623', '0009361e'),
         ('0009361e', '0009361f', '00093620', '00093621', '00093622', '00093623', '00093624')),
        (0x968, 'robotmistergutsy', 'robotmistergutsy', ('0008304b', '0008304c', '0008304d'),
         ('00083035', '00083036', '0008303b'),
         ('0008302f', '00083030', '00083031', '00083033', '00083035', '00083036', '00083037', '00083038', '0008303b', '0008303d')),
        (0x96F, 'robotsentrybot', 'robotsentrybot', ('00080dab', '00080dac', '00080dad'),
         ('00080e13', '00080e03', '00080e01'),
         ('00080e01', '00080e02', '00080e03', '00080e04', '00080e05', '00080e10', '00080e12', '00080e13', '00080e15')))
] + [
    # Fallout 3's robobrain lines (voice RobotRoboBrainDC: the same
    # GenericRobot INFOs, other recordings - all 32 combat files differ from New Vegas'), TTW's Fallout3 - Voices.bsa
    # (sound\voice\falloutnv.esm\robotrobobraindc). TTW plugin only, female; the New Vegas set is male-only there.
    dict(gen=12, ttw=True, races=[0x954], sex=1, npc_folder=None, ext='.ogg', topics={
        'Hit': [GR('robotrobobraindc', 'hit', i) for i in ('00080dde', '00080ddf', '00080de0', '00080de1', '00080de2', '00080de3')],
        'Death': [GR('robotrobobraindc', 'death', i) for i in ('0008195a', '0008195b', '0008195c', '00080dae')],
        'PowerAttack': [GR('robotrobobraindc', 'attack', i) for i in ('00081971', '0008196a', '00081968')],
        'Attack': [GR('robotrobobraindc', 'attack', i) for i in ('00081965', '00081966', '00081967', '00081969', '0008196a',
                                                                  '0008196b', '0008196d', '00081971', '00081973', '00081977')],
    })
]

# ---- masters: every plugin that owns a quest in the merged topic lists, in load order, + PlayableCreatures.esp
order = T['order']
if MERGED:
    masters = os.environ['PC_MASTERS'].split(',')
    assert masters[0] == 'FalloutNV.esm', masters
    MIDX = {m.lower(): i for i, m in enumerate(masters)}
    for t in T['topics'].values():                       # quests of plugins that aren't masters are left out
        t['quests'] = [q for q in t['quests'] if q[0].lower() in MIDX]
    SELF = len(masters) << 24
    PC = SELF                                            # the races are in the same plugin
else:
    need = {'falloutnv.esm'} | {q[0].lower() for t in T['topics'].values() for q in t['quests']}
    masters = [p for p in order if p.lower() in need] + ['PlayableCreatures.esp']
    assert masters[0].lower() == 'falloutnv.esm' and 'PlayableCreatures.esp' in order
    MIDX = {m.lower(): i for i, m in enumerate(masters)}
    SELF = len(masters) << 24
    PC = MIDX['playablecreatures.esp'] << 24
def gfid(plugin, local): return (MIDX[plugin.lower()] << 24) | local
def wanted(v): return SETS == 'all' or not v.get('ttw')

next_id = [ID_BASE]
def new_id():
    v = SELF | next_id[0]; next_id[0] += 1; return v

quest_fid = new_id()
quest = record('QUST', quest_fid, [('EDID', z(QUEST_EDID)), ('FULL', z('Playable Creatures Voices')),
                                   ('DATA', struct.pack('<BBHf', 0x11, 110, 0, 0.0))])   # start game enabled, priority 110 (> GenericPlayer 101)

def ctda(func, form, OR=False):
    return struct.pack('<B3sfHHIIII', 0x01 if OR else 0, b'\0\0\0', 1.0, func, 0, form, 0, 0, 0)
def ctda_voice(vt_fid):
    # type/operator 0 (==, AND), comparison 1.0, function, pad, param1, param2, run on subject, reference
    return struct.pack('<B3sfHHIIII', 0, b'\0\0\0', 1.0, GET_IS_VOICE_TYPE, 0, vt_fid, 0, 0, 0)
SCHR = bytes.fromhex('0000000000000000000000000000000000000100')
TRDT = struct.pack('<IiIB3sIB3s', 0, 50, 0, 1, b'\0\0\0', 0, 1, b'\0\0\0')

ids = {}; vtypes = {}
# ids are allocated per generation ('gen', default 6): INFOs of that generation, then its new voice types - so the
# ids of every earlier plugin version stay where they were (INFOs 801-8FD, VTYPs 8FE-901; later generations append after)
for g in sorted({v.get('gen', 6) for v in VOICES}):
    for vi, v in enumerate(VOICES):
        if v.get('gen', 6) != g: continue
        for topic in TOPICS:
            for i, _ in enumerate(v['topics'].get(topic, [])): ids[(vi, topic, i)] = new_id()
    for v in VOICES:
        if v.get('gen', 6) == g and v.get('vtype') and v['vtype'] not in vtypes: vtypes[v['vtype']] = new_id()
vt_wanted = {v['vtype'] for v in VOICES if v.get('vtype') and wanted(v)}
vtyp_recs = [record('VTYP', fid, [('EDID', z(e)), ('DNAM', bytes([0]))]) for e, fid in vtypes.items() if e in vt_wanted]
dial_groups = []; plan = []; n_info = 0
for topic, tfid in TOPICS.items():
    t = T['topics'][topic]
    last = {k: bytes.fromhex(v) for k, v in t['last'].items()}
    quests = [gfid(p, l) for p, l in t['quests']] + [quest_fid]
    subs = [('EDID', last['EDID'])] + [('QSTI', u32(q)) for q in quests]
    for k in ('FULL', 'PNAM', 'TDUM', 'DATA'):
        if k in last: subs.append((k, last[k]))
    dial = record('DIAL', tfid, subs)                     # FalloutNV.esm is master 0, so the id stays 000000xx
    infos = []
    for vi, v in enumerate(VOICES):
        if not wanted(v): continue
        files = v['topics'].get(topic, [])
        for i, src in enumerate(files):
            fid = ids[(vi, topic, i)]
            flags = 0x0002 | (0x0020 if i == len(files) - 1 else 0)          # Random (+ Random End on the last)
            infos.append(record('INFO', fid, [
                ('DATA', struct.pack('<BBH', 2, 0, flags)), ('QSTI', u32(quest_fid)), ('TRDT', TRDT),
                ('NAM1', z(' ')), ('NAM2', z('')), ('NAM3', z('')),
                # GetIsRace whenever the set lists its races: GetIsVoiceType never matched the player (TTW super
                # mutants / swampfolk / trogs / tunneler silent; the NPC voice type given by the DLL doesn't count)
                *([('CTDA', ctda(GET_IS_RACE, PC | r, OR=(k < len(v['races']) - 1))) for k, r in enumerate(v['races'])] if v.get('races') else
                  [('CTDA', ctda_voice(vtypes[v['vtype']]))]),
                # GetIsSex: a set for one sex (in the TTW plugin, where the Robobrain has a female set too)
                *([('CTDA', ctda(GET_IS_SEX, v['sex']))] if v.get('sex') is not None else
                  [('CTDA', ctda(GET_IS_SEX, v['sex_ttw']))] if v.get('sex_ttw') is not None and SETS == 'all' else []),
                ('SCHR', SCHR), ('NEXT', b''), ('SCHR', SCHR)]))
            # the player speaks with PlayerVoiceMale / PlayerVoiceFemale whatever its NPC voice type says (Actor::Say
            # looks in ...\\PlayerVoiceMale\\...), NPCs of the race with the race's voice type
            for folder in ['playervoicemale', 'playervoicefemale'] + ([v['npc_folder']] if v['npc_folder'] else []):
                base = f"sound\\voice\\{ESP_NAME.lower()}\\{folder}\\{QUEST_EDID.lower()}_{topic.lower()}_{fid & 0xFFFFFF:08x}_1"
                plan.append((src + v['ext'], base + v['ext']))
            n_info += 1
    child = b'GRUP' + struct.pack('<IIiHHHH', 24 + sum(len(x) for x in infos), tfid, 7, 0, 0, 0, 0) + b''.join(infos)
    dial_groups.append(dial + child)

groups = [group('QUST', [quest])] + ([group('VTYP', vtyp_recs)] if vtyp_recs else [])
dial_top = b''.join(dial_groups)
groups.append(b'GRUP' + struct.pack('<I4sIIHH', 24 + len(dial_top), b'DIAL', 0, 0, 0, 0) + dial_top)
nrec = 1 + len(vtyp_recs) + len(TOPICS) + n_info + len(groups) + len(TOPICS)   # quest + vtyps + dials + infos + groups + child groups
hdr = [('HEDR', struct.pack('<fII', 1.34, nrec, next_id[0])), ('CNAM', z('Claude (Playable Creatures project)')),
       ('SNAM', z('Playable Creatures: creature voice sets as combat dialogue (merged topic quest lists for this load order)'))]
for m in masters: hdr += [('MAST', z(m)), ('DATA', struct.pack('<Q', 0))]
open(OUT, 'wb').write(record('TES4', 0, hdr) + b''.join(groups))
open(PLAN, 'w').write(''.join(f'{a}\t{b}\n' for a, b in plan))
print('wrote', OUT, 'masters', masters, 'infos', n_info, 'next id %03X' % next_id[0])
for e, fid in vtypes.items(): print('  voice type', e, '%06X' % (fid & 0xFFFFFF))
