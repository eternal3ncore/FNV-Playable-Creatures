"""Creature reloads/jams: procedural motion on the Zetan's own skeleton + aim pose (no human motion data).
Timing and 'Sound:' / 'Hit' text keys are copied from the matching vanilla/TTW human file of the same group,
so each weapon keeps its own reload sounds and round-insert timing. Writes 1hp*/2hr* reload A..S, W..Z(+Start), jam A..S, W..Z."""
import json, os, sys
from author import Rig, sample, write_kf
from plans import CFG, magazine, loop_start, loop_step, jam
OUT = sys.argv[1] if len(sys.argv) > 1 else '/home/claude/fnv/build/reload11'
KEYS = json.load(open('/home/claude/fnv/human_reload_keys.json'))
os.makedirs(OUT, exist_ok=True)
PLAIN = 'ABCDEFGHIJKLMNOPQRS'; LOOP = 'WXYZ'
def keys_for(fname, seq, default_len, default_keys):
    h = KEYS.get(fname)
    if not h: return default_len, default_keys, False
    L = h['len']; ks = [(t, s) for t, s in h['keys'] if s and s not in ('start', 'end')]
    return L, [(0.0, 'start')] + [(min(t, L), s) for t, s in ks] + [(L, 'end')], True
n = 0; used = 0; report = []
for hp, aim in (('1hp', '1hpaim.kf'), ('2hr', '2hraim.kf')):
    rig = Rig(aim); c = CFG[hp]
    def emit(fname, seq, plan_fn, dlen, dkeys):
        global n, used
        L, ks, h = keys_for(fname, seq, dlen, dkeys)
        plan = plan_fn(L, ks)
        write_kf(f'{OUT}/{fname}', seq, L, ks, sample(rig, plan, L))
        n += 1; used += h
        report.append(f'{fname}\t{seq}\t{L:.2f}s\t{"human timing" if h else "default"}\t' + ','.join(s for _, s in ks))
    for Lt in PLAIN:
        emit(f'{hp}reload{Lt.lower()}.kf', f'Reload{Lt}', lambda L, k: magazine(c), 2.0, [(0, 'start'), (0.0333, 'Blend:3'), (2.0, 'end')])
        emit(f'{hp}jam{Lt.lower()}.kf', f'Jam{Lt}', lambda L, k: jam(c), 1.4, [(0, 'start'), (0.0333, 'Blend:3'), (1.4, 'end')])
    for Lt in LOOP:
        emit(f'{hp}reload{Lt.lower()}start.kf', f'Reload{Lt}Start', lambda L, k: loop_start(c), 0.9, [(0, 'start'), (0.9, 'end')])
        def lp(L, k):
            hit = [t for t, s in k if s == 'Hit']
            return loop_step(c, (hit[0] / L) if hit else 0.45)
        emit(f'{hp}reload{Lt.lower()}.kf', f'Reload{Lt}', lp, 1.6, [(0, 'start'), (0.7, 'Hit'), (1.6, 'end')])
        emit(f'{hp}jam{Lt.lower()}.kf', f'Jam{Lt}', lambda L, k: jam(c), 1.4, [(0, 'start'), (0.0333, 'Blend:3'), (1.4, 'end')])
open(f'{OUT}/reload_manifest.txt', 'w').write('\n'.join(report) + '\n')
print(n, 'files,', used, 'with human timing/sound keys ->', OUT)
