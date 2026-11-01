"""Builds a creature's complete weapon animation sets (Playable Creatures).
usage: python3 build_creature.py <creature config name> <out dir>
Sources, in order of preference (never human motion):
  1. the creature's own files, reused under another weapon prefix (aims / equip / unequip / holster)
  2. the creature's own animations with the off hand pinned to the weapon by IK (two-handed melee)
  3. procedural motion on the creature's own skeleton and aim pose (reloads, jams, recoil, automatic
     fire, spin-up, throws, mine placement)
Timing and text keys (Hit, a:, Release, Hold, Attach, Fire, Loop, Sound:...) come from the vanilla/TTW
human file of the same group, so each weapon keeps its engine events and sounds.
Groups the creature already has are never regenerated; its own files are never overwritten."""
import sys, os, json, glob, struct, importlib, re, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from rig import Creature, Rig, Plan, pose, sample, write_kf, offhand_overlay, offhand_release
from kf import KF
from nifedit import NifFile
import motions as M

cfg = importlib.import_module('creatures.' + sys.argv[1])
OUT = sys.argv[2]
os.makedirs(OUT, exist_ok=True)
cr = Creature(cfg)
HERE = os.path.dirname(os.path.abspath(__file__))
HK = {}
for j in ('human_reload_keys.json', 'human_weapon_keys.json'):
    for k, v in json.load(open(os.path.join(HERE, j))).items():
        if not k.startswith('loco/'): HK[k] = v

VARS = [('', ''), ('up', 'Up'), ('down', 'Down'), ('is', 'IS'), ('isup', 'ISUp'), ('isdown', 'ISDown')]
PLAIN = 'ABCDEFGHIJKLMNOPQRS'; LOOP = 'WXYZ'
PREFIXES = ['h2h', '1hm', '2hm', '1hp', '2hr', '2ha', '2hh', '2hl', '1gt', '1md', '1lm']

# ---- what the creature already has: (prefix, group) from its own files ----
own_files = {}
own_groups = set()
for f in glob.glob(os.path.join(cfg.ANIM_SRC, '**', '*.kf'), recursive=True):
    rel = os.path.relpath(f, cfg.ANIM_SRC).replace(os.sep, '\\').lower()
    if rel.startswith('idleanims'): continue
    own_files[rel] = f
    base = os.path.basename(rel)
    m = re.match(r'^(sneak|swim|fly)?(' + '|'.join(PREFIXES) + ')?', base)
    pre = (m.group(1) or '') + (m.group(2) or '')
    own_groups.add((pre, KF(f).name.lower()))
def has(prefix, group): return (prefix, group.lower()) in own_groups
def prefix_of(name):
    m = re.match(r'^(sneak|swim|fly)?(' + '|'.join(PREFIXES) + ')?', name.replace('\\', '/').split('/')[-1])
    return (m.group(1) or '') + (m.group(2) or '')
def register(n, path, seq):
    """a generated file that later steps may use like one of the creature's own"""
    own_files[n] = path; own_groups.add((prefix_of(n), seq.lower())); cr.extra[n] = path
NATIVE = {k: list(v) for k, v in cfg.NATIVE.items()}

manifest = []; written = set()
def outname(name):
    n = name.lower()
    if n in own_files or n in written: n = n[:-3] + '_pc.kf'
    written.add(n); return os.path.join(OUT, n), n

def clean_keys(ks, L):
    out = []
    for t, s in ks:
        s = s.replace('\r', '').replace('\n', '').rstrip()
        if not s or s.startswith(' -') or s.startswith('-'): continue
        out.append((min(max(t, 0.0), L), s))
    return out

def keys_for(fname, fallback, dlen, dkeys):
    """human timing/keys for `fname` (or the first existing fallback); else defaults"""
    for f in [fname] + list(fallback):
        h = HK.get(f)
        if h:
            L = h['len']; ks = clean_keys(h['keys'], L)
            if not any(s == 'start' for _, s in ks): ks = [(0.0, 'start')] + ks
            if not any(s == 'end' for _, s in ks): ks = ks + [(L, 'end')]
            return L, sorted(ks, key=lambda x: x[0]), f
    return dlen, dkeys, None

