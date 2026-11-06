"""Super mutant taunt voices: the lines Core plays as a super mutant taunt starts (TauntIdles=, the super mutants' own
intimidation idles, played as they are, weapon drawn). A 'Sound: <SOUN>' text key in copies of those idles played nothing
for the player (tested in game), so the idles are the vanilla files and the voice is Core's (StartSound, 3D at the player).
  taunt      TauntSound=      combat barks
  tauntkill  TauntKillSound=  the gloat, for the first taunt within 10 s of the player's kill
Sets (picked with the user 2026-11-05; each folder one SOUN, a random file per play):
  supermutant   (Super Mutant; creaturelowintsm)        PCSuperMutantTauntVox / PCSuperMutantTauntKillVox
  nightkin      (Nightkin; creaturesupermutant)          PCNightkinTauntVox / PCNightkinTauntKillVox
  supermutantdc (TTW Capital mutants; creaturesupermutantdc, Fallout 3) PCSuperMutantDCTauntVox / ...TauntKillVox
Lines already used as the races' attack / power attack / hit / death voices are not reused; searching lines (hiding /
seeking: "Come out and fight!", "Here human, human, human..."), "Don't you want to be like us?" and lines calling the
target human / small people (Nightkin fight more than humans) were dropped (user, 11-05). Wav: 44.1 kHz mono 16-bit,
as the attack barks -> sound\\fx\\npc\\playablecreatures\\<set>\\<taunt|tauntkill>\\pc_<set>_<kind>_NN.wav
usage: python3 -P sm_taunt.py <dir holding sound\\voice\\falloutnv.esm\\...> <dir holding sound\\voice\\fallout3.esm\\...> <out root>"""
import os, sys, subprocess

