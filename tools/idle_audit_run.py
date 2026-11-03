"""device runner: resolve the MO2 profile's active plugins to files (MO2 priority: modlist.txt top wins, then Data) and scan them"""
import os, subprocess, sys
H = os.path.expanduser('~/mnt'); MO = H + '/MO2'; DATA = H + '/Fallout New Vegas/Data'
prof = MO + '/profiles/Default'
plugins = [l.strip().lstrip('*') for l in open(prof + '/plugins.txt', encoding='utf-8', errors='replace') if l.strip() and not l.startswith('#')]
mods = [l.strip()[1:] for l in open(prof + '/modlist.txt', encoding='utf-8', errors='replace') if l.startswith('+')]
paths = []
for p in plugins:
    hit = None
    for m in mods:
        f = os.path.join(MO, 'mods', m, p)
        if os.path.exists(f): hit = f; break
    if not hit and os.path.exists(os.path.join(DATA, p)): hit = os.path.join(DATA, p)
    print(p, '->', hit, file=sys.stderr); paths.append(hit) if hit else None
subprocess.run([sys.executable, os.path.dirname(os.path.abspath(__file__)) + '/idle_audit.py', sys.argv[1]] + paths, check=True)
