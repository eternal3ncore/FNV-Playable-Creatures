# Playable Creatures race settings

Each creature pack carries its own settings file, `Data\NVSE\Plugins\PlayableCreatures\PlayableCreatures_<Pack>.ini`,
read by PlayableCreatures.dll (Playable Creatures Core) at startup: one section per race of that pack. Installing or
removing a pack adds or removes its file; nothing is shared between packs (the single PlayableCreatures.ini of older
releases is no longer read: delete it). The shipped files carry the keys that change something, plus FirstPersonBody=1
in every section so first person can be switched off per race - anything left out takes its default.

```
Sections whose plugin isn't loaded are skipped (logged "NOT FOUND (plugin inactive?)").
  Plugin/Race       : plugin file + race FormID (local hex, without the load-order byte)
  Skeleton          : path under Data\Meshes; every .kf in that folder (+Locomotion\, Locomotion\Hurt\) is the anim set
  Marker            : node name inside that skeleton identifying it (detects when a rebuild is needed)
  ArmorVisuals      : 0 = worn armor is never drawn on the creature (stats still apply); 1 = drawn normally
  ShowForms         : armor that stays visible even with ArmorVisuals=0 (Plugin|FormID, comma separated)
  FirstPersonForms  : armor drawn only in the 1st-person view (Pip-Boy 3000 = FalloutNV.esm|015038)
  LoopSound         : looping creature sound (SOUN, Plugin|FormID) kept on the player while alive (empty = none).
      Melee / throw / jump vocals come from the creature's animations ("Sound:" text keys), not from here.
  VoiceType         : voice type (Plugin|FormID) the player gets while in this race. Hit / death / ranged-hit voices are
      then the vanilla Hit / Death / Attack dialogue topics spoken by the player (Actor::Say, from xNVSE's OnHit /
      OnDeath events): lines = dialogue data in the race plugin, files in
      sound\voice\<plugin>\PlayerVoiceMale|PlayerVoiceFemale\. Pain 60 % (at most every 1.5 s), gun / launcher
      hit bark 25 % (at most every 6 s), death always. Every race has every weapon type and may wear armor.
  ImpactMaterial    : blood/impact material of the player while in this race (the creature record's value):
      6 Organic (red, human), 10 OrganicBug (Zetans, Ghost People), 11 OrganicGlow. Empty = unchanged.
  Race abilities are on the RACE records ("<Race> Physiology": the creature's own effects + Radiation Immunity),
        not in this file; the DLL doesn't add or remove abilities.
  RadImmune         : 1 = the player's resistance cap (fPlayerMaxResistance, 85) is raised to 100 while in the race
                      (put back when leaving it), so the race ability's +100 Rad Resistance is full immunity
  ChildRace         : the race's child version (local FormID, same plugin): Tranquility Lane's AgeRace -1 puts
                      the player in it; it uses this section's skeleton, voices and traits
  CloudImmune       : 1 = Dead Money's toxic cloud never starts for you (its trigger, damage and hardcore Villa scripts
                      don't run while you're this race: no damage, screen effect, weather change or message)
  Faction           : the species' in-game factions, Plugin|FormID[,Plugin|FormID...] (up to 4); a plugin that
                      isn't loaded is skipped (one ini serves New Vegas and TTW)
  BodyPartData      : Plugin|FormID of the body part data (BPTD: gore, dismemberment, VATS parts) the race uses;
                      empty = the player's default
  LockedItems       : Plugin|FormID[,...] (up to 8): items refused, and unequipped at load, until UnlockGlobal= is 1 or
                      more (Securitrons: the Mk II grenade launcher and missiles until the Securitron upgrade)
  UnlockGlobal      : Plugin|FormID of the GLOB that unlocks LockedItems
  LockedMessage     : message shown when a locked item is refused. Default "You can't use that yet."
  FaceEyes          : Plugin|FormID[,...] (up to 16): eyes forms picked in the race menu; the n-th one shows the n-th
                      FaceNodes node and hides the others (Securitrons: the face screens)
  FaceNodes         : skeleton node names, comma separated, in the FaceEyes order
  UnarmedEffect     : Plugin|FormID of an enchantment the player's unarmed attacks carry while in the race (as a
                      creature's EITM), fired on UnarmedEffectAnim (Glowing One: its radiation burst; Ghost People:
                      the gas spray's knockout). The engine casts it on the actor the attack hit (bare fists; with
                      weapons see UnarmedEffectWeapons): Touch effects land on that target only, Self effects on the player. On a
                      directional power attack (0x5D-0x60) it also fires on that direction's unarmed special-move perk
                      attack (Legion Assault / Ranger Takedown / Khan Trick: AttackCustom1 / 2 / 4 / 5Power)
  UnarmedEffectAnim : the attack animation group the effect fires on (as a creature's EAMT, e.g. 0x5E = AttackBackPower, 0x5D =
                      AttackForwardPower, 0xFF = every attack)
  (The next three keys act only with UnarmedEffect= set; every race's settings list them, 0 = off. Ghost People: on.)
  UnarmedEffectWeapons : 1 = the effect also with an unarmed or melee weapon equipped (its forward power attack is
                      the AttackCustom group the weapon plays in its place; the weapon's own enchantment still applies);
                      0 (default) = bare fists only. Ghost People: 1
  UnarmedEffectReachMult : that attack's melee reach is at least the unarmed reach (64) x this (the hit test adds half
                      of it to both actors' radii); that attack (and what stands for it) only; 0 (default) = vanilla. Ghost People: 3
  UnarmedEffectCone : that attack's hit cone is at least this, degrees either side of the facing (vanilla: forward /
                      standing power 40, side / back 100, Custom1 50, others 35); same scope; 0 (default) = vanilla. Ghost People: 60
  GhostMoveForms    : the GhostMoves forms: hop spell, search spell, search idle, hop-left idle, hop-right idle,
                      back-dodge idle (back + jump with a weapon out; optional - without it that jumps normally),
                      back-dodge spell (cast with the dodge; optional - without it the hop spell)
  JoinFaction       : 1 = the player joins those factions (rank 0) while in the race and leaves them on a race
                      change, so the species treats you as its own; 0 (default) = the factions are never touched
  GiveItems         : Plugin|FormID[,...] (up to 4): items given to the player, one each and not equipped, when
                      the race menu closes (an existing copy is replaced, never stacked). Robots: their own weapon
  GivePerks         : Plugin|FormID[,...] (up to 4): perks the player gets when the race menu closes, if not already
                      had (never a second rank; not removed on a later race change). Every non-robot race:
                      Terrifying Presence (FalloutNV.esm|10C6CD); robots list the key empty
  TauntIdles        : Plugin|FormID[,...] (up to 4): back + jump plays the next of these idles (in turn), the player
                      held still while it plays; races without GhostMoves only. Super Mutants / Nightkin / the
                      Capital super mutants: their own intimidation idles
  NoFallDamage      : 1 = no fall damage, the engine's rule for flying creatures (vanilla eyebots carry the
                      "Flies" flag). Default 0
  GhostMoves        : 1 = Ghostification's ghost moves on the jump key (decided before a jump starts, so no jump):
                      jump while strafing = hop (dodge, brief ghosting; slow motion + crit only in combat),
                      jump while walking backward with the weapon holstered = search (trash pick, loot after 5 s)
  GhostEssential    : 1 = the player is always essential (lethal damage knocks it down, it gets back up); a hit that
                      leaves a limb crippled kills, with that limb dismembered. Needs PlayerEssentialFix.dll (vanilla
                      leaves an essential player ragdolled).
  ResistCap         : the player's resistance cap (fPlayerMaxResistance, 85) while in the race; 100 = the race
                      ability's +100 resistance is full immunity (Spore Carrier poison; RadImmune already means 100)
  BlockAnimOverrides: 1 (default) = kNVSE animation overrides (AnimGroupOverride folders, SetActorAnimationPath) never
                      replace this race's own animations; 0 = they apply as they would to a human
  SneakCamera       : share of the 1st-person crouch drop the 3rd-person camera takes while sneaking; 1 (default) = the
                      full drop, 0 = none (robots, super mutants), any value in between
  ShowInRaceMenu    : 1 (default) = the race is listed in the race menu; 0 = hidden (its RACE playable flag is cleared
                      at startup; a character already of that race keeps it)
  FirstPersonBody   : 1 (default) = in 1st person you see the creature's own body (its head hidden, the camera at
                      FirstPersonNode + FirstPersonOffset) instead of the human 1st-person arms; 0 = off (the vanilla
                      1st-person view, the creature body stretched over the human arms)
  FirstPersonNode   : skeleton node the 1st-person camera follows. Default Bip01 Head
  FirstPersonHide   : node shrunk away in 1st person (with its children). Default Bip01 Head; empty = none
  FirstPersonOffset : camera offset from FirstPersonNode: right, forward, up (in the actor's heading frame).
                      Default 0,-12,-12 (behind and below the head, the hands in view)
```
