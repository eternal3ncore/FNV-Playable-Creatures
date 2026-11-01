import sys,importlib,os,numpy as np; sys.path.insert(0,'/home/claude/fnv/anim')
from rig import Creature, write_kf
import loco2
out=sys.argv[2]; os.makedirs(out,exist_ok=True)
cr=Creature(importlib.import_module('creatures.'+sys.argv[1]))
jobs=[('mtidle.kf','sneakmtidle.kf',None)]+[(f'locomotion/mt{g}.kf',f'sneakmt{g}.kf',None) for g in ('forward','backward','left','right','turnleft','turnright','fastforward','fastbackward')]
for src,dst,_ in jobs:
    fr,bones,L,keys,cyc,name=loco2.crouch_frames(cr,src)
    write_kf(cr,os.path.join(out,dst),name,L,keys,fr,bones=bones,cycle=cyc); print(dst,name,round(L,2))
for side in 'LR':
    fr,bones,L,keys,cyc,name=loco2.crab_frames(cr,'locomotion/mtfastforward.kf',side)
    p=os.path.join(out,'Locomotion'); os.makedirs(p,exist_ok=True)
    write_kf(cr,os.path.join(p,f'mtfast{"left" if side=="L" else "right"}.kf'),name,L,keys,fr,bones=bones,cycle=cyc); print(name,round(L,2))
    # sneak version of the crab run: crouch it
    cr.extra['__crab'+side]=os.path.join(p,f'mtfast{"left" if side=="L" else "right"}.kf')
    fr,bones,L,keys,cyc,_=loco2.crouch_frames(cr,'__crab'+side)
    write_kf(cr,os.path.join(out,f'sneakmtfast{"left" if side=="L" else "right"}.kf'),name,L,keys,fr,bones=bones,cycle=cyc)
