# Playable Creatures: races and features

Install **Playable Creatures Core** (PlayableCreatures.dll, for xNVSE) and then any of the creature packs below. Each pack has its own plugin, `PlayableCreatures_<Pack>.esp`, and its own settings file,
`NVSE\Plugins\PlayableCreatures\PlayableCreatures_<Pack>.ini`. The single `PlayableCreatures.ini` of older releases
is no longer needed once your packs are updated and can be deleted. Pick a race in the normal race menu (character
creation or `showracemenu`).

New Vegas packs also work in Tale of Two Wastelands. The packs marked TTW need Tale of Two Wastelands. The two TTW
add-ons need their base pack too.

## Every race

- Its own skeleton, full animation set and third-person camera, applied as soon as the race menu closes (no
  save/reload).
- Its own hit, death and attack voices, footsteps and blood type.
- Block animations for unarmed and melee.
- Furniture use (chairs, stools, the Vault 112 pods) and getting up after a knockdown.
- Its own animations for drinking from water, Cannibal, Mister Sandman kills and stimpaks (robots: a placeholder
  for Cannibal; robots without a seated pose float onto chairs and stools).
- The creature's own body parts for gore, dismemberment and VATS.
- Armor can be worn for its stats but isn't drawn (except where noted).
- Human animation overrides from kNVSE animation mods don't apply to creature races.
- First person shows the creature's own body (its head hidden, the view just behind it); Ghost People keep the
  vanilla first-person view (their skeleton is human). `FirstPersonBody=0` / `1` in a race's section of its pack's
  settings file switches it.

## Zetan
`PlayableCreatures_Zetan.esp`
*Zetan, Zetan (Helmet)*
- All weapon types.

## Ghost People
`PlayableCreatures_GhostPeople.esp`
*Hooded, Unhooded*
- All weapon types.
- Immune to radiation and the Sierra Madre toxic cloud.
- Always essential: lethal damage knocks you down and you get back up. A crippled limb kills, with that limb
  blown off.
- Ghost moves on the jump key: a sideways hop when strafing, and a search when moving backward with your weapon
  holstered (sneaking or not).
- Starts with a bottomless **Throwing Knife Spear** (Dead Money's best, can't be dropped, weightless); its critical
  hits knock the target down.
- Starts with a built-in recharging **Ghost Gas**: sprays the Sierra Madre gas (a heavy weapon, flamer range);
  poison damage over time, resisted by Poison Resistance.
- **Gas spray**: the back power attack steps in and sprays gas from the mask; the one target it hits is knocked
  out for a few seconds (not an area blast). Bare fists, unarmed and melee weapons; the same with Ranger Takedown.
  The forward power attack is the Ghost's charging lunge.
- Heavy weapons are cast from the open palm: the gun isn't drawn, and the shots, gas, flames or beams leave just in
  front of the hand (no backpack either).
- Constant breathing wheeze.
- Needs **PlayerEssentialFix** (separate download): without it an essential player stays ragdolled after getting
  back up.

## Feral Ghouls
`PlayableCreatures_FeralGhouls.esp`
*Feral Ghoul, Glowing One*
- All weapon types.
- Immune to radiation.
- **Glowing One:** the backward power attack releases its radiation burst.

## Super Mutants
`PlayableCreatures_SuperMutants.esp`
*Super Mutant, Nightkin*
- All weapon types.
- One-handed melee weapons swing with its unarmed attacks; the weapon isn't drawn.
- Immune to radiation.
- Wear their own super mutant armor, which is drawn on the body.
- **Nightkin:** Stealth Boy cloak while sneaking.

### TTW add-on: `PlayableCreatures_SuperMutantsTTW.esp`
- **Capital Wasteland super mutants:** Super Mutant, Brute and Master, with four Capital armors and their own
  voices. Brute and Master are hidden from the race menu by default.
- They move and fight with Fallout 3's own super mutant animations where those differ from New Vegas': idle, walk,
  run, strafes, unarmed and melee attacks, grenade throws, and Fallout 3's extra rifle / assault rifle / heavy weapon /
  launcher attacks and reloads.

## Tunnelers
`PlayableCreatures_Tunnelers.esp`
*Tunneler, Spore Carrier*
- All weapon types. Weapons aren't drawn: every gun fires from its mouth as its bite, the shot leaving as the jaws open; grenades and mines are thrown and placed with its claws.
- Uses chairs, stools and pods: Core keeps the game from treating this short a creature as a child.
- **Spore Carrier:** immune to poison.

## Eyebot
`PlayableCreatures_Eyebot.esp`
- Built-in recharging laser; can also fire guns. Weapons aren't drawn: every shot leaves its laser.
- Melee weapons, one- and two-handed, swing with its unarmed attacks; the weapon isn't drawn.
- No fall damage.
- Hovers lower when sneaking.
- Immune to radiation and poison.

## Securitron
`PlayableCreatures_Securitron.esp`
*Securitron, Securitron Mk II*
- Built-in recharging machine gun, laser, grenade launcher and shoulder missiles; can also fire guns.
- Weapons aren't drawn: pistols and automatics fire from the machine gun arm, rifles from the laser arm, launchers,
  grenades and mines from the grenade launcher arm, heavy weapons from the shoulder missiles.
