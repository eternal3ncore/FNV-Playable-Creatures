"""Capital Wasteland super mutant (TTW: Fallout 3's Creatures\\SMSpineBreakerDC, the same skeleton as New Vegas'
SMSpineBreaker bone for bone) - the Super Mutant config on Fallout 3's own animation set (Fallout3 - Meshes.bsa +
TaleOfTwoWastelands - Main.bsa, the latter loading over the former). Used by assemble_smdc.py (sneak locomotion)."""
from creatures.supermutant import *          # noqa: F401,F403
NAME = 'Super Mutant (Capital)'
ANIM_SRC = '/home/claude/fnv/creature_src_ttw/smspinebreakerdc'
SKELETON = ANIM_SRC + '/skeleton.nif'