def keyt(ks, name, L, default):
    for t, s in ks:
        if s.lower() == name.lower(): return t / L
    return default

rigs = {}
def rig_for(src, vi):
    kfname = NATIVE[src][vi]
    if kfname not in rigs: rigs[kfname] = Rig(cr, kfname)
    return rigs[kfname]

def emit_proc(prefix, fname, seq, rig, plan_fn, dlen, dkeys, fallback=(), cycle=2, priority=65):
    L, ks, src = keys_for(fname, fallback, dlen, dkeys)
    path, n = outname(fname)
    write_kf(cr, path, seq, L, ks, sample(rig, plan_fn(L, ks), L), priority=priority, cycle=cycle)
    manifest.append(f'{n}\t{seq}\t{L:.2f}s\tprocedural\tkeys:{src or "default"}')

def copy_own(src_rel, prefix_from, prefix_to, why):
    base = os.path.basename(src_rel)
    new = base.replace(prefix_from, prefix_to, 1)
    path, n = outname(new)
    shutil.copyfile(own_files[src_rel], path)
    seq = KF(path).name; register(n, path, seq)
    manifest.append(f'{n}\t{seq}\t\tcreature own ({src_rel}){why}')

def renamed_copy(src_rel, new_name, seq):
    f = NifFile(own_files[src_rel])
    bi = [i for i, t in enumerate(f.btype) if f.types[t] == 'NiControllerSequence'][0]
    b = bytearray(f.blocks[bi]); struct.pack_into('<i', b, 0, f.str_index(seq)); f.blocks[bi] = bytes(b)
    path, n = outname(new_name)
    open(path, 'wb').write(f.to_bytes())
    manifest.append(f'{n}\t{seq}\t\tcreature own ({src_rel}, renamed)')

def add_key(ks, t, s): return sorted(ks + [(t, s)], key=lambda x: x[0])

# 0) synthetic aims for weapon types the creature has no hold for: its own standing pose with the weapon
#    arm (and optionally the off hand) solved by IK to a weapon frame in front of the torso
def synth_aims(T, sp):
    base = Rig(cr, sp['base'])
    wp = base.W0[cr.torso][0] + np.asarray(sp['wpos'], float)
    barrel = np.asarray(sp.get('barrel', (0, 1, 0)), float); up = np.asarray(sp.get('up', (0, 0, 1)), float)
    base.W0[cr.weapon] = (wp, np.column_stack([barrel, up, np.cross(barrel, up)]))
    lh = ('weapon', sp['grip']) if sp.get('grip') is not None else ('base',)
    loc0 = pose(base, Plan([(0, dict(lhand=lh, curl=sp.get('curl', 0)))]), 0)
    hold = Rig(cr, base_pose={k: v for k, v in loc0.items()})
    names = []
    for vi, (fs, ss) in enumerate(VARS):
        v = dict(sp['variants'][vi]); v.setdefault('lhand', lh); v.setdefault('curl', 0)   # the hold already carries sp['curl'] (was applied twice)
        loc = pose(hold, Plan([(0, v)]), 0)
        name = f'{T}aim{fs}.kf'
        path, n = outname(name)
        write_kf(cr, path, 'Aim' + ss, 2.0, [(0.0, 'start'), (2.0, 'end')], [(0.0, loc), (2.0, loc)],
                 priority=sp.get('priority', 45), cycle=0)
        register(n, path, 'Aim' + ss); rigs[n] = Rig(cr, base_pose=loc); names.append(n)
        manifest.append(f'{n}\tAim{ss}\t2.00s\tsynthetic hold on the creature\'s own pose ({sp["base"]})')
    NATIVE[T] = names

for T, spec in cfg.WEAPON_TYPES.items():
    if spec.get('synth'): synth_aims(T, spec['synth'])

