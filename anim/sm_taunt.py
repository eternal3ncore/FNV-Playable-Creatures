"""Super mutant taunts with a voice: copies of the super mutants' intimidation idles (the TauntIdles of Core) carrying a
'Sound: <SOUN>' text key, and the taunt voice files for that SOUN (the vanilla KFs and voice lines are untouched).
  NV  (Super Mutant / Nightkin): creatures\\smspinebreaker\\idleanims\\specialidle_2haintimidate / 2 / 4.kf ->
      PlayableCreatures\\SuperMutant\\IdleAnims\\PCTaunt1-3.kf, key 'Sound: PCSuperMutantTauntVox';
      voice = the low-int super mutant's combat shouts (creaturelowintsm AlertToCombat / LostToCombat / NormalToCombat,
      10 lines) -> sound\\fx\\npc\\playablecreatures\\supermutant\\taunt\\pc_supermutant_taunt_NN.wav
  DC  (Capital Super Mutant / Brute / Master, TTW): creatures\\smspinebreakerdc\\idleanims\\... ->
      PlayableCreatures\\SuperMutantDC\\IdleAnims\\PCTaunt1-3.kf, key 'Sound: PCSuperMutantDCTauntVox';
      voice = Fallout 3's super mutant taunts (creaturesupermutantdc MS01MutantTaunt + GenericSup NormalToCombat, 22
      lines) -> sound\\fx\\npc\\playablecreatures\\supermutantdc\\taunt\\pc_supermutantdc_taunt_NN.wav
The key sits at KEY_AT (just after the start: a key on the start frame played nothing in the Ghost dodge). Every line,
no silence padding (a taunt always speaks). Wav: 44.1 kHz mono 16-bit, as the attack barks.
usage: python3 -P sm_taunt.py <nv idleanims dir> <dc idleanims dir> <nv voice dir> <dc voice dir> <out root>"""
import os, sys, glob, struct, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.append(os.path.dirname(HERE))
from nifedit import NifFile
from sound_keys import text_keys

KEY_AT = 0.10
FILES = ('specialidle_2haintimidate.kf', 'specialidle_2haintimidate2.kf', 'specialidle_2haintimidate4.kf')
SETS = {'nv': ('SuperMutant', 'PCSuperMutantTauntVox', 'supermutant', ('vdialogues_alerttocombat', 'vdialogues_losttocombat', 'vdialogues_normaltocombat')),
        'dc': ('SuperMutantDC', 'PCSuperMutantDCTauntVox', 'supermutantdc', ('ms01_ms01mutanttaunt', 'genericsup_normaltocombat'))}


def keyed_copy(src, dst, sound):
    f = NifFile(src); assert f.to_bytes() == open(src, 'rb').read(), 'round trip'
    i, name, keys = text_keys(f); assert i is not None
    keys = [k for k in keys if k[1] != 'Sound: ' + sound] + [(KEY_AT, 'Sound: ' + sound)]
    keys.sort(key=lambda k: (k[0], k[1] != 'start', k[1] == 'end'))
    f.blocks[i] = struct.pack('<iI', name, len(keys)) + b''.join(struct.pack('<fi', t, f.str_index(s)) for t, s in keys)
    os.makedirs(os.path.dirname(dst), exist_ok=True); open(dst, 'wb').write(f.to_bytes())


def build(kf_dirs, voice_dirs, out):
    made = []
    for tag in ('nv', 'dc'):
        folder, soun, snd, topics = SETS[tag]
        for n, fn in enumerate(FILES, 1):
            dst = os.path.join(out, 'meshes', 'PlayableCreatures', folder, 'IdleAnims', f'PCTaunt{n}.kf')
            keyed_copy(os.path.join(kf_dirs[tag], fn), dst, soun); made.append(dst)
        lines = sorted(p for p in glob.glob(os.path.join(voice_dirs[tag], '*.ogg')) if os.path.basename(p).lower().startswith(topics))
        vd = os.path.join(out, 'sound', 'fx', 'npc', 'playablecreatures', snd, 'taunt'); os.makedirs(vd, exist_ok=True)
        for n, p in enumerate(lines, 1):
            w = os.path.join(vd, f'pc_{snd}_taunt_{n:02d}.wav')
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', p, '-ar', '44100', '-ac', '1', '-sample_fmt', 's16', w], check=True)
            made.append(w)
    return made


if __name__ == '__main__':
    a = sys.argv[1:]
    made = build({'nv': a[0], 'dc': a[1]}, {'nv': a[2], 'dc': a[3]}, a[4])
    for m in made: print(m)
