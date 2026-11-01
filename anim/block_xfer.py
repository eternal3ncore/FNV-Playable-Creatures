"""block_xfer.py Human block animations onto a human-proportioned creature (xfer_human.transfer: the creature keeps
its own torso / head, each hand where the human's is relative to the shoulder, fingers / Weapon node from the human):
  h2hblockidle / h2hblockhit  <- human mtblockidle / mtblockhit (unarmed guard; base pose h2haim)
  1hmblockidle / 1hmblockhit  <- human 1hmblockidle / 1hmblockhit (base 1hmaim)
  2hmblock*  = copies of the 1HM pair (shared);  mtblock* = copies of the H2H pair
  sneak copies of all eight (upper body only: the legs come from the sneak locomotion)
usage: python3 -P block_xfer.py <creature cfg> <out dir> [human block ref dir]"""
import os, sys, shutil, importlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import xfer_human as X
from rig import Creature, write_kf
cfg = importlib.import_module('creatures.' + sys.argv[1]); out = sys.argv[2]
ref = sys.argv[3] if len(sys.argv) > 3 else '/home/claude/fnv/ref_block'
cr = Creature(cfg); os.makedirs(out, exist_ok=True)
JOBS = [('h2hblockidle.kf', 'mtblockidle.kf', 'h2haim.kf'), ('h2hblockhit.kf', 'mtblockhit.kf', 'h2haim.kf'),
        ('1hmblockidle.kf', '1hmblockidle.kf', '1hmaim.kf'), ('1hmblockhit.kf', '1hmblockhit.kf', '1hmaim.kf')]
made = []
for dst, src, base in JOBS:
    fr, bones, L, keys, cyc, seq = X.transfer(cr, os.path.join(ref, src), os.path.join(ref, base))
    write_kf(cr, os.path.join(out, dst), seq, L, keys, fr, bones=bones, cycle=cyc); made.append(dst)
for a, b in (('1hm', '2hm'), ('h2h', 'mt')):
    for g in ('blockidle', 'blockhit'):
        shutil.copyfile(os.path.join(out, a + g + '.kf'), os.path.join(out, b + g + '.kf')); made.append(b + g + '.kf')
for f in list(made): shutil.copyfile(os.path.join(out, f), os.path.join(out, 'sneak' + f))
print(len(made) * 2, 'block files ->', out)
