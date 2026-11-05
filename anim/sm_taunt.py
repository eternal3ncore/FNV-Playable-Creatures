"""Super mutant taunt voices: the lines Core plays (TauntSound=) as a super mutant taunt starts (TauntIdles=, the super
mutants' own intimidation idles, played as they are). A 'Sound: <SOUN>' text key in copies of those idles played nothing
for the player (tested in game), so the idles are the vanilla files and the voice is Core's.
  NV  (Super Mutant / Nightkin): SOUN PCSuperMutantTauntVox; voice = the low-int super mutant's combat shouts
      (creaturelowintsm AlertToCombat / LostToCombat / NormalToCombat, 10 lines)
      -> sound\\fx\\npc\\playablecreatures\\supermutant\\taunt\\pc_supermutant_taunt_NN.wav
  DC  (Capital Super Mutant / Brute / Master, TTW): SOUN PCSuperMutantDCTauntVox; voice = Fallout 3's super mutant
      taunts (creaturesupermutantdc MS01MutantTaunt + GenericSup NormalToCombat, 22 lines)
      -> sound\\fx\\npc\\playablecreatures\\supermutantdc\\taunt\\pc_supermutantdc_taunt_NN.wav
Every line, no silence padding (a taunt always speaks). Wav: 44.1 kHz mono 16-bit, as the attack barks.
usage: python3 -P sm_taunt.py <nv voice dir> <dc voice dir> <out root>"""
import os, sys, glob, subprocess

SETS = {'nv': ('supermutant', ('vdialogues_alerttocombat', 'vdialogues_losttocombat', 'vdialogues_normaltocombat')),
        'dc': ('supermutantdc', ('ms01_ms01mutanttaunt', 'genericsup_normaltocombat'))}


def build(voice_dirs, out):
    made = []
    for tag in ('nv', 'dc'):
        snd, topics = SETS[tag]
        lines = sorted(p for p in glob.glob(os.path.join(voice_dirs[tag], '*.ogg')) if os.path.basename(p).lower().startswith(topics))
        vd = os.path.join(out, 'sound', 'fx', 'npc', 'playablecreatures', snd, 'taunt'); os.makedirs(vd, exist_ok=True)
        for n, p in enumerate(lines, 1):
            w = os.path.join(vd, f'pc_{snd}_taunt_{n:02d}.wav')
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', p, '-ar', '44100', '-ac', '1', '-sample_fmt', 's16', w], check=True)
            made.append(w)
    return made


if __name__ == '__main__':
    a = sys.argv[1:]
    for m in build({'nv': a[0], 'dc': a[1]}, a[2]): print(m)
