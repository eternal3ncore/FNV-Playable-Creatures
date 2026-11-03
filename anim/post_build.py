"""post_build.py: the fixes made after the race sets were built, as one repeatable step, so a rebuild of
a race folder doesn't lose them. Run after build_creature.py / build_robot.py / build_securitron.py / build_eyebot.py
(and their own post passes listed in README) on the finished folder, before deploying.
usage: python3 -P post_build.py <race folder> <race>     race = the folder name in meshes\\PlayableCreatures

  1. human weapon transfer (xfer_human: own torso, human hands / fingers / Weapon node, weapon-part tracks incl.
     magazines; two-handed types turn the spine into the human stance) - Ghost 2HA / 2HR / 2HH / 2HL (its 1HP transfer
     and the Weapon-node fix that follows it are run by hand if the Ghost set is rebuilt),
     Ghoul / Glowing One / Hillfolk 2HA / 2HR / 2HH / 2HL (synthetic rifle holds before)
  2. aimed (IS) attacks time-warped onto the hip attack's timing (retime_is) - Super Mutant, Nightkin, Swampfolk, Zetan
  3. Eyebot sneak hover lowered 40 (sneak_lower)
  4. block animations (H2H + 1HM / 2HM shared): humanoids = human blocks transferred (block_xfer); robots, Eyebot,
     Securitron, Trog, Tunneler, Deathclaw = own guard (own_block); Mister Handy / Gutsy = their claw 1HM blocks copied
  5. Ghost heavy weapons cast from the palm (ghost_cast: its 2HH files rebuilt from its pistol files, gun hidden)
  6. priorities (prio_fix): aim / attack up / down no higher than their level file; walk / run / sneak / turn / jump
     upper body capped under the race's lowest weapon stance (Ghost: 22 - Dead Money's walk keyed the arms at 45, over
     the 2HR / 2HA hip stance's 35: walking with a gun out swung it off to the side); Hillfolk's fist / melee aims first
     raised from 20 (= its idle) to 23
Every step writes only its own files; sneak copies are made where the step says so."""
import os, re, shutil, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
REF = '/home/claude/fnv/ref_male'
XFER = {'Ghost': ('ghost', ['2ha', '2hr', '2hh', '2hl']), 'Ghoul': ('ghoul', ['2ha', '2hr', '2hh', '2hl']),
        'GlowingOne': ('ghoul', ['2ha', '2hr', '2hh', '2hl']), 'Hillfolk': ('hillfolk1', ['2ha', '2hr', '2hh', '2hl'])}
RETIME = {'SuperMutant', 'Nightkin', 'Swampfolk', 'Zetan'}
SNEAK_LOWER = {'Eyebot': -40}
LOCO_CAP = {'Ghost': 22}
PRIO_FIX = {'Lakelurk', 'Ghost', 'Ghoul', 'GlowingOne', 'Hillfolk', 'Swampfolk', 'SuperMutant', 'Nightkin', 'Zetan'}
AIM_RAISE = {'Hillfolk': (r'^(sneak)?(h2h|1hm|2hm)aim(up|down)?\.kf$', 20, 23),
             'Lakelurk': (r'^(sneak)?(h2h|1hm|2hm)aim(up|down)?\.kf$', 20, 23)}
BLOCK_HUMAN = {'Ghost': 'ghost', 'Ghoul': 'ghoul', 'GlowingOne': 'ghoul', 'Hillfolk': 'hillfolk1',
               'SuperMutant': 'supermutant', 'Nightkin': 'supermutant', 'Swampfolk': 'swampfolk', 'Zetan': 'zetan'}
BLOCK_OWN = {'Eyebot': 'h2h,mt', 'Securitron': 'h2h,mt', 'Protectron': 'h2h,mt', 'Robobrain': 'h2h,mt',
             'SentryBot': 'h2h,mt', 'Lakelurk': 'h2h,mt,1hm,2hm', 'Mirelurk': 'h2h,mt,1hm,2hm', 'Trog': 'h2h,mt,1hm,2hm', 'Deathclaw': 'h2h,mt,1hm,2hm', 'Tunneler': 'h2h,mt,1hm,2hm',
             'MisterHandy': 'h2h,mt --keep-1hm', 'MisterGutsy': 'h2h,mt --keep-1hm'}

