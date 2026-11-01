"""Robot skeletons for Playable Creatures: Protectron, Robobrain, Mister Handy / Gutsy, Sentry Bot.
usage: python3 -P build_skel_robot.py <robot> <creature src dir> <out dir>
Same recipe as the Securitron / Eyebot skeletons (build_skel_securitron.py, build_skel_eyebot.py), from the vanilla
Creatures\\<robot>\\Skeleton.nif:
  * Camera3rd (child of Scene Root) at the robot's camera height (skeleton units: the robobrain's rig is 3x size and
    scaled 0.33 by its race), the human's y offset; the race's marker (PCSkeleton:<Robot>, read by
    PlayableCreatures.dll); HeadAnims under Bip01 Head;
  * the creature's rigid model parts (its NIFZ list: weapon emitters, brain, dome, tracks, jets...), which a creature
    gets attached by their 'Prn' string and an NPC race can't carry, grafted under that node (root renamed when the
    skeleton already has a node of that name; a BSFadeNode root becomes a NiNode; BSXFlags 'animated' so their
    controllers run);
  * projectile direction: a weapon fires along its projectile node's local +Y -> each emitter is levelled in the
    robot's own aim pose of its weapon (world frame = world axes there: +Y straight ahead), so the aim up / down
    poses pitch it with the arm (CFG 'level');
  * Weapon (if missing) + ProjectileNode under it: the animations re-parent Weapon (prn keys) onto the projectile
    node that fires the equipped weapon type;
  * every other human node as a zero-offset stand-in (PLACE map, else the human parent, else the robot's torso).
A robot with several bodies (Mister Handy / Mister Gutsy) gets one skeleton file per variant (same animations)."""
import os, struct, sys
import numpy as np
sys.path.append('/home/claude/fnv'); sys.path.append('/home/claude/fnv/anim')
from nifedit import NifFile
from nif import Nif
from graft import graft, set_bsx_animated
from kf import KFEval, Skeleton
from robotlib import rot_axis

ROBOT, SRC, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
HUM = '/home/claude/fnv/ref_weap/skeleton.nif'
BARREL_Y = np.array([[0, 1, 0], [0, 0, 1], [1, 0, 0]], float)      # columns X=(0,0,1) Y=(1,0,0) Z=(0,1,0)
JET = '/home/claude/fnv/robot_src/Fallout - Meshes/meshes/creatures/mistergutsy/'

