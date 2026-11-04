"""Head collision shape for hand_xfer.HEAD_SHAPE, and a finger-in-head check for built files.
  shape: the head (+ jaw, lips, eyelids) vertices of a skinned body mesh, in Bip01 Head space (the skin data's bone
         transform), and the minimum-volume ellipsoid enclosing them (Khachiyan): prints c and A for HEAD_SHAPE
  check: every hand / finger joint and finger-segment point of a .kf against the vertices' convex hull, per frame
         (convex = conservative under the chin)
usage: python3 head_shape.py shape <body.nif>
       python3 head_shape.py check <body.nif> <Skeleton.nif> <file.kf> [...]"""
import os, struct, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.append(os.path.dirname(HERE))
from nifedit import NifFile

HEAD_BONES = ('Bip01 Head', 'Bip01 Ponytail1_Jaw', 'Bip01 Ponytail2_UpperLip', 'Bip01 Ponytail3_TopEvelid',
              'Bip01 Ponytail4_BotEvelid')


def head_cloud(path, bones=HEAD_BONES, wmin=0.3):
    f = NifFile(path)
    si = next(i for i, b in enumerate(f.blocks) if f.types[f.btype[i]] in ('BSDismemberSkinInstance', 'NiSkinInstance'))
    b = f.blocks[si]; data, _, _, nb = struct.unpack_from('<iiiI', b, 0); refs = struct.unpack_from('<%di' % nb, b, 16)
    names = [f.strings[struct.unpack_from('<i', f.blocks[r], 0)[0]] for r in refs]
    geo = next(i for i, b in enumerate(f.blocks) if f.types[f.btype[i]] in ('NiTriShapeData', 'NiTriStripsData'))
    g = f.blocks[geo]; nv = struct.unpack_from('<H', g, 4)[0]
    V = np.array(struct.unpack_from('<%df' % (3 * nv), g, 9)).reshape(-1, 3)
    d = f.blocks[data]; o = 52; nbs, _ = struct.unpack_from('<IB', d, o); o += 5
    idx = set(); HR = None
    for k in range(nbs):
        R = np.array(struct.unpack_from('<9f', d, o)).reshape(3, 3); t = np.array(struct.unpack_from('<3f', d, o + 36)); o += 68
        n, = struct.unpack_from('<H', d, o); o += 2
        w = [struct.unpack_from('<Hf', d, o + 6 * j) for j in range(n)]; o += 6 * n
        if names[k] in bones: idx |= {i for i, ww in w if ww >= wmin}
        if names[k] == bones[0]: HR = (R, t)
    return V[sorted(idx)] @ HR[0].T + HR[1]


def mvee(P, tol=1e-4):
    from scipy.spatial import ConvexHull
    P = P[ConvexHull(P).vertices]; N, d = P.shape; Q = np.vstack([P.T, np.ones(N)]); u = np.ones(N) / N
    for _ in range(5000):
        X = Q @ np.diag(u) @ Q.T; M = np.einsum('ij,ji->i', Q.T @ np.linalg.inv(X), Q); j = np.argmax(M)
        st = (M[j] - d - 1) / ((d + 1) * (M[j] - 1)); nu = (1 - st) * u; nu[j] += st
        if np.linalg.norm(nu - u) < tol: u = nu; break
        u = nu
    c = P.T @ u; return c, np.linalg.inv(P.T @ np.diag(u) @ P - np.outer(c, c)) / d


def check(cloud, skel, kf, sides='LR'):
    from scipy.spatial import Delaunay
    from kf import Skeleton, KFEval
    from hand_xfer import fk, local_pose
    hull = Delaunay(cloud); sk = Skeleton(skel); k = KFEval(kf); n = int(round((k.stop - k.start) * 30)) + 1; bad = []
    for i in range(n):
        t = k.start + (k.stop - k.start) * i / (n - 1); W = fk(sk, local_pose(sk, k.sample(t))); ph, Rh = W['Bip01 Head']
        pts = []
        for x in sk.order:
            if any(x == f'Bip01 {s} Hand' or x.startswith(f'Bip01 {s} Finger') for s in sides):
                pts.append(W[x][0]); p = sk.parent[x]
                if x.startswith('Bip01 ') and 'Finger' in x and p: pts.append((W[x][0] + W[p][0]) / 2)
        inside = int((hull.find_simplex((np.array(pts) - ph) @ Rh) >= 0).sum())
        if inside: bad.append((round(t, 2), inside))
    return n, bad


if __name__ == '__main__':
    a = sys.argv[1:]
    cl = head_cloud(a[1])
    if a[0] == 'shape':
        c, A = mvee(cl); print(len(cl), 'vertices; c', np.round(c, 2).tolist(), 'A', np.round(A, 5).tolist())
    else:
        for p in a[3:]:
            n, bad = check(cl, a[2], p); print(os.path.basename(p), 'frames with hand points inside the head:', len(bad), '/', n, bad[:10])
