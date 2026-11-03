"""Turns creature sound-enum text keys ("Enum: Left", "Enum: Auxiliary2", ...) into direct "Sound: <SOUN EDID>" keys.
usage: python3 enum_keys.py <race> <folder> [--recursive]

Why: a creature's animations name its sounds indirectly - "Enum: <type>" plays the sound the *creature record* (CREA
sound list, CSDT/CSDI) assigns to that type (feet, swing, attack vox...). A creature-race player is a Character: its
base is an NPC_ with no creature sound list, so those keys are silent (no footsteps, no swing / attack vocals).
The fix is data only: each Enum key becomes the Sound key of the SOUN the vanilla creature uses for that type (from
its AudioTemplate CREA). Enum types with no sound in the template are dropped; anything else stays as it is.
Idempotent (a file without Enum keys is left untouched)."""
import os, sys, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from nifedit import NifFile
from sound_keys import text_keys

MAPS = {
    # FalloutNV.esm AudioTemplateFeralGhoul (00065712)
    'ghoul': {'left': 'NPCFeralGhoulFootWalkLeft', 'right': 'NPCFeralGhoulFootWalkRight',
              'backleft': 'NPCFeralGhoulFootRunLeft', 'backright': 'NPCFeralGhoulFootRunRight',
              'auxiliary2': 'NPCFeralGhoulSwing', 'auxiliary3': 'NPCFeralGhoulAttack', 'auxiliary4': 'NPCFeralGhoulVoxAtk',
              'auxiliary5': 'NPCFeralGhoulVoxAtk2', 'auxiliary6': 'NPCFeralGhoulAware', 'auxiliary8': None,       # chase vox: every run cycle on the player = constant screeching
              'auxiliary1': None, 'auxiliary7': None},
    # FalloutNV.esm AudioTemplateSuperMutant (0001FF5F)
    'supermutant': {'left': 'NPCSuperMutantFootLeft', 'right': 'NPCSuperMutantFootRight',
                    'backleft': 'NPCSuperMutantRunLeft', 'backright': 'NPCSuperMutantRunRight',
                    'auxiliary1': 'NPCSuperMutantFoley', 'auxiliary2': 'NPCSuperMutantArmor',
                    'auxiliary3': None, 'auxiliary4': None, 'auxiliary5': None, 'auxiliary6': None, 'auxiliary7': None,
                    'auxiliary8': None, 'equip': None, 'unequip': None},
    # (TTW) Point Lookout swampfolk (Hillfolk1 / Hillfolk2and3): their CREA audio template is the super mutant's
    # (Fallout3 AudioTemplateSuperMutant); their animations only use the foot enums
    'swampfolk': {'left': 'NPCSuperMutantFootLeft', 'right': 'NPCSuperMutantFootRight',
                  'backleft': None, 'backright': None, 'equip': None, 'unequip': None},
    # (TTW) The Pitt trog: AudioTemplateTrog has no foot sounds (death + idle loop only); the trog's own SOUNs
    # (ThePitt.esm) are used - walk steps, and run steps for the run-derived files ('trogrun')
    'trog': {'left': 'NPCTrogFootLeft', 'right': 'NPCTrogFootRight', 'backleft': None, 'backright': None},
    'trogrun': {'left': 'NPCTrogFootRunLeft', 'right': 'NPCTrogFootRunRight', 'backleft': None, 'backright': None},
    # Lonesome Road tunneler = FalloutNV AudioTemplateSporeCarrier (001489F5). Idle (aim vox in every strafe /
    # turn loop) and Aware (hiss in the aim loop) dropped - on the player they would fire constantly.
    'sporecarrier': {'left': 'NPCSporeCarrierFootLeft', 'right': 'NPCSporeCarrierFootRight',
                     'backleft': 'NPCSporeCarrierFootRunLeft', 'backright': 'NPCSporeCarrierFootRunRight',
                     'idle': None, 'aware': None, 'attack': 'NPCSporeCarrierArmSwing',
                     'auxiliary1': 'NPCSporeCarrierRise', 'auxiliary2': 'NPCSporeCarrierRiseVox', 'auxiliary3': 'NPCSporeCarrierAtkVox',
                     'auxiliary4': 'NPCSporeCarrierJump', 'auxiliary5': 'NPCSporeCarrierLand', 'auxiliary6': 'NPCSporeCarrierSwing',
                     'auxiliary7': 'NPCSporeCarrierAtkVox', 'auxiliary8': 'NPCSporeCarrierFlyVox'},
    # FalloutNV.esm AudioTemplateDeathclaw (000A5D40). Idle (vox in its idle loop) and Auxiliary1 (chase vox in its run
    # and strafes) dropped - on the player they would fire constantly.
    'deathclaw': {'left': 'NPCDeathclawFootWalkL', 'right': 'NPCDeathclawFootWalkR',
                  'backleft': 'NPCDeathclawFootRunL', 'backright': 'NPCDeathclawFootRunR', 'idle': None,
                  'auxiliary1': None, 'auxiliary2': 'NPCDeathClawLand', 'auxiliary3': 'NPCDeathclawPowerAtkVox',
                  'auxiliary4': 'NPCDeathClawArmSwing', 'auxiliary5': 'NPCDeathclawStrikeVox',
                  'auxiliary6': 'NPCDeathclawStrikeVox', 'auxiliary7': 'NPCDeathclawPainVox'},
    # FalloutNV.esm AudioTemplateMirelurkKing (000C3B2E; the lakelurks'). Idle (vox) and Auxiliary1 (attack vox in its run)
    # dropped - on the player they would fire constantly; Auxiliary7 = the shriek's vox, Auxiliary6 / 8 = its equips.
    'lakelurk': {'left': 'NPCMirelurkKingFootL', 'right': 'NPCMirelurkKingFootR', 'backleft': None, 'backright': None,
                 'idle': None, 'aware': None, 'auxiliary1': None, 'auxiliary2': 'NPCMirelurkKingSwing',
                 'auxiliary3': 'NPCMirelurkKingAttack', 'auxiliary4': 'NPCMirelurkKingAttack', 'auxiliary5': 'NPCMirelurkKingAttack',
                 'auxiliary6': 'NPCMirelurkKingEquip', 'auxiliary7': 'NPCMirelurkKingSonicVox', 'auxiliary8': 'NPCMirelurkKingSonicEquip',
                 'eight': None},
    # (TTW) Fallout 3 AudioTemplateMirelurk (000710A3). Idle (vox in its idle loop) dropped.
    'mirelurk': {'left': 'NPCMirelurkFootLeft', 'right': 'NPCMirelurkFootRight', 'backleft': 'NPCMirelurkRunFootLeft',
                 'backright': 'NPCMirelurkRunFootRight', 'idle': None, 'aware': None, 'attack': 'NPCMirelurkAttack',
                 'auxiliary1': None},
}

