# PlayableCreatures.ini keys

Reference for the race sections read by PlayableCreatures.dll. The shipped ini only carries keys that change something - anything left out takes its default.

```
Playable Creatures — creature race registry (read by PlayableCreatures.dll at startup)
One section per playable creature race.
Two plugins, use ONE of them: PlayableCreatures.esp (Fallout: New Vegas) or PlayableCreaturesTTW.esp (Tale of Two
  Wastelands: every race below, including the PlayableCreatures.esp ones under the same ids). A reference to
  PlayableCreatures.esp|<id> resolves to PlayableCreaturesTTW.esp|<id> when only the TTW plugin is loaded, so the
  sections below serve both. Sections whose plugin isn't loaded are skipped (logged "NOT FOUND (plugin inactive?)").
  Plugin/Race       : plugin file + race FormID (local hex, without the load-order byte)
  Skeleton          : path under Data\Meshes; every .kf in that folder (+Locomotion\, Locomotion\Hurt\) is the anim set
  Marker            : node name inside that skeleton identifying it (detects when a rebuild is needed)
  AllowArmor        : 1 = armor/clothing can be equipped (stats apply); 0 = refused
  ArmorVisuals      : 0 = worn armor is never drawn on the creature (stats still apply); 1 = drawn normally
  ShowForms         : armor that stays visible even with ArmorVisuals=0 (Plugin|FormID, comma separated)
  FirstPersonForms  : armor drawn only in the 1st-person view (Pip-Boy 3000 = FalloutNV.esm|015038)
  WeaponAnims       : weapon animation types the creature has anims for (H2H 1HM 2HM 1HP 2HR 2HA 2HH 2HL 1GT 1MD 1LM)
  AllowForms        : items always allowed to be equipped
  SilentBlockForms  : items refused without an on-screen message
  HitSound / DeathSound / RangedAttackSound / LoopSound : creature voice SOUNs (Plugin|FormID) played on the player
      by the DLL from xNVSE's OnHit / OnDeath events (no polling). RangedAttackSound = bark when the player lands a
      hit with a gun/launcher. LoopSound = looping creature sound kept on the player while alive (empty = none).
      Melee / throw / jump vocals come from the creature's animations ("Sound:" text keys), not from here.
  HitSoundChance / HitSoundCooldown (ms), RangedAttackSoundChance / RangedAttackSoundCooldown (ms): 0-100 %, min gap
  VoiceType         : voice type (Plugin|FormID) the player gets while in this race. When set, hit / death / ranged-hit
      voices are the vanilla Hit / Death / Attack dialogue topics spoken with the Say command (lines = dialogue data in
      the race plugin) instead of the *Sound SOUNs; chances and cooldowns above still apply.
  DialogueVoice     : 1 = hit / death / ranged-hit voices are the vanilla Hit / Death / Attack topics spoken by the
      player (Actor::Say): lines = dialogue data in the race plugin (conditioned on the race), files in
      sound\voice\<plugin>\PlayerVoiceMale|PlayerVoiceFemale\. VoiceType can stay empty.
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
  HideWeapon        : 1 = the equipped weapon is never drawn on the 3rd-person body (still equipped and used; the
                      1st-person view still shows it). Set for the races on all fours. Default 0
  JoinFaction       : 1 = the player joins those factions (rank 0) while in the race and leaves them on a race
                      change, so the species treats you as its own; 0 (default) = the factions are never touched
  GiveItems         : Plugin|FormID[,...] (up to 4): items given to the player, one each and not equipped, when
                      the race menu closes (an existing copy is replaced, never stacked). Robots: their own weapon
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
```