CFG = {
    # Protectron (41 nodes, a biped with the human bone names): hand laser on the right forearm, head laser on the
    # head, brain, dome. Jet (Mister Handy's FXMrHandyJetAddOn, main flame only) on the back as 'PCJet', switched by
    # the locomotion animations through its scale (hover = 1, on foot = ~0).
    'protectron': dict(
        camz=121.0, torso='Bip01 Spine',
        variants=[('Skeleton.nif', 'PCSkeleton:Protectron',
                   [('1hprhandlaser.nif', 'Bip01 R Forearm', 'Dummy01_RHandLaser'),
                    ('2hlheadlaser.nif', 'Bip01 Head', 'Dummy01_HeadLaser '),
                    ('blowawaybrain.nif', 'Bip01 Spine Brain', 'Brain'),
                    ('blowawaydome.nif', 'Bip01 Head', 'PCDomeRoot')])],   # under its Prn: the part root
                                                                            # carries DomeRoot's rotation itself
        pnodes=['ProjectileNode_RHandLaser', 'ProjectileNode_HeadLaser'],
        level={'ProjectileNode_RHandLaser': 'specialanims/1hpaim.kf', 'ProjectileNode_HeadLaser': 'specialanims/2hlaim.kf'},
        place={}, back_jet=(0.0, -19.0, 74.0)),
    # Robobrain (41 nodes, rig 3x size, CREA scale 0.33): laser in the right hand (ProjectileNode_Right), mesmetron
    # beam from the head (ProjectileNode_HeadLaser), left hand emitter. Parts: the small brain plate, animated tracks
    # on the feet, and BrainTalk = the brain
    # itself in the dome (Prn DomeRoot), its talking glow controllers dropped (static brain).
    'robobrain': dict(
        camz=360.0, torso='Bip01 Spine',
        variants=[('Skeleton.nif', 'PCSkeleton:Robobrain',
                   [('brain.nif', 'Bip01 Spine Brain', 'PCBrain'),
                    ('lefttrack.nif', 'Bip01 L Foot', 'Node_LeftTrack'),
                    ('righttrack.nif', 'Bip01 R Foot', 'Node_RightTrack'),
                    ('braintalk.nif', 'DomeRoot', 'PCBrainTalk')])],
        static=['braintalk.nif'],
        pnodes=['ProjectileNode_Right', 'ProjectileNode_HeadLaser'], place={},
        level={'ProjectileNode_Right': '1hpaim.kf', 'ProjectileNode_HeadLaser': '2hl_aim.kf'}),
    # Mister Handy / Mister Gutsy (53 nodes; the 'legs' are its three arms: front claw = R Thigh Front chain, right
    # arm = R Thigh chain (buzzsaw / plasma gun), left arm = L Thigh chain (flamer)); jets on the pelvis (all three
    # flames, always on: it hovers). one folder each (the Gutsy's melee uses its claw: own animations)
    'misterhandy': dict(
        camz=118.0, torso='Bip01 Spine',
        variants=[('Skeleton.nif', 'PCSkeleton:MisterHandy',
                   [('brainhandy.nif', 'Bip01 Spine Brain', 'Brain'),
                    ('fxmrhandyjetaddon.nif', 'Bip01 Pelvis', 'PCJets'),
                    ('gutsyflametank.nif', 'Bip01 L Foot 01', 'PCFlameTank'),
                    ('gutsyflamethrower.nif', 'Bip01 L Toe 1', 'PCFlamethrower'),
                    ('gutsybuzzsaw.nif', 'Bip01 R Foot 01', 'PCBuzzsaw')])],
        pnodes=['ProjectileNode_HeadLaser', 'ProjectileNode_HeadLaser01'],
        level={'ProjectileNode_HeadLaser': 'specialanims/2hlaim.kf', 'ProjectileNode_HeadLaser01': 'specialanims/1hpaim.kf'},
        place={'Bip01 Spine1': 'Bip01 Spine', 'Bip01 Neck': 'Bip01 Neck1'}, projnode='ProjectileNode_HeadLaser'),
    'mistergutsy': dict(
        camz=118.0, torso='Bip01 Spine',
        variants=[('Skeleton.nif', 'PCSkeleton:MisterGutsy',
                   [('braingutsy.nif', 'Bip01 Spine Brain', 'Brain'),
                    ('fxmrhandyjetaddon.nif', 'Bip01 Pelvis', 'PCJets'),
                    ('gutsyflametank(army).nif', 'Bip01 L Foot 01', 'PCFlameTank'),
                    ('gutsyflamethrower(army).nif', 'Bip01 L Toe 1', 'PCFlamethrower'),
                    ('gutsyplasmagun(army).nif', 'Bip01 R Toe', 'PCPlasmaGun'),
                    ('gutsyplasmapack(army).nif', 'Bip01 R Foot 01', 'PCPlasmaPack')])],
        pnodes=['ProjectileNode_HeadLaser', 'ProjectileNode_HeadLaser01'],
        level={'ProjectileNode_HeadLaser': 'specialanims/2hlaim.kf', 'ProjectileNode_HeadLaser01': 'specialanims/1hpaim.kf'},
        place={'Bip01 Spine1': 'Bip01 Spine', 'Bip01 Neck': 'Bip01 Neck1'}, projnode='ProjectileNode_HeadLaser'),
    # Sentry Bot (26 nodes; its rig lies along +Y): gatling on the right forearm (ProjectileNode_RGatling), missile
    # pod on the left (SBMissile part, Prn Bip01 L Finger1).
    'sentrybot': dict(
        camz=124.0, torso='Bip01 Spine',
        variants=[('Skeleton.nif', 'PCSkeleton:SentryBot',
                   [('sentrybotmissileaddon.nif', 'Bip01 L Finger1', 'PCMissilePod')])],
        pnodes=['ProjectileNode_RGatling', 'PCMissileEmitter'], place={},
        emitters=[('PCMissileEmitter', 'Bip01 L Finger1')],          # launcher / thrown / mine emitter on the missile pod
        level={'ProjectileNode_RGatling': '2hhaim.kf', 'PCMissileEmitter': '2hlaim.kf'}),
}
C = CFG[ROBOT]
h = Nif(HUM); hn = {x[3]: x for x in h.tree()}


def pose_of(s, sk):
    """a KF sample as an FK pose. The accumulation root Bip01, when the sequence doesn't key it, is identity in game
    (the sentry bot's idle / aims key only Bip01 NonAccum, with Bip01's bind transform: Bip01's own bind - rotated,
    z 72 - would be applied twice and lay the robot on its back)"""
    pose = {n: v for n, v in s.items() if n in sk.local}
    if 'Bip01' not in pose: pose['Bip01'] = (np.zeros(3), np.eye(3))
    return pose