- Melee weapons, one- and two-handed, swing with its unarmed attacks; the weapon isn't drawn.
- **Securitron:** damage threshold +20. After the Securitron upgrade (Fortification Hill): +30, +55 health and
  self-repair. The missiles and grenade launcher need the upgrade.
- **Securitron Mk II:** the infantry face, damage threshold +30. Hidden from the race menu by default.
- Immune to radiation and poison.

## Protectron
`PlayableCreatures_Protectron.esp`
- Built-in recharging hand laser and head laser; can also fire guns. Weapons aren't drawn: guns fire from the hand
  laser, launchers from the head laser.
- Melee weapons, one- and two-handed, swing with its unarmed attacks; the weapon isn't drawn.
- Hovers on its back jet when running.
- Immune to radiation and poison.

## Robobrain
`PlayableCreatures_Robobrain.esp`
- Built-in recharging laser and Mesmetron; can also fire guns. Weapons aren't drawn: guns fire from the laser arm,
  launchers from the head.
- Melee weapons, one- and two-handed, swing with its unarmed attacks; the weapon isn't drawn.
- Immune to radiation and poison.

### TTW add-on: `PlayableCreatures_RobobrainTTW.esp`
- Female Robobrains use the Capital Wasteland female robobrain voice.

## Mister Handy
`PlayableCreatures_MisterHandy.esp`
*Mister Handy, Mister Gutsy*
- All weapon types; two-handed melee weapons swing like one-handed ones. Weapons aren't drawn.
- **Mister Handy:** built-in recharging flamer and buzzsaw; guns, grenades and mines fire from the flamer arm.
- **Mister Gutsy:** built-in recharging flamer and plasma gun; heavy weapons fire from the flamer arm, every other gun
  from the plasma arm; the pincer claw for melee.
- No fall damage.
- Immune to radiation and poison.

## Sentry Bot
`PlayableCreatures_SentryBot.esp`
- Built-in recharging gatling laser and missile launcher; can also fire guns. Weapons aren't drawn: guns fire from the
  gatling arm, launchers, grenades and mines from the missile pod.
- Melee weapons, one- and two-handed, swing with its unarmed attacks; the weapon isn't drawn.
- Immune to radiation and poison.

## Deathclaws
`PlayableCreatures_Deathclaw.esp`
*Deathclaw, Deathclaw Alpha (the Alpha Male, or the Mother as female), Legendary Deathclaw*
- All weapon types.
- Fights with its claws: left and right swings, forward, side, standing and back power attacks, and sneak
  attacks (crouched).
- Melee weapons swing with its own claw attacks; the weapon isn't drawn.
- Guns aren't drawn: every gun fires from its mouth, the jaw opening on each shot (aim up and down with the head).
  Shots land on the crosshair, also with 3rd Person Aim Fix.
- Grenades and mines are thrown and placed with its claws.
- Damage threshold +15 (the deathclaw's own).
- **Young Deathclaw:** the child race (smaller, damage threshold +5).

## Lakelurks
`PlayableCreatures_Lakelurks.esp`
*Lakelurk, Lakelurk Alpha*
- All weapon types.
- Starts with its **Shriek**: the lakelurk's sonic blast from the mouth (Perception -10 for 10 s on the target, 50 extra
  damage). It recharges by itself (one shot every 3 s, nothing to carry), can't be dropped, weighs nothing.
- Fights with its claws: left and right swipes, standing and forward power attacks, and sneak attacks (crouched).
- Melee weapons swing with its own claw attacks; the weapon isn't drawn.
- Guns aren't drawn: every gun fires as its shriek, from the mouth.
- Grenades and mines are thrown and placed with its claws.
- Breathes underwater.
- **Young Lakelurk:** the child race (smaller).

## TTW-only packs

### Swampfolk
`PlayableCreatures_Swampfolk.esp`
*Brawler, Scrapper, Creeper, Tracker, Bruiser*
- All weapon types.
- Immune to radiation.
- Tracker and Bruiser have the larger, long-armed build.

### Trogs
`PlayableCreatures_Trogs.esp`
*Trog, Trog Brute, Trog Savage*
- All weapon types. Weapons aren't drawn: every gun fires from its mouth as its bite, the shot leaving as the jaws open; grenades and mines are thrown and placed with its claws.
- Uses chairs, stools and pods: Core keeps the game from treating this short a creature as a child.
- Brute and Savage are hidden from the race menu by default.

### Mirelurks
`PlayableCreatures_Mirelurks.esp`
*Mirelurk, Mirelurk Hunter, Nukalurk*
- All weapon types: claw strikes and four power attacks; melee weapons strike with its claws (weapon not
  drawn); guns aren't drawn - every gun fires from its mouth, with its own lunge, claws raised.
- Grenades and mines: launched from its right pincer with its claw strike.
- Blocks with both pincers raised before its face.
- Damage threshold +5, breathes underwater.
- Nukalurk: its claws carry radiation (Rad Poisoning, 10 rads a second for 3 s, unless the target resists radiation).
- Sneaks crouched; on chairs and stools it settles its shell onto the seat.

A hidden race can be shown by setting `ShowInRaceMenu=1` in its section of the pack's settings file.
