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

## Credits

By i3ncore ([Nexus Mods](https://www.nexusmods.com/profile/i3ncore/)). Built on xNVSE and JIP LN.
Fallout: New Vegas, Fallout 3 and their DLC are © Bethesda Softworks.