def py(*a):
    r = subprocess.run([sys.executable, '-P', *a], capture_output=True, text=True)
    if r.returncode: sys.exit(r.stderr)
    return r.stdout.strip().splitlines()[-1:] if r.stdout.strip() else []

def copy_in(src, dst, sneak=True):
    for f in os.listdir(src):
        shutil.copyfile(os.path.join(src, f), os.path.join(dst, f))
        if sneak and not f.startswith('sneak'): shutil.copyfile(os.path.join(src, f), os.path.join(dst, 'sneak' + f))

if __name__ == '__main__':
    d, race = sys.argv[1], sys.argv[2]; tmp = os.path.join(d, '_post_tmp')
    if race in XFER:
        cfg, pres = XFER[race]
        sys.path.insert(0, HERE); import weaponparts as WP
        shutil.rmtree(tmp, ignore_errors=True)
        for p in pres: print(race, 'xfer', p, py(os.path.join(HERE, 'xfer_human.py'), cfg, p, tmp))
        refs = set(os.listdir(REF)); n = 0
        for f in sorted(os.listdir(tmp)):
            c = [f] + ([] if re.search(r'reload|jam', f) else [f[:3] + 'aim.kf'])
            s = next((x for x in c if x in refs), None)
            if s: n += WP.merge(os.path.join(tmp, f), os.path.join(REF, s), keep_loose_transforms=True)
        print(race, 'weapon-part tracks', n); copy_in(tmp, d); shutil.rmtree(tmp)
    if race in RETIME: print(race, 'retime_is', py(os.path.join(HERE, 'retime_is.py'), d))
    if race in SNEAK_LOWER: print(race, 'sneak_lower', py(os.path.join(HERE, 'sneak_lower.py'), d, str(SNEAK_LOWER[race])))
    if race in BLOCK_HUMAN:
        shutil.rmtree(tmp, ignore_errors=True)
        print(race, 'blocks', py(os.path.join(HERE, 'block_xfer.py'), BLOCK_HUMAN[race], tmp)); copy_in(tmp, d, sneak=False); shutil.rmtree(tmp)
    elif race in BLOCK_OWN:
        shutil.rmtree(tmp, ignore_errors=True); a = BLOCK_OWN[race].split()
        print(race, 'blocks', py(os.path.join(HERE, 'own_block.py'), d, tmp, *a)); copy_in(tmp, d, sneak=False); shutil.rmtree(tmp)
    if race == 'Ghost':
        shutil.rmtree(tmp, ignore_errors=True)
        print(race, 'ghost_cast', py(os.path.join(HERE, 'ghost_cast.py'), d, tmp)); copy_in(tmp, d, sneak=False); shutil.rmtree(tmp)
    if race in AIM_RAISE:
        import struct, prio_fix as PF, loco_prio as LP
        from nifedit import NifFile
        pat, old, new = AIM_RAISE[race]; k = 0
        for f in os.listdir(d):
            if not re.match(pat, f.lower()): continue
            nf = NifFile(os.path.join(d, f)); si, sb, ncb = PF._seq(nf)
            for j in range(ncb):
                o = 12 + 29 * j; nm = nf.strings[struct.unpack_from('<i', sb, o + 9)[0]]
                if not LP.LOWER.match(nm) and sb[o + 8] == old: sb[o + 8] = new
            nf.blocks[si] = bytes(sb); open(os.path.join(d, f), 'wb').write(nf.to_bytes()); k += 1
        print(race, 'aims raised', k)
    if race in LOCO_CAP: print(race, 'loco_prio', py(os.path.join(HERE, 'loco_prio.py'), d, str(LOCO_CAP[race])))
    if race in PRIO_FIX: print(race, 'prio_fix', py(os.path.join(HERE, 'prio_fix.py'), d, '--loco', 'auto'))
