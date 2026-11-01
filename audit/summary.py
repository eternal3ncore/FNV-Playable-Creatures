import json,collections,os,sys
D=sys.argv[1] if len(sys.argv)>1 else '.'
def cat(f):
    b=os.path.basename(f).lower(); s='sneak ' if b.startswith('sneak') else ''
    b=b[5:] if b.startswith('sneak') else b
    if f.lower().startswith('idleanims'): return 'furniture'
    if 'reload' in b: return s+'reload'
    if 'jam' in b: return s+'jam'
    if 'jump' in b: return s+'jump'
    if b.startswith('mt') or f.lower().startswith('locomotion'): return s+'loco'
    if 'throw' in b: return s+'throw'
    if 'aim' in b: return s+'aim'
    if 'attack' in b or 'placemine' in b: return s+'attack'
    if 'equip' in b or 'holster' in b: return s+'equip'
    return s+'other'
tot=collections.Counter()
for r in ['Zetan','Ghost','Ghoul','SuperMutant','Swampfolk','Hillfolk','Trog']:
    d=json.load(open(os.path.join(D,r+'.json'))); fl=[f for f in d['flags'] if 'bone' in f]
    print(f"== {r}: files flagged {len(set(f['file'] for f in fl))}  hinge ranges {d.get('hinge_range')}")
    c=collections.Counter()
    for f in fl:
        k=f['kind']; part=('arm' if any(x in f['bone'] for x in ('Arm','Forearm','Hand','Clav')) else 'leg' if any(x in f['bone'] for x in ('Thigh','Calf','Foot')) else 'spine')
        c[(cat(f['file']).replace('sneak ',''), part, k)]+=1
    for k,v in sorted(c.items(), key=lambda x:-x[1])[:16]: print('   %4d'%v, k)
    tot[r]=len(set(f['file'] for f in fl))
print(dict(tot))