def idle_world(names):
    """world transforms of `names` in the creature's mtidle pose at t=0 (vanilla skeleton + idle keys)"""
    sk = Skeleton(os.path.join(SRC, 'skeleton.nif')); k = KFEval(os.path.join(SRC, 'mtidle.kf')); s = k.sample(k.start)
    W = sk.fk(pose_of(s, sk)); return {n: W[n] for n in names}


def unlink(f, pred):
    """remove children whose name matches pred from every NiNode / NiBillboardNode (blocks stay, unreferenced)"""
    names = {}
    for i, b in enumerate(f.blocks):
        if f.types[f.btype[i]] in ('NiNode', 'NiBillboardNode', 'NiTriStrips', 'NiTriShape'):
            si = struct.unpack_from('<i', b, 0)[0]; names[i] = f.strings[si] if 0 <= si < len(f.strings) else ''
    n = 0
    for i, b in enumerate(f.blocks):
        tn = f.types[f.btype[i]]
        if tn not in ('NiNode', 'NiBillboardNode'): continue
        tail = b[-2:] if tn == 'NiBillboardNode' else b''
        r = NifFile.parse_node(b[:len(b) - len(tail)])
        kids = [c for c in r['children'] if not (c >= 0 and pred(names.get(c, '')))]
        if len(kids) != len(r['children']):
            n += len(r['children']) - len(kids); r['children'] = kids; f.blocks[i] = NifFile.build_node(r) + tail
    if n: print('  unlinked', n, 'refraction cloud nodes')


