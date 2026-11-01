cd /home/claude/fnv/anim
for r in Zetan Ghost Ghoul SuperMutant Swampfolk Hillfolk Trog; do
  python3 hinge_fix.py /home/claude/fnv/audit/fixed/$r /home/claude/fnv/audit/$r.json > /home/claude/fnv/audit/fix_$r.log 2>&1 &
done
wait
for r in Zetan Ghost Ghoul SuperMutant Swampfolk Hillfolk Trog; do echo "$r: $(tail -n 1 /home/claude/fnv/audit/fix_$r.log) errors=$(grep -c ERROR /home/claude/fnv/audit/fix_$r.log)"; done
# holster spots: races whose weapon sets borrow equip / unequip / holster from one other type get the human
# holster bone + position per weapon type (anim/holster_fix.py; needs the human ref_male KFs + characters\_male\skeleton.nif)
for r in Ghost Ghoul Hillfolk; do
  python3 holster_fix.py /home/claude/fnv/ref_male /home/claude/fnv/ref_human_skeleton.nif /home/claude/fnv/audit/fixed/$r --apply > /home/claude/fnv/audit/holster_$r.log 2>&1
done
# sneak crouch: sneak files copied from standing ones get the race's sneak-idle lower body, upper body kept
# in world orientation (anim/sneak_fix.py; audit with anim/sneak_audit.py). Trog / Tunneler excluded (2-unit crouch).
for r in Ghost Ghoul SuperMutant Zetan Swampfolk Hillfolk; do
  python3 sneak_fix.py /home/claude/fnv/audit/fixed/$r --apply > /home/claude/fnv/audit/sneak_$r.log 2>&1
done