for T, spec in cfg.WEAPON_TYPES.items():
    src = spec.get('src', T); fam = spec.get('family')
    # 1) reuse the creature's own aims / equip / unequip / holster under the new prefix
    reuse_aims = spec.get('reuse_aims', not (spec.get('thrown') or spec.get('mine') or spec.get('melee2')))
    what_src = 'aim|equip|unequip|holster' + ('|attack|recoil' if spec.get('copy_attacks') else '')
    for frm, what in ((src, what_src), (spec.get('equip_from'), 'equip|unequip|holster')):
        if not frm or frm == T: continue
        for rel in sorted(own_files):
            base = os.path.basename(rel)
            if '\\' in rel: continue
            m = re.match(r'^(sneak)?' + frm + r'(' + what + r')', base)
            if not m: continue
            if m.group(2) == 'aim' and not reuse_aims: continue
            if has(prefix_of(base.replace(frm, T, 1)), KF(own_files[rel]).name): continue
            copy_own(rel, frm, T, '')
    # 1b) one-handed use of the creature's own two-handed set: off arm hangs free
    if spec.get('release_from'):
        R2 = spec['release_from']
        for rel in sorted(own_files):
            base = os.path.basename(rel)
            if '\\' in rel or not re.match(r'^' + R2 + r'(aim|attack)', base): continue
            k0 = KF(own_files[rel])
            if has(T, k0.name): continue
            frames, bones, k = offhand_release(cr, rel)
            pr = dict(bones); arm_pr = max([p for n2, p in bones if ' R ' in n2] or [55])
            bl = bones + [(n2, arm_pr) for n2 in cr.arm['L'] + cr.fingers['L'] if n2 not in pr]
            path, n = outname(base.replace(R2, T, 1))
            write_kf(cr, path, k.name, k.stop, list(k.textkeys), frames, bones=bl, cycle=k.cycle)
            register(n, path, k.name)
            manifest.append(f'{n}\t{k.name}\t{k.stop:.2f}s\tcreature own ({rel}) with the off arm free')
    # 1c) missing power attacks: the creature's own power swing under the other power-attack names
    if spec.get('power_src') and spec['power_src'] in own_files:
        for g in ('AttackPower', 'AttackForwardPower', 'AttackBackPower', 'AttackLeftPower', 'AttackRightPower'):
            if not has(T, g): renamed_copy(spec['power_src'], f'{T}{g.lower()}.kf', g)
    # 2) ranged: attacks the creature lacks, automatic fire loop, spin-up, reloads, jams
    if spec.get('ranged'):
        groups = ['Attack3', 'Attack4', 'AttackLeft', 'AttackRight', 'AttackLoop', 'AttackSpin', 'AttackSpin2']
        for g in groups:
            for vi, (fs, ss) in enumerate(VARS):
                seq = g + ss
                if has(T, seq): continue
                rig = rig_for(src, vi)
                fname = f'{T}{seq.lower()}.kf'
                base_f = f'{T}{g.lower()}.kf'
                fb = [base_f, f'2ha{seq.lower()}.kf', f'2ha{g.lower()}.kf']
                if g == 'AttackLoop':
                    emit_proc(T, fname, seq, rig, lambda L, k: M.fire_loop(fam, cfg), 0.1667,
                              [(0, 'start'), (0.0333, 'BlendIn:1'), (0.1667, 'end')], fb, cycle=0, priority=55)
                elif g.startswith('AttackSpin'):
                    emit_proc(T, fname, seq, rig, lambda L, k: M.spin(fam, cfg, keyt(k, 'Fire', L, .4)), 0.3333,
                              [(0, 'start'), (0.0333, 'Blend:2'), (0.1333, 'Fire'), (0.3, 'Loop'), (0.3333, 'end')],
                              fb + [f'2hh{g.lower()}.kf'], priority=55)
                else:
                    tag = {'Attack3': 'a:3', 'Attack4': 'a:4', 'AttackLeft': 'a:L', 'AttackRight': 'a:R'}[g]
                    emit_proc(T, fname, seq, rig, lambda L, k: M.recoil(fam, cfg, keyt(k, 'Hit', L, .06)), 0.5667,
                              [(0, 'start'), (0.0333, 'Hit'), (0.1667, tag), (0.2333, 'BlendIn:1'), (0.5667, 'end')],
                              fb, priority=55)
        rig = rig_for(src, 0)
        # groups the creature already has (e.g. Super Mutant 2HA ReloadA/E/F) are kept, never duplicated
        for Lt in PLAIN:
            if not has(T, f'Reload{Lt}'):
                emit_proc(T, f'{T}reload{Lt.lower()}.kf', f'Reload{Lt}', rig, lambda L, k: M.magazine(fam, cfg), 2.0,
                          [(0, 'start'), (0.0333, 'Blend:3'), (2.0, 'end')])
            if not has(T, f'Jam{Lt}'):
                emit_proc(T, f'{T}jam{Lt.lower()}.kf', f'Jam{Lt}', rig, lambda L, k: M.jam(fam, cfg), 1.4,
                          [(0, 'start'), (0.0333, 'Blend:3'), (1.4, 'end')])
        for Lt in LOOP:
            if not has(T, f'Reload{Lt}Start'):
                emit_proc(T, f'{T}reload{Lt.lower()}start.kf', f'Reload{Lt}Start', rig, lambda L, k: M.loop_start(fam, cfg), 0.9,
                          [(0, 'start'), (0.9, 'end')])
            if not has(T, f'Reload{Lt}'):
                emit_proc(T, f'{T}reload{Lt.lower()}.kf', f'Reload{Lt}', rig,
                          lambda L, k: M.loop_step(fam, cfg, keyt(k, 'Hit', L, .45)), 1.6, [(0, 'start'), (0.7, 'Hit'), (1.6, 'end')])
            if not has(T, f'Jam{Lt}'):
                emit_proc(T, f'{T}jam{Lt.lower()}.kf', f'Jam{Lt}', rig, lambda L, k: M.jam(fam, cfg), 1.4,
                          [(0, 'start'), (0.0333, 'Blend:3'), (1.4, 'end')])
    # 3) one-handed melee: power attacks from the creature's own chop swing
    if spec.get('melee'):
        chop = f'{src}attackright_chop.kf'
        for g in ('AttackPower', 'AttackForwardPower', 'AttackBackPower', 'AttackLeftPower', 'AttackRightPower'):
            if not has(T, g) and chop in own_files: renamed_copy(chop, f'{T}{g.lower()}.kf', g)
    # 4) two-handed melee: the creature's own one-handed set with the off hand on the handle
    if spec.get('melee2'):
        grip = spec['grip']
        def overlay(src_rel, new_name, seq, keys=None, cycle=None, extra=()):
            frames, bones, k = offhand_overlay(cr, src_rel, grip)
            pr = dict(bones)
            arm_pr = max([p for n, p in bones if ' R ' in n] or [55])
            bl = bones + [(n, arm_pr) for n in cr.arm['L'] + cr.fingers['L'] if n not in pr]
            ks = list(keys if keys is not None else k.textkeys)
            for t, s in extra: ks = add_key(ks, t, s)
            path, n = outname(new_name)
            write_kf(cr, path, seq, k.stop, ks, frames, bones=bl, cycle=k.cycle if cycle is None else cycle)
            manifest.append(f'{n}\t{seq}\t{k.stop:.2f}s\tcreature own ({src_rel}) + off-hand IK')
        overlay(f'{src}aim.kf', f'{T}aim.kf', 'Aim')
        for rel in sorted(own_files):
            base = os.path.basename(rel)
            if '\\' in rel or not base.startswith(src + 'attack'): continue
            k = KF(own_files[rel])
            hit = keyt(k.textkeys, 'Hit', k.stop, .5) * k.stop
            overlay(rel, base.replace(src, T, 1), k.name, extra=[(max(0.0, hit - 0.2), 'Sound: FXSwing2hm')])
        chop = f'{src}attackright_chop.kf'
        if chop in own_files:
            k = KF(own_files[chop]); hit = keyt(k.textkeys, 'Hit', k.stop, .5) * k.stop
            for g in ('AttackPower', 'AttackForwardPower', 'AttackBackPower', 'AttackLeftPower', 'AttackRightPower'):
                overlay(chop, f'{T}{g.lower()}.kf', g, extra=[(max(0.0, hit - 0.2), 'Sound: FXSwing2hm')])
    # 5) thrown weapons / mines: chest hold, throws, placing
    if spec.get('thrown') or spec.get('mine'):
        for vi, (fs, ss) in enumerate(VARS):
            rig = rig_for(src, vi)
            if not has(T, 'Aim' + ss):
                emit_proc(T, f'{T}aim{fs}.kf', 'Aim' + ss, rig, lambda L, k: M.hold(cfg), 2.0,
                          [(0, 'start'), (2.0, 'end')], cycle=0, priority=55)
            if spec.get('thrown'):
                for i in ('', '2', '3', '4', '5', '6', '7', '8'):
                    g = f'AttackThrow{i}'; fname = f'{T}{g.lower()}{fs}.kf'
                    if has(T, g + ss): continue
                    emit_proc(T, fname, g + ss, rig,
                              lambda L, k: M.throw(cfg, keyt(k, 'Hold', L, .33), keyt(k, 'Release', L, .51)), 1.7,
                              [(0, 'start'), (0.0333, 'Blend:3'), (0.5667, 'Hold'), (0.8667, 'Release'), (1.5333, 'Attach'), (1.7, 'end')],
                              [f'{T}{g.lower()}.kf', '1gtattackthrow.kf'])
            else:
                for i in ('', '2'):
                    g = f'PlaceMine{i}'; fname = f'{T}{g.lower()}{fs}.kf'
                    if has(T, g + ss): continue
                    emit_proc(T, fname, g + ss, rig, lambda L, k: M.place(cfg, keyt(k, 'Release', L, .5)), 3.0667,
                              [(0, 'start'), (0.0333, 'BlendIn:3'), (1.5, 'Release'), (2.6333, 'Attach'), (3.0667, 'end')],
                              [f'{T}{g.lower()}.kf', f'{T}placemine.kf', '1lmplacemine.kf'])

