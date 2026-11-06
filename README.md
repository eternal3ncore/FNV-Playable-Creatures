# FNV Playable Creatures

Play Fallout: New Vegas as a creature. Creature races are picked in the normal race menu (character creation or
`showracemenu`). Each one gets its own skeleton, animation set and third-person camera, attached at runtime with
no save/reload. Everything is event and hook driven: no per-frame scripts, polling or timers.

## Requirements

- Fallout: New Vegas 1.4.0.525 (the DLL uses runtime addresses of this exe).
- [xNVSE](https://github.com/xNVSE/NVSE).
- JIP LN NVSE Plugin, for the live race switch. Without it, the new skeleton applies after a save and reload.
- kNVSE is optional. When it is installed, the DLL keeps kNVSE's human animation overrides off creature players.
- For `PlayableCreaturesTTW.esp`: Tale of Two Wastelands 3.4.

## Purpose
Creature skeleton for the player. The player is always an NPC_, and the engine picks the human skeleton for it. The DLL swaps in the creature’s skeleton (and with it the whole animation folder) per race. This is the core of the project.
Rebuilding the player right after the race menu. When the menu closes, the DLL rebuilds the player’s 3D through JIP’s pipeline, so the new body appears without a reload.
3rd-person camera height. The engine places the camera from the human first-person skeleton’s height, whatever body you have. The DLL uses each skeleton’s own Camera3rd node instead.
First-person creature body. It shows the creature’s own body with the head hidden, instead of human arms (the FirstPersonBody setting).
Hidden armor that still counts. With ArmorVisuals=0, armor never gets a model, but its DT and effects still apply.
No fall damage. The engine only exempts creatures with the “Flies” flag, and the player is never a creature. This covers the robots that hover or fly (Eyebot, Mister Handy and similar).
Short creatures not treated as children. The engine calls anything under a certain height a child. Tunnelers, Spore Carriers and Trogs were refused furniture, including the Vault 112 pods.
Ghost moves on the jump key. The hop and the search have to replace the jump before it starts, and a script can’t cancel a jump.
Crash guard. It prevents the Securitron crash about 2 seconds after the race menu (a half-built ragdoll controller).
Keeping the creature’s animations under kNVSE. It stops kNVSE’s human animation overrides from replacing the creature’s own. This only matters if kNVSE animation packs are installed.
The player record is shared by every race, so these values have to be swapped in while you’re in the race and restored afterwards. Putting them in a plugin would change human players too and conflict with other mods that edit the player.
Combat voice type (Hit / Death / Attack lines).
Blood and impact material (ImpactMaterial).
Body part data: gore, dismemberment and limb names (BodyPartData).
Unarmed attack effect: the Glowing One’s burst, the Nukalurk’s radiation and the new Ghost gas knockout (UnarmedEffect / UnarmedEffectAnim).
Resistance cap raised to 100 for radiation-immune races only. Changing it in a plugin would raise it for everyone.
Dead Money toxic cloud immunity. The DLL skips the cloud scripts for the player instead of overriding Dead Money’s script records.
Securitron face screens. The face chosen in the race menu shows its screen node on the skeleton and hides the others.
Locked items. The Securitron’s upgrade weapons are refused before they’re equipped, until the upgrade is done. A script could only unequip them afterwards.

## Credits

By i3ncore ([Nexus Mods](https://www.nexusmods.com/profile/i3ncore/)). Built on xNVSE and JIP LN.
Fallout: New Vegas, Fallout 3 and their DLC are © Bethesda Softworks.