LINES = [   # (game, voice type, file, set, kind)
    ('nv', 'creaturelowintsm', 'vdialogues_alerttocombat_0015cceb_1.ogg', 'supermutant', 'taunt'),   # Now you die!
    ('nv', 'creaturelowintsm', 'vdialogues_normaltocombat_0015cd14_1.ogg', 'supermutant', 'taunt'),   # Gonna kill you!
    ('nv', 'creaturelowintsm', 'vdialogues_attack_0015cd3f_1.ogg', 'supermutant', 'taunt'),   # Want more?
    ('nv', 'creaturelowintsm', 'vdialogues_attack_0015cd3e_1.ogg', 'supermutant', 'taunt'),   # Yeah ha ha ha!
    ('nv', 'creaturelowintsm', 'vdialogues_attack_0015cd41_1.ogg', 'supermutant', 'taunt'),   # Destroy!
    ('nv', 'creaturelowintsm', 'vdialogues_attack_0015cd40_1.ogg', 'supermutant', 'taunt'),   # Kill!
    ('nv', 'creaturelowintsm', 'vdialogues_guardtrespass_0015ccda_1.ogg', 'supermutant', 'taunt'),   # This is our place. Go or be smashed.
    ('nv', 'creaturelowintsm', 'vdialogues_murder_0015cd03_1.ogg', 'supermutant', 'taunt'),   # You'll die for that!
    ('nv', 'creaturelowintsm', 'vdialogues_murdernocrime_0015ccd3_1.ogg', 'supermutant', 'tauntkill'),   # Weakling!
    ('nv', 'creaturelowintsm', 'vdialogues_murdernocrime_0015ccd2_1.ogg', 'supermutant', 'tauntkill'),   # Ah ha ha ha ha!
    ('nv', 'creaturelowintsm', 'vdialogues_combattonormal_0015cd75_1.ogg', 'supermutant', 'tauntkill'),   # Ha ha. Too weak.
    ('nv', 'creaturesupermutant', 'vdialoguen_alerttocombat_00152be9_1.ogg', 'nightkin', 'taunt'),   # You're mine!
    ('nv', 'creaturesupermutant', 'vdialoguen_normaltocombat_00152b76_1.ogg', 'nightkin', 'taunt'),   # You die now!
    ('nv', 'creaturesupermutant', 'vdialoguen_normaltocombat_00152b77_1.ogg', 'nightkin', 'taunt'),   # I'll kill you!
    ('nv', 'creaturesupermutant', 'vdialoguenightkin_murder_00152b72_1.ogg', 'nightkin', 'taunt'),   # Now you pay!
    ('nv', 'creaturesupermutant', 'vdialoguen_playerinironsit_00152b5d_1.ogg', 'nightkin', 'taunt'),   # {Snarls}I don't think so.
    ('nv', 'creaturesupermutant', 'vdialoguen_murdernocrime_00152b9a_1.ogg', 'nightkin', 'tauntkill'),   # {Slightly amused chuckle}
    ('nv', 'creaturesupermutant', 'vdialoguen_murdernocrime_00152b9b_1.ogg', 'nightkin', 'tauntkill'),   # {Medium sized laugh}
    ('nv', 'creaturesupermutant', 'vdialoguen_murdernocrime_00152b9c_1.ogg', 'nightkin', 'tauntkill'),   # {Big laugh}
    ('dc', 'creaturesupermutantdc', 'ms01_ms01mutanttaunt_0002dd9a_1.ogg', 'supermutantdc', 'taunt'),   # Don't be scared!
    ('dc', 'creaturesupermutantdc', 'ms01_ms01mutanttaunt_0002de01_1.ogg', 'supermutantdc', 'taunt'),   # Don't be shy!
    ('dc', 'creaturesupermutantdc', 'ms01_ms01mutanttaunt_0002de03_1.ogg', 'supermutantdc', 'taunt'),   # The time has come!
    ('dc', 'creaturesupermutantdc', 'ms01_ms01mutanttaunt_0002dd9b_1.ogg', 'supermutantdc', 'taunt'),   # Ahahahaha!
    ('dc', 'creaturesupermutantdc', 'ms01_ms01mutanttaunt_0002de05_1.ogg', 'supermutantdc', 'taunt'),   # Graahahaha!
    ('dc', 'creaturesupermutantdc', 'ms01_ms01mutanttaunt_0002de0c_1.ogg', 'supermutantdc', 'taunt'),   # GRRAAAHHHH!
    ('dc', 'creaturesupermutantdc', 'genericsup_normaltocombat_000483dc_1.ogg', 'supermutantdc', 'taunt'),   # Time to die!
    ('dc', 'creaturesupermutantdc', 'genericsup_normaltocombat_0006296f_1.ogg', 'supermutantdc', 'taunt'),   # I'll wear your bones around my neck!
    ('dc', 'creaturesupermutantdc', 'genericsup_normaltocombat_00062970_1.ogg', 'supermutantdc', 'taunt'),   # Gonna splatter your brains!
    ('dc', 'creaturesupermutantdc', 'genericsup_normaltocombat_00062971_1.ogg', 'supermutantdc', 'taunt'),   # I love a good fight!
    ('dc', 'creaturesupermutantdc', 'genericsupermutant_attack_0002959e_1.ogg', 'supermutantdc', 'taunt'),   # Oh ho ho! Little baby scared?
    ('dc', 'creaturesupermutantdc', 'genericsupermutant_attack_0002959f_1.ogg', 'supermutantdc', 'taunt'),   # Scream! Scream for your worthless life!
    ('dc', 'creaturesupermutantdc', 'genericsupermutant_attack_0002959d_1.ogg', 'supermutantdc', 'taunt'),   # You are weak! I am stroooonng!
    ('dc', 'creaturesupermutantdc', 'genericsupermutant_attack_000295a1_1.ogg', 'supermutantdc', 'taunt'),   # Hurry up and die! I'm hungry! Ha ha ha ha ha!
    ('dc', 'creaturesupermutantdc', 'genericsupermutant_attack_000217ff_1.ogg', 'supermutantdc', 'taunt'),   # I'll eat your brain and drink your blood!
    ('dc', 'creaturesupermutantdc', 'genericsupermutant_attack_000217fa_1.ogg', 'supermutantdc', 'taunt'),   # Bleed! Bleed and die!
    ('dc', 'creaturesupermutantdc', 'genericsup_alerttocombat_00062961_1.ogg', 'supermutantdc', 'taunt'),   # Game's over!
    ('dc', 'creaturesupermutantdc', 'genericsup_combattonormal_000629a8_1.ogg', 'supermutantdc', 'tauntkill'),   # I win again!
    ('dc', 'creaturesupermutantdc', 'genericsup_combattonormal_000629aa_1.ogg', 'supermutantdc', 'tauntkill'),   # You lose!
    ('dc', 'creaturesupermutantdc', 'genericsup_combattonormal_000629ab_1.ogg', 'supermutantdc', 'tauntkill'),   # Okay, who's next?!
]


def build(roots, out):
    made, count = [], {}
    for game, vt, fn, folder, kind in LINES:
        n = count[(folder, kind)] = count.get((folder, kind), 0) + 1
        esm = 'falloutnv.esm' if game == 'nv' else 'fallout3.esm'
        src = os.path.join(roots[game], 'sound', 'voice', esm, vt, fn)
        d = os.path.join(out, 'sound', 'fx', 'npc', 'playablecreatures', folder, kind); os.makedirs(d, exist_ok=True)
        w = os.path.join(d, f'pc_{folder}_{kind}_{n:02d}.wav')
        subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-i', src, '-ar', '44100', '-ac', '1', '-sample_fmt', 's16', w], check=True)
        made.append(w)
    return made


if __name__ == '__main__':
    a = sys.argv[1:]
    for m in build({'nv': a[0], 'dc': a[1]}, a[2]): print(m)