# 6) jumps: airborne tuck / landing on the creature's own legs (weapon aims override the arms)
if getattr(cfg, 'IDLE_KF', None):
    import jumps as J
    JREF = getattr(cfg, 'HUMAN_JUMP_REF', '/home/claude/fnv/ref_weap')
    for g, jrig, K, cyc in J.build(cr):
        if has('', g): continue
        fname = f'mt{g.lower()}.kf'; rp = os.path.join(JREF, fname)
        if os.path.exists(rp):
            hk = KF(rp); L = hk.stop; ks = clean_keys(hk.textkeys, L); src = fname
        else:
            L = J.DEFAULT_LEN.get(g, 2.1 if 'Loop' in g else 0.5); ks = [(0.0, 'start'), (L, 'end')]; src = None
        nf = max(2, int(round(L * 30)) + 1)
        frames = [(L * i / (nf - 1), J.jump_pose(jrig, K.at(i / (nf - 1)))) for i in range(nf)]
        path, n = outname(fname)
        write_kf(cr, path, g, L, ks, frames, bones=J.jump_bones(cr), cycle=cyc)
        manifest.append(f'{n}\t{g}\t{L:.2f}s\tprocedural jump\tkeys:{src or "default"}')

# 7) sneak: crouched versions of the creature's own idle/locomotion, and the stance-independent groups
#    (aims, attacks, reloads, equips, throws, jumps...) under the sneak prefix, because the engine does not
#    fall back from a missing sneak group to the standing one (the player cannot move / act while sneaking)
if getattr(cfg, 'SNEAK', True):
    import sneak as SN
    LOCO = {'idle', 'forward', 'backward', 'left', 'right', 'turnleft', 'turnright',
            'fastforward', 'fastbackward', 'fastleft', 'fastright'}
    def emit_crouch(src_rel, name, seq=None, timescale=1.0):
        frames, bones, L, keys, cyc, sname = SN.crouch_frames(cr, own_files[src_rel], timescale)
        seq = seq or sname
        path, n = outname(name)
        write_kf(cr, path, seq, L, keys, frames, bones=bones, cycle=cyc)
        register(n, path, seq)
        manifest.append(f'{n}\t{seq}\t{L:.2f}s\tcreature own ({src_rel}) crouched')
    loco_src = {}
    for rel in sorted(own_files):
        if rel.startswith('idleanims') or prefix_of(rel) != '': continue
        g = KF(own_files[rel]).name.lower()
        if g in LOCO and g not in loco_src: loco_src[g] = rel
    for g, rel in sorted(loco_src.items()):
        if not has('sneak', g): emit_crouch(rel, f'sneakmt{g}.kf')
    if not has('sneak', 'fastforward') and 'forward' in loco_src:
        emit_crouch(loco_src['forward'], 'sneakmtfastforward.kf', seq='FastForward', timescale=1.5)
    n_copy = 0
    for rel in sorted(own_files):
        base = os.path.basename(rel)
        if '\\' in rel or base.startswith('sneak'): continue
        pre = prefix_of(base); seq = KF(own_files[rel]).name
        if seq.lower() in LOCO or seq.lower().startswith('specialidle') or seq.lower() == 'death': continue
        if has('sneak' + pre, seq): continue
        path, n = outname('sneak' + base)
        shutil.copyfile(own_files[rel], path); register(n, path, seq); n_copy += 1
    for n0 in sorted(written):
        if n0.startswith('sneak'): continue
        path0 = os.path.join(OUT, n0); pre = prefix_of(n0)
        seq = KF(path0).name
        if seq.lower() in LOCO or has('sneak' + pre, seq): continue
        path, n = outname('sneak' + n0)
        shutil.copyfile(path0, path); register(n, path, seq); n_copy += 1
    manifest.append(f'(sneak copies of stance-independent groups: {n_copy})')
    print('sneak copies', n_copy)