def build(out_name, marker, grafts):
    f = NifFile(os.path.join(SRC, 'skeleton.nif')); added = []

    def add(parent, name, trans=(0, 0, 0), rot=(1, 0, 0, 0, 1, 0, 0, 0, 1)):
        if f.find(name) is not None: return f.find(name)
        pi = f.find(parent); assert pi is not None, parent
        i = f.add_node(pi, name, trans, rot, flags=524302); added.append((parent, name)); return i

    hc = hn['Camera3rd'][4]
    add('Scene Root', 'Camera3rd', (0.0, hc['trans'][1], C['camz']), hc['rot'])
    add('Scene Root', marker)
    add('Bip01 Head', 'HeadAnims')
    for part, parent, name in grafts:
        src = os.path.join(SRC, part) if os.path.exists(os.path.join(SRC, part)) else os.path.join(JET, part)
        before = len(f.blocks)
        existing = {x[3] for x in Nif(f.to_bytes()).tree()}
        idx, n = graft(f, parent, src, 0, name)
        if f.types[f.btype[idx]] == 'BSFadeNode': f.btype[idx] = f.type_index('NiNode')
        if part in C.get('static', []):                                   # property controllers dropped
            for i in range(before, len(f.blocks)):
                if f.types[f.btype[i]] in ('NiMaterialProperty', 'BSShaderPPLightingProperty', 'NiAlphaProperty'):
                    b = bytearray(f.blocks[i]); ne = struct.unpack_from('<I', b, 4)[0]
                    struct.pack_into('<i', b, 8 + 4 * ne, -1); f.blocks[i] = bytes(b)
        for i in range(before, len(f.blocks)):                          # grafted names that clash -> 'PC' + name
            if i == idx or f.types[f.btype[i]] not in ('NiNode', 'NiTriStrips', 'NiTriShape', 'NiBillboardNode'): continue
            b = bytearray(f.blocks[i]); si = struct.unpack_from('<i', b, 0)[0]
            if 0 <= si < len(f.strings) and f.strings[si] in existing:
                struct.pack_into('<i', b, 0, f.str_index('PC' + f.strings[si])); f.blocks[i] = bytes(b)
                print('    renamed grafted', f.strings[si], '->', 'PC' + f.strings[si])
        print('  grafted', part, '->', parent, 'as', repr(name), n, 'blocks')
    if C.get('back_jet'):
        # Mister Handy's jet (FXMrHandyJetAddOn: Prn Bip01 Pelvis, three flames around its base, billboarded): only
        # the main flame (JetFlames, 27 units below the add-on root, pointing down) is kept. Placed on the back below
        # the brain, with the Handy's idle world orientation of the add-on tilted 15 deg (flame down and back).
        gk = Skeleton(JET + 'skeleton.nif'); gi = KFEval(JET + 'mtidle.kf'); gs = gi.sample(gi.start)
        G = gk.fk({n: v for n, v in gs.items() if n in gk.local})
        jn = Nif(JET + 'fxmrhandyjetaddon.nif'); jr = jn.node(0)
        Rw = rot_axis([1, 0, 0], -15) @ G['Bip01 Pelvis'][1] @ np.array(jr['rot']).reshape(3, 3)
        main = [c for c in jr['children'] if jn.objnet(c)[0]['name'] == '##JetFlames']
        idx, n = graft(f, C['torso'], JET + 'fxmrhandyjetaddon.nif', 0, 'PCJet', keep_children=main)
        ps, Rs = idle_world([C['torso']])[C['torso']]
        r = f.node(idx)
        r['trans'] = [float(x) for x in Rs.T @ (np.array(C['back_jet'], float) - ps)]
        r['rot'] = [float(x) for x in (Rs.T @ Rw).reshape(9)]
        r['scale'] = 0.001                  # off unless a hover animation keys it on (a reset to bind = off)
        f.set_node(idx, r)
        print('  grafted back jet', n, 'blocks at', C['back_jet'], 'flame dir (idle, world):', np.round(Rw @ np.array([0, 0, -1.0]), 3))
    # (white blobs around Mister Handy / Gutsy / the protectron when changing weapons) the jets'
    # RefractCloudMesh (heat-haze refraction shells) render as opaque white on the player: unlinked, the flames stay
    unlink(f, lambda nm: nm.lstrip('#').startswith('RefractCloudMesh'))
    for i, sname in enumerate(f.strings):                               # '##' names -> plain (only the jets have them)
        if sname.startswith('##'): f.strings[i] = sname[2:]
    set_bsx_animated(f)
    for name, parent in C.get('emitters', []): add(parent, name)
    # projectile nodes levelled: in the robot's own aim pose of the weapon fired from it (CFG 'level'), the
    # node's world frame = the world axes (+Y forward, +Z up), so a shot leaves straight ahead and the aim up / down
    # poses pitch it with the arm (the sentry bot's gatling pointed 37 deg up / along +X in its aim pose)
    import tempfile
    tmp = tempfile.NamedTemporaryFile(suffix='.nif', delete=False).name; open(tmp, 'wb').write(f.to_bytes())
    sk = Skeleton(tmp)
    for pn, kfp in C['level'].items():
        k = KFEval(os.path.join(SRC, kfp)); s = k.sample(k.start)
        W = sk.fk(pose_of(s, sk))
        Rp = W[sk.parent[pn]][1]; i = f.find(pn); r = f.node(i)
        before = W[pn][1][:, 1]
        r['rot'] = [float(x) for x in Rp.T.reshape(9)]; f.set_node(i, r)
        print('  levelled', pn, 'in', kfp, ': +Y was', np.round(before, 2), '-> (0, 1, 0)')
    tree = h.tree(); stack = []                                          # human stand-ins, parents first
    for d, b, t, nm, r in tree:
        while stack and stack[-1][0] >= d: stack.pop()
        par = stack[-1][1] if stack else None
        stack.append((d, nm))
        if r is None or nm in ('Scene Root', 'Camera3rd') or f.find(nm) is not None: continue
        parent = C['place'].get(nm) or par
        while parent is not None and f.find(parent) is None: parent = C['place'].get(parent, C['torso'])
        add(parent, nm)
    # (the Handy / Gutsy flamer standing and moving) a text-key prn moves
    # the weapon MODEL, not the skeleton's Weapon node; an embedded robot weapon has no model and fires from its NNAM
    # node - except a Flame projectile, which leaves from the actor's 'ProjectileNode': under Weapon that is on the
    # Handy / Gutsy's front claw (Dummy01), hanging down / trailing behind. CFG 'projnode' puts it on the flamer tip.
    add(C.get('projnode', 'Weapon'), 'ProjectileNode')
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, out_name); open(p, 'wb').write(f.to_bytes())
    n = Nif(p); names = [x[3] for x in n.tree()]
    dup = sorted({x for x in names if x and names.count(x) > 1})
    print(out_name, 'added', len(added), 'nodes; human nodes missing:', sorted(x for x in set(hn) - set(names) if x), '; duplicate names:', dup)
    for need in (marker, 'Camera3rd', 'HeadAnims', 'Weapon', 'ProjectileNode') + tuple(C['pnodes']): assert need in names, need


for v in C['variants']: build(*v)