def convert(path, m):
    raw = open(path, 'rb').read()
    f = NifFile(path)
    assert f.to_bytes() == raw, 'round trip mismatch ' + path
    i, name, keys = text_keys(f)
    if i is None or not any(s.strip().lower().startswith('enum:') for _, s in keys): return None
    out = []; stats = {}
    for t, s in keys:
        st = s.strip()
        if st.lower().startswith('enum:'):
            typ = st[5:].strip().lower().replace(' ', '')
            if typ in m:
                snd = m[typ]
                stats[typ] = stats.get(typ, 0) + 1
                if snd: out.append((t, 'Sound: ' + snd))
                continue
        out.append((t, s))
    f.blocks[i] = struct.pack('<iI', name, len(out)) + b''.join(struct.pack('<fi', t, f.str_index(s)) for t, s in out)
    return f, stats

if __name__ == '__main__':
    race, folder = sys.argv[1], sys.argv[2]
    m = MAPS[race]; total = {}; nfiles = 0
    walk = os.walk(folder) if '--recursive' in sys.argv else [(folder, [], os.listdir(folder))]
    for d, _, fs in walk:
        for fn in fs:
            if not fn.lower().endswith('.kf'): continue
            p = os.path.join(d, fn)
            r = convert(p, m)
            if not r: continue
            f, st = r
            open(p, 'wb').write(f.to_bytes()); nfiles += 1
            for k, v in st.items(): total[k] = total.get(k, 0) + v
            _, _, keys = text_keys(NifFile(p))
            assert not any(s.strip().lower().startswith('enum:') and s.strip()[5:].strip().lower().replace(' ', '') in m for _, s in keys)
    print(nfiles, 'files changed', total)
