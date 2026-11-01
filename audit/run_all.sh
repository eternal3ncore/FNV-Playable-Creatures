cd /home/claude/fnv/anim
S=${1:-/home/claude/fnv/audit/snap/PlayableCreatures}; O=${2:-/home/claude/fnv/audit}; T=/home/claude/fnv/creature_src_ttw
python3 audit_twist.py Swampfolk $S/Swampfolk $T/swampfolk > $O/Swampfolk.json &
python3 audit_twist.py Trog $S/Trog $T/trog > $O/Trog.json &
python3 audit_twist.py Hillfolk $S/Hillfolk $T/hillfolk1 > $O/Hillfolk.json &
python3 audit_twist.py Ghoul $S/Ghoul "/home/claude/fnv/creature_src/Fallout - Meshes/meshes/creatures/ghoul" > $O/Ghoul.json &
python3 audit_twist.py SuperMutant $S/SuperMutant "/home/claude/fnv/creature_src/Fallout - Meshes/meshes/creatures/smspinebreaker" > $O/SuperMutant.json &
python3 audit_twist.py Zetan $S/Zetan /home/claude/fnv/assets/meshes/dlc05/creatures/alien > $O/Zetan.json &
python3 audit_twist.py Ghost $S/Ghost /home/claude/fnv/ghost_src/meshes/nvdlc01/creatures/ghosts /home/claude/fnv/ref_male > $O/Ghost.json &
wait
