"""Normalizes the TTW creature sources (Point Lookout Hillfolk1 / Hillfolk2and3, The Pitt street trog) for build_creature:
Hillfolk1 attack files are renamed to the vanilla group convention (one group name, variants by file suffix, like the
feral ghoul's h2hattackleft_b.kf) - FO3's AttackLeft_Bashing etc. are not FNV group names. Missing 2HM AttackLeft =
copies of the AttackRight swings. usage: python3 prep_ttw.py <creature_src_ttw dir>"""
import sys, os, struct, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.path.append('/home/claude/fnv')
from nifedit import NifFile
from kf import KF
D = sys.argv[1]
def rename(src, dst, seq):
    f = NifFile(src)
    bi = [i for i, t in enumerate(f.btype) if f.types[t] == 'NiControllerSequence'][0]
    b = bytearray(f.blocks[bi]); struct.pack_into('<i', b, 0, f.str_index(seq)); f.blocks[bi] = bytes(b)
    data = f.to_bytes()
    if os.path.abspath(src) != os.path.abspath(dst) and os.path.exists(src): os.remove(src)
    open(dst, 'wb').write(data)
    assert KF(dst).name == seq, (dst, KF(dst).name)
    print(f'{os.path.basename(src):34s} -> {os.path.basename(dst):28s} {seq}')
H = os.path.join(D, 'hillfolk1')
J = lambda n: os.path.join(H, n)
if os.path.exists(J('h2hattackleft_backhand.kf')):
    shutil.copyfile(J('2hmattackright_backhand.kf'), J('_l1.kf')); shutil.copyfile(J('2hmattackright_cross.kf'), J('_l2.kf'))
    for s, d, q in [('h2hattackleft_backhand.kf', 'h2hattackleft.kf', 'AttackLeft'),
                    ('h2hattackleft_bashing.kf', 'h2hattackleft_b.kf', 'AttackLeft'),
                    ('h2hattackleft_cross.kf', 'h2hattackleft_c.kf', 'AttackLeft'),
                    ('h2hattackright_backhand.kf', 'h2hattackright.kf', 'AttackRight'),
                    ('h2hattackright_cross.kf', 'h2hattackright_b.kf', 'AttackRight'),
                    ('h2hpowerattack.kf', 'h2hattackrightpower.kf', 'AttackRightPower'),
                    ('2hmattackright_backhand.kf', '2hmattackright.kf', 'AttackRight'),
                    ('2hmattackright_cross.kf', '2hmattackright_b.kf', 'AttackRight'),
                    ('_l1.kf', '2hmattackleft.kf', 'AttackLeft'),
                    ('_l2.kf', '2hmattackleft_b.kf', 'AttackLeft'),
                    ('2hmpowerattack.kf', '2hmattackrightpower.kf', 'AttackRightPower'),
                    ('2hmforwardpowerattack.kf', '2hmattackforwardpower.kf', 'AttackForwardPower')]:
        rename(J(s), J(d), q)
# trog: the misnamed left-leg hit idle (sequence SpecialIdle_HitLegRight) is not used by the player - left as is
