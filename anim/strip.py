import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt, numpy as np
from author import SK, GRASP
YLIM = (40, 130)
SKIP = ('Ponytail', 'Footsteps', 'Axe', 'raygun', 'Scene Root', 'Twist', 'Finger')
def strip(rig, frames, out, gunlen=(-4, 30), views=((1, 2, 'side'), (0, 2, 'front'))):
    n = len(frames)
    fig, axs = plt.subplots(len(views), n, figsize=(3.4 * n, 4.2 * len(views)))
    for c, (lab, loc) in enumerate(frames):
        W = rig.fk(loc)
        for r, (a, b, vn) in enumerate(views):
            ax = axs[r, c]
            for nm in SK.order:
                p = SK.parent[nm]
                if p is None or any(k in nm for k in SKIP) or any(k in p for k in SKIP): continue
                if nm == 'Weapon': continue
                col = 'r' if ' R ' in nm else ('b' if ' L ' in nm else 'k')
                ax.plot([W[p][0][a], W[nm][0][a]], [W[p][0][b], W[nm][0][b]], col + '-', lw=1.5)
            wp, wR = W['Weapon']
            g0 = wp + wR[:, 0] * gunlen[0]; g1 = wp + wR[:, 0] * gunlen[1]
            ax.plot([g0[a], g1[a]], [g0[b], g1[b]], 'g-', lw=4, alpha=.6)
            m = wp - wR[:, 1] * 6 + wR[:, 0] * 5
            ax.plot([wp[a] + wR[0 if a == 0 else a, 0] * 0, m[a]], [wp[b], m[b]], 'g-', lw=2)
            gp = W['Bip01 L Hand'][0] + W['Bip01 L Hand'][1] @ GRASP
            ax.plot([W['Bip01 L Hand'][0][a], gp[a]], [W['Bip01 L Hand'][0][b], gp[b]], 'c-', lw=3)
            ax.set_xlim(-40 if a == 0 else -70, 45 if a == 0 else 60); ax.set_ylim(YLIM)
            ax.set_aspect('equal'); ax.set_title(f'{lab} {vn}', fontsize=7); ax.tick_params(labelsize=5)
    plt.tight_layout(); plt.savefig(out, dpi=75); plt.close()
