import sys, subprocess
from pe import PE
p = PE('/home/claude/fnv/FalloutNV_unpacked.exe')
def dis(va, n=0x80):
    o = p.off(va)
    open('/tmp/claude-0/_d.bin', 'wb').write(p.d[o:o+n])
    out = subprocess.run(['objdump', '-D', '-b', 'binary', '-m', 'i386', '-M', 'intel', f'--adjust-vma={va:#x}', '/tmp/claude-0/_d.bin'], capture_output=True, text=True).stdout
    return '\n'.join(l for l in out.splitlines()[7:])
if __name__ == '__main__':
    print(dis(int(sys.argv[1], 16), int(sys.argv[2], 16) if len(sys.argv) > 2 else 0x80))
