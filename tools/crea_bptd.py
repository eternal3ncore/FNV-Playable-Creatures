import struct,zlib,sys
def walk(d):
    # iterate top-level groups/records properly
    i=0; n=len(d)
    out=[]
    def rec_iter(start,end):
        j=start
        while j<end:
            t=d[j:j+4]
            if t==b'GRUP':
                gsz=struct.unpack_from('<I',d,j+4)[0]
                yield from rec_iter(j+24,j+gsz); j+=gsz
            else:
                sz,fl,fid=struct.unpack_from('<III',d,j+4)
                yield t,fl,fid,d[j+24:j+24+sz]; j+=24+sz
    return rec_iter(0,n)
def subs(b):
    i=0
    while i+6<=len(b):
        t=b[i:i+4]; l=struct.unpack_from('<H',b,i+4)[0]
        if t==b'XXXX': l=struct.unpack_from('<I',b,i+6)[0]; i+=10; t=b[i:i+4]; yield t,b[i+6:i+6+l]; i+=6+l; continue
        yield t,b[i+6:i+6+l]; i+=6+l
for path in sys.argv[1:]:
    d=open(path,'rb').read()
    masters=[]
    for t,fl,fid,b in walk(d):
        if t==b'TES4':
            masters=[v.rstrip(b'\0').decode() for s,v in subs(b) if s==b'MAST']; continue
        if t not in (b'CREA',b'BPTD',b'NPC_'): continue
        if fl&0x40000:
            try: b=zlib.decompress(b[4:])
            except: continue
        f=dict()
        for s,v in subs(b):
            f.setdefault(s,v)
        ed=f.get(b'EDID',b'').rstrip(b'\0').decode('latin1')
        if t==b'BPTD': print('BPTD',hex(fid),ed,(f.get(b'MODL') or b'').rstrip(b'\0').decode('latin1')); continue
        if t==b'CREA' and b'PNAM' in f:
            pn=struct.unpack('<I',f[b'PNAM'][:4])[0]
            print('CREA',hex(fid),ed,'PNAM',hex(pn),(f.get(b'MODL') or b'').rstrip(b'\0').decode('latin1')[:60])
