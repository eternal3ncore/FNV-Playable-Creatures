"""Lonesome Road Tunneler skeleton folder (meshes\\PlayableCreatures\\Tunneler\\), built on the finished Trog set.
FNV's creatures\\NVSporeCarrier\\skeleton.nif (Spore Carrier + Tunneler) is the street trog's skeleton: same 57 bones,
hierarchy and bind pose (verified); its animations are the trog's with spore-carrier text keys, a reworked
AttackLeft / AttackLeftPower, an extra AttackBackPower and its own get-ups.
  * base: the deployed Trog folder (melee only, hinge-fixed): sneak locomotion, crab / backward runs, jumps from the
    leap, furniture;
  * the creature's own files (vanilla nvsporecarrier: idle, locomotion, hurt locomotion, H2H set) replace the trog's,
    Enum keys -> Sound keys (AudioTemplateSporeCarrier);
  * melee only (as the trog): H2H up / down from the regular pose (fill_updown), 1HM / 2HM = its H2H set with the
    vanilla weapon-part tracks merged in (switchblade, baton, chainsaw...), sneak copies;
  * the trog's Sound keys left in the shared files are mapped to the spore-carrier SOUNs.
usage: python3 build_tunneler.py <trog folder> <nvsporecarrier src> <out folder> <skeleton.nif>"""
import sys, os, re, shutil, glob, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import enum_keys as EK, fill_updown as FU, weaponparts as WP
from nifedit import NifFile
TROG, SPORE, OUT, SKEL = sys.argv[1:5]
REF = '/home/claude/fnv/ref_male'; refs = set(os.listdir(REF))
SOUND_MAP = {'NPCTrogFootLeft': 'NPCSporeCarrierFootLeft', 'NPCTrogFootRight': 'NPCSporeCarrierFootRight',
             'NPCTrogFootRunLeft': 'NPCSporeCarrierFootRunLeft', 'NPCTrogFootRunRight': 'NPCSporeCarrierFootRunRight'}
MELEE = re.compile(r'^(sneak)?(h2h|1hm|2hm)')
if os.path.isdir(OUT): shutil.rmtree(OUT)
os.makedirs(OUT)
def cp(a, b): os.makedirs(os.path.dirname(b), exist_ok=True); shutil.copyfile(a, b)
n = dict(trog=0, own=0, derived=0, sneak=0)
# 1) trog base without its melee sets
for d, _, fs in os.walk(TROG):
    if '_disabled' in d: continue
    for f in fs:
        rel = os.path.relpath(os.path.join(d, f), TROG)
        if rel == 'Skeleton.nif' or (os.sep not in rel and MELEE.match(f.lower())): continue
        cp(os.path.join(d, f), os.path.join(OUT, rel)); n['trog'] += 1
# 2) the creature's own files
for f in glob.glob(SPORE + '/*.kf'): cp(f, os.path.join(OUT, os.path.basename(f))); n['own'] += 1
for f in glob.glob(SPORE + '/locomotion/*.kf'): cp(f, os.path.join(OUT, 'Locomotion', os.path.basename(f))); n['own'] += 1
for f in glob.glob(SPORE + '/locomotion/hurt/*.kf'): cp(f, os.path.join(OUT, 'Locomotion', 'Hurt', os.path.basename(f))); n['own'] += 1
cp(SPORE + '/deathposes.psa', os.path.join(OUT, 'DeathPoses.psa')); cp(SKEL, os.path.join(OUT, 'Skeleton.nif'))
# 3) H2H up / down, 1HM / 2HM from H2H, sneak copies
FU.run(OUT)
for f in sorted(os.listdir(OUT)):
    if not f.lower().startswith('h2h') or not f.endswith('.kf'): continue
    for T in ('1hm', '2hm'):
        nf = T + f[3:]; p = os.path.join(OUT, nf); shutil.copyfile(os.path.join(OUT, f), p); n['derived'] += 1
        src = next((c for c in (nf.lower(), f'{T}aim.kf') if c in refs), None)
        if src: WP.merge(p, os.path.join(REF, src), keep_loose_transforms=True)
for f in sorted(os.listdir(OUT)):
    if MELEE.match(f.lower()) and not f.lower().startswith('sneak') and f.endswith('.kf'):
        shutil.copyfile(os.path.join(OUT, f), os.path.join(OUT, 'sneak' + f)); n['sneak'] += 1
# 4) sounds: Enum -> spore carrier SOUNs; trog Sound keys -> spore carrier
conv = remap = 0
for d, _, fs in os.walk(OUT):
    for f in fs:
        if not f.endswith('.kf'): continue
        p = os.path.join(d, f)
        r = EK.convert(p, EK.MAPS['sporecarrier'])
        if r: open(p, 'wb').write(r[0].to_bytes()); conv += 1
        nif = NifFile(p); i, name, keys = EK.text_keys(nif)
        if i is None: continue
        new = [(t, ('Sound: ' + SOUND_MAP[s.split(':', 1)[1].strip()]) if s.lower().startswith('sound:') and s.split(':', 1)[1].strip() in SOUND_MAP else s) for t, s in keys]
        if new != keys:
            nif.blocks[i] = struct.pack('<iI', name, len(new)) + b''.join(struct.pack('<fi', t, nif.str_index(s)) for t, s in new)
            open(p, 'wb').write(nif.to_bytes()); remap += 1
total = sum(len(fs) for _, _, fs in os.walk(OUT))
print(n, 'enum-converted', conv, 'trog sounds remapped', remap, 'total files', total)
