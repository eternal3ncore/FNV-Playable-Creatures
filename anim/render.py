import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt, numpy as np
SKIP = ('Ponytail', 'Footsteps', 'Axe', 'raygun', 'Scene Root')
def draw(sk, Ws, titles, out, gun=None):
    """Ws: list of FK dicts; draws front (x,z), side (y,z), top (x,y)."""
    fig, axs = plt.subplots(len(Ws), 3, figsize=(12, 4*len(Ws)))
    axs = np.atleast_2d(axs)
    for r, (W, ti) in enumerate(zip(Ws, titles)):
        for c, (a, b, lab) in enumerate(((0, 2, 'front x-z'), (1, 2, 'side y-z (+y fwd)'), (0, 1, 'top x-y'))):
            ax = axs[r, c]
            for nm in sk.order:
                p = sk.parent[nm]
                if p is None or any(k in nm for k in SKIP) or any(k in p for k in SKIP): continue
                col = 'r' if ' R ' in nm or 'R Clav' in nm else ('b' if ' L ' in nm else 'k')
                if nm == 'Weapon': col = 'g'
                ax.plot([W[p][0][a], W[nm][0][a]], [W[p][0][b], W[nm][0][b]], col+'-', lw=1.5)
            if 'Weapon' in W:
                wp, wR = W['Weapon']
                for k, cc in ((0, 'm'), (1, 'c'), (2, 'y')):
                    e = wp + wR[:, k]*15
                    ax.plot([wp[a], e[a]], [wp[b], e[b]], cc+'-', lw=2)
            ax.set_aspect('equal'); ax.set_title(f'{ti}: {lab}', fontsize=8); ax.grid(alpha=.3)
    plt.tight_layout(); plt.savefig(out, dpi=70); plt.close()