# ---- post-process ----------------------------------------------------------------------------
import weaponparts as WP
REF = getattr(cfg, 'HUMAN_REF', os.path.join(HERE, '..', 'ref_male'))
refs = set(os.listdir(REF)) if os.path.isdir(REF) else set()
wp_n = 0
for n in sorted(written):
    m = re.match(r'^(sneak)?(' + '|'.join(PREFIXES) + ')', n)
    if not m or m.group(2) == 'h2h': continue
    T = m.group(2); h = n.replace('_pc.kf', '.kf')
    cands = [h, h[5:] if h.startswith('sneak') else None]
    if not re.search(r'reload|jam', h): cands.append(f'{T}aim.kf')
    src = next((c for c in cands if c and c in refs), None)
    if src:
        wp_n += WP.merge(os.path.join(OUT, n), os.path.join(REF, src), keep_loose_transforms=not re.search(r'reload|jam', h))
print('weapon-part tracks added:', wp_n)
for T, spec in cfg.WEAPON_TYPES.items():
    if spec.get('weapon_rot') is None: continue
    k = 0
    for n in sorted(written):
        if re.match(r'^(sneak)?' + T, n): k += WP.rotate_node(os.path.join(OUT, n), cr.weapon, spec['weapon_rot'])
    print(T, 'weapon node re-oriented in', k, 'tracks')

open(os.path.join(OUT, 'weaponsets_manifest.txt'), 'w').write('\n'.join(manifest) + '\n')
print(len(manifest), 'files ->', OUT)
