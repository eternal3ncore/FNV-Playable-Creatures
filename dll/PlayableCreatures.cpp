// Playable Creatures — xNVSE plugin (Fallout: New Vegas 1.4.0.525)
// Event/hook driven only: no per-frame code, no timers.
//
//  1. Skeleton: TESNPC's TESModel::GetModelPath vtable slot (0x104A1A4[5]) -> creature race => creature skeleton.
//     The engine loads that skeleton and every KF in its folder, so the creature's own animation set comes with it.
//  2. Live switch: RaceSexMenu destructor (0x1075974[0]) -> enforce the creature's equipment policy, then rebuild the
//     player's 3D immediately through JIP LN's UpdatePlayer3D pipeline (flag 0x5F|=1 + ModelLoader::QueueReference).
//     JIP's QueuedPlayer/GeneratePlayerNode patches are what make a mid-game player rebuild clean (1st-person node copy,
//     anim-data teardown, weapon anim re-sync); without JIP the vanilla queue ignores the request.
//  3. Locked items: Actor::EquipItem (0x88C650) entry detour, player only: LockedItems= stay refused until their
//     UnlockGlobal= is set (every race has every weapon type and may wear armor).
//  5. Creature players keep their own anim set: kNVSE AnimGroupOverride results are bypassed for the player's
//     3rd-person AnimData while in a creature race (guards on the 11 anim-map lookup sites, chained); and on the
//     4 sequence-play sites (AnimData::MorphOrBlendToSequence), where kNVSE swaps in its overrides (BlockAnimOverrides=1).
//  4. Armor visuals: TESNPC::AddItemToBiped (0x6061B0) entry detour: for creature races with ArmorVisuals=0 worn
//     armor never gets a model in the biped, so the creature body stays as-is while the armor still counts.
//  6. Looping voice: an optional looping SOUN (LoopSound=, e.g. Ghost People's wheeze) follows the player's 3D and is
//     (re)started when that 3D is set, stopped on death / race change / leaving the game.
//     Melee / throw / jump vocals are anim text keys ("Sound: <SOUN>") in the creature's KFs, not DLL code.
//  7. Voice types: a profile with VoiceType= gives the player that voice type while in the race (restored
//     afterwards) and speaks the vanilla combat topics (Hit / Death / Attack) through the engine's Actor::Say on xNVSE's
//     native OnHit / OnDeath events
//     (the function the Say command uses for immediate speech: picks the topic's INFO by its conditions, builds the
//     voice file path from the voice type and plays it) - the lines themselves are ordinary
//     dialogue data (in each family plugin, PlayableCreatures_<Family>.esp), so they are edited like any NPC voice.
//  9. Race traits: RadImmune=1 -> a radiation-immunity ability (+100 Rad Resistance, the race's own ability) is
//     given while in the race and the player's resistance cap (fPlayerMaxResistance, 85) is raised to 100;
//     CloudImmune=1 -> Dead Money's toxic cloud scripts (NVDLC01ToxicCloudSCRIPT / NVDLC01GlobalToxicDamageSCRIPT) do no
//     damage to the player (their DamageActorValue calls are filtered by script); GhostEssential=1 -> Dead Money's
//     NVDLC01GhostSCRIPT for the player: essential, "semi-dead" when downed (death vocal, limbs to 10, killable by melee /
//     pistol hits or a crippled limb, with dismemberment), back up and essential again on revive. The revive itself needs
//     PlayerEssentialFix.dll (vanilla leaves an essential player ragdolled); its Downed/Revived messages drive this.
// 10. CloudImmune skips Dead Money's three toxic-cloud scripts (Script::Execute) instead of filtering their damage
//     (no cloud effects at all); Faction= the species' in-game factions, joined while in the race only with JoinFaction=1.
// 11. GhostMoves=1: Ghostification's ghost moves on the jump key, decided before any jump starts (see below).
// 12. First person: the creature's own 3rd-person body is shown (head hidden, camera at FirstPersonNode +
//     FirstPersonOffset) instead of the human 1st-person skeleton; on by default, FirstPersonBody=0 per race turns it off.
// 13. UnarmedEffect= on a directional power attack also fires on that direction's unarmed special-move perk attack
//     (Legion Assault -> AttackCustom1Power for AttackForwardPower, etc.). Per race, off unless set (Ghost People: on):
//     UnarmedEffectWeapons=1 the effect also on hits with an unarmed / melee weapon (its forward power attack stands
//     for AttackForwardPower), UnarmedEffectReachMult= / UnarmedEffectCone= that attack's minimum reach / hit cone.
//  8. Blood: ImpactMaterial= gives the player's base the creature's impact material while in the race
//     (TESNPC+0x1E4, the NPC_/CREA NAM4 field: 6 Organic = red, 10 OrganicBug, 11 OrganicGlow); weapons then
//     use their own impact data for that material (spray + decals), exactly as they do on the creature.
#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <stdarg.h>
#include <stdlib.h>
#include <math.h>

typedef uint32_t UInt32; typedef uint8_t UInt8; typedef uint16_t UInt16; typedef int32_t SInt32;

// ---------------- xNVSE interface (subset) ----------------
struct PluginInfo { UInt32 infoVersion; const char* name; UInt32 version; };
struct NVSEInterface {
	UInt32 nvseVersion, runtimeVersion, editorVersion, isEditor;
	void* RegisterCommand; void* SetOpcodeBase;
	void* (*QueryInterface)(UInt32 id);
	UInt32 (*GetPluginHandle)(void);
};
struct NVSEMessage { const char* sender; UInt32 type; UInt32 dataLen; void* data; };
typedef void (*NVSEEventCallback)(NVSEMessage*);
struct NVSEMessagingInterface {
	UInt32 version;
	bool (*RegisterListener)(UInt32 listener, const char* sender, NVSEEventCallback handler);
};
enum { kInterface_Console = 1, kInterface_Messaging = 2, kInterface_Script = 6, kInterface_EventManager = 8 };
struct NVSEConsoleInterface {                  // xNVSE PluginAPI.h
	UInt32 version;
	bool (*RunScriptLine)(const char* buf, void* object);
	bool (*RunScriptLine2)(const char* buf, void* object, bool bSuppressConsoleOutput);
};
struct NVSEScriptInterface {                   // xNVSE PluginAPI.h order
	void* CallFunction; void* GetFunctionParams; void* ExtractArgsEx; void* ExtractFormatStringArgs;
	bool (*CallFunctionAlt)(void* funcScript, void* callingObj, UInt8 numArgs, ...);
	void* (*CompileScript)(const char* scriptText);
};
typedef void (*NativeEventHandler)(void* thisObj, void* parameters);
struct NVSEEventManagerInterface {             // xNVSE PluginAPI.h order
	void* RegisterEvent; void* DispatchEvent; void* DispatchEventAlt;
	bool (*SetNativeEventHandler)(const char* eventName, NativeEventHandler func);
	bool (*RemoveNativeEventHandler)(const char* eventName, NativeEventHandler func);
};
enum { kMessage_PostLoad = 0, kMessage_ExitToMainMenu = 2, kMessage_PreLoadGame = 6, kMessage_PostLoadGame = 8, kMessage_PostPostLoad = 9,
       kMessage_NewGame = 14, kMessage_DeferredInit = 18, kMessage_OnRefSet3D = 26 };
static const UInt32 kRuntime_1_4_0_525 = 0x040020D0;
static const UInt32 kPluginVersion = 98;

// ---------------- engine (1.4.0.525) ----------------
static const UInt32 kVtbl_TESNPC_TESModel = 0x0104A1A4, kAddr_TESNPC_GetModelPath = 0x00601C30;
static const UInt32 kVtbl_RaceSexMenu = 0x01075974, kAddr_RaceSexMenu_Dtor = 0x007AC530;
static const UInt32 kPtr_FormMap = 0x011C54C0;             // NiTPointerMap<UInt32,TESForm*>* (runtime form table)
static const UInt32 kAddr_QueueReference = 0x00444850;     // ModelLoader::QueueReference(ref, 1, 0)
static const UInt32 kAddr_EquipItem = 0x0088C650, kAddr_UnequipItem = 0x0088C790;
static const UInt32 kAddr_QueueUIMessage = 0x007052F0;
static const UInt32 kAddr_AddItemToBiped = 0x006061B0;
static const UInt32 kSlot_QueuedPlayerRun = 0x01016DB8, kAddr_VanillaQueuedPlayerRun = 0x00441C30;
static const UInt32 kPtr_DataHandler = 0x011C3F2C, kPtr_ModelLoader = 0x011C3B3C, kPtr_Player = 0x011DEA3C;
static const UInt8 kFormType_Race = 0x0C, kFormType_SOUN = 0x0D, kFormType_ARMO = 0x18, kFormType_WEAP = 0x28, kFormType_VTYP = 0x5D, kFormType_DIAL = 0x45, kFormType_SPEL = 0x14, kFormType_GLOB = 0x06, kFormType_Perk = 0x56;

// ---------------- logging ----------------
static FILE* g_log = nullptr;
static void Log(const char* fmt, ...) {
	if (!g_log) return;
	va_list a; va_start(a, fmt); vfprintf(g_log, fmt, a); va_end(a);
	fputc('\n', g_log); fflush(g_log);
}

// ---------------- creature profiles ----------------
struct FormRef { char plugin[64]; UInt32 localID; UInt32 fid; };
static const UInt32 kPtr_DefaultBodyPartData = 0x011CAFEC;   // DefaultBodyPartData (form 0x1D), set at data load (0x5E53E6)
struct Profile {
	char section[64], plugin[128], skeleton[260], marker[64];
	char ini[MAX_PATH];             // the config file the section came from (FirstPerson* keys are read again from it)
	UInt32 localID;
	void* race;
	bool armorVisuals;              // 0 = worn armor keeps its stats but is never drawn on the creature
	FormRef show[16]; int numShow;     // armor that stays visible even when armorVisuals=0
	FormRef show1st[16]; int numShow1st; // armor drawn only in the 1st-person view (e.g. Pip-Boy, needed to read it)
	FormRef loopSnd;                // LoopSound= - looping SOUN on the player's 3D
	FormRef voiceType;              // BGSVoiceType given to the player while in this race: speaks Hit / Death / Attack
	int impactMaterial;             // -1 = leave as is
	DWORD lastHit, lastRanged;
	bool radImmune, cloudImmune, ghostEssential;   // race traits (GhostCrippleDeath gone)
	FormRef childRace;              // ChildRace= - the race's child version (Tranquility Lane AgeRace -1): same profile
	void* childRacePtr;
	FormRef factions[4]; int numFactions;   // Faction= list of the species' in-game factions (missing plugins skipped)
	bool joinFaction;               // JoinFaction=1 joins them while in the race (default 0: never touched)
	bool noFallDamage;              // NoFallDamage=1 - the engine's flying-creature fall-damage exemption applies to the player
	FormRef bodyParts;              // BodyPartData= - the creature's own body part data (gore / dismemberment / VATS parts)
	FormRef give[4]; int numGive;   // GiveItems= - items handed over (one each, not equipped) when the race menu closes
	FormRef perks[4]; int numPerks; // GivePerks= - perks added (if not already had) when the race menu closes
	FormRef taunts[4]; int numTaunts; // TauntIdles= - back + jump plays the next of these idles, held still (races
	                                //   without GhostMoves)
	bool ghostMoves;                // Ghostification's hop / search on the jump key
	FormRef ghostForms[7];          // GhostMoveForms= hop spell, search spell, search idle, hop-left idle, hop-right idle,
	                                //   back-dodge idle, back-dodge spell (else the hop spell)
	FormRef locked[8]; int numLocked;  // LockedItems= - refused (and unequipped) until UnlockGlobal is 1 or more
	FormRef unlockGlobal;           // UnlockGlobal= - the GLOB that unlocks them
	char lockedMsg[128];            // LockedMessage= - shown when one is refused
	FormRef faceEyes[16]; int numFaces; // FaceEyes= - eyes forms; the n-th picks the n-th FaceNodes= node to show
	char faceNodes[16][48];         // FaceNodes= - skeleton nodes (the others are hidden)
	FormRef unarmedEffect;          // UnarmedEffect= - enchantment given to the player's unarmed attacks while in the race
	UInt16 unarmedAnim;             // UnarmedEffectAnim= - the attack animation it fires on (anim group id, e.g. 0x5E)
	bool unarmedWeapons;            // UnarmedEffectWeapons=1 - the effect also with an unarmed / melee weapon (default 0)
	float unarmedReachMult, unarmedCone;  // UnarmedEffectReachMult= / UnarmedEffectCone= - that attack's minimum reach (x the
	                                //   unarmed reach) / hit cone (degrees); 0 (default) = vanilla
	bool blockAnimOverrides;        // BlockAnimOverrides=1 (default) - kNVSE never swaps the sequence an actor in this race plays
	bool showInMenu;                // ShowInRaceMenu=0 hides the race from the race menu (RACE playable flag)
	int resistCap;                  // ResistCap= - fPlayerMaxResistance while in the race (0 = unchanged)
	float sneakCamera;              // SneakCamera= - share of the 1st-person crouch drop the 3rd-person camera takes (default 1)
	bool fpBody;                    // FirstPersonBody=1 (default; 0 = off) - 1st person shows the creature's own body
	char fpNode[64], fpHide[64];    // FirstPersonNode= camera anchor node, FirstPersonHide= node shrunk away (head)
	float fpOff[3];                 // FirstPersonOffset= right, forward, up from the anchor, in the actor's heading frame
};
static Profile g_prof[64];
static int g_numProf = 0;
static char g_gameDir[MAX_PATH];
static bool g_jip = false;

static int ParseForms(const char* s, FormRef* out, int max) {
	// "Plugin.esm|0015038, Other.esp|000801"
	int n = 0; char buf[1024]; strncpy(buf, s, 1023); buf[1023] = 0;
	for (char* t = strtok(buf, ","); t && n < max; t = strtok(nullptr, ",")) {
		while (*t == ' ') t++;
		char* bar = strchr(t, '|'); if (!bar) continue; *bar = 0;
		char* e = t + strlen(t); while (e > t && e[-1] == ' ') *--e = 0;
		strncpy(out[n].plugin, t, 63); out[n].localID = strtoul(bar + 1, nullptr, 16) & 0xFFFFFF; out[n].fid = 0; n++;
	}
	return n;
}
// FirstPerson* keys: read at startup and again each time 1st person starts, so the ini can be tuned in game.
static void ReadFirstPersonKeys(Profile& p) {
	char tmp[96];
	p.fpBody = GetPrivateProfileIntA(p.section, "FirstPersonBody", 1, p.ini) != 0;
	GetPrivateProfileStringA(p.section, "FirstPersonNode", "Bip01 Head", p.fpNode, sizeof(p.fpNode), p.ini);
	GetPrivateProfileStringA(p.section, "FirstPersonHide", "Bip01 Head", p.fpHide, sizeof(p.fpHide), p.ini);
	GetPrivateProfileStringA(p.section, "FirstPersonOffset", "0,-12,-12", tmp, sizeof(tmp), p.ini);
	p.fpOff[0] = p.fpOff[1] = p.fpOff[2] = 0.0f;
	sscanf(tmp, "%f , %f , %f", &p.fpOff[0], &p.fpOff[1], &p.fpOff[2]);
}
// One config file per creature pack: Data\NVSE\Plugins\PlayableCreatures\<pack>.ini, shipped in the pack, so adding
// or removing a pack needs no shared file.
static int LoadConfigFile(const char* ini) {
	char names[4096];
	DWORD len = GetPrivateProfileSectionNamesA(names, sizeof(names), ini);
	if (!len) { Log("config: no sections in %s", ini); return 0; }
	int added = 0;
	for (char* sec = names; *sec && g_numProf < 64; sec += strlen(sec) + 1) {
		Profile& p = g_prof[g_numProf]; memset(&p, 0, sizeof(p));
		char tmp[1024];
		strncpy(p.section, sec, 63); strncpy(p.ini, ini, MAX_PATH - 1);
		GetPrivateProfileStringA(sec, "Plugin", "", p.plugin, sizeof(p.plugin), ini);
		GetPrivateProfileStringA(sec, "Race", "", tmp, sizeof(tmp), ini); p.localID = strtoul(tmp, nullptr, 16) & 0xFFFFFF;
		GetPrivateProfileStringA(sec, "Skeleton", "", p.skeleton, sizeof(p.skeleton), ini);
		GetPrivateProfileStringA(sec, "Marker", "", p.marker, sizeof(p.marker), ini);
		p.armorVisuals = GetPrivateProfileIntA(sec, "ArmorVisuals", 1, ini) != 0;
		GetPrivateProfileStringA(sec, "ShowForms", "", tmp, sizeof(tmp), ini); p.numShow = ParseForms(tmp, p.show, 16);
		GetPrivateProfileStringA(sec, "FirstPersonForms", "", tmp, sizeof(tmp), ini); p.numShow1st = ParseForms(tmp, p.show1st, 16);
		GetPrivateProfileStringA(sec, "LoopSound", "", tmp, sizeof(tmp), ini); ParseForms(tmp, &p.loopSnd, 1);
		GetPrivateProfileStringA(sec, "VoiceType", "", tmp, sizeof(tmp), ini); ParseForms(tmp, &p.voiceType, 1);
		p.impactMaterial = GetPrivateProfileIntA(sec, "ImpactMaterial", -1, ini);
		p.radImmune = GetPrivateProfileIntA(sec, "RadImmune", 0, ini) != 0;
		p.cloudImmune = GetPrivateProfileIntA(sec, "CloudImmune", 0, ini) != 0;
		p.ghostEssential = GetPrivateProfileIntA(sec, "GhostEssential", 0, ini) != 0;
		GetPrivateProfileStringA(sec, "ChildRace", "", tmp, sizeof(tmp), ini);
		if (tmp[0]) { strncpy(p.childRace.plugin, p.plugin, 63); p.childRace.localID = strtoul(tmp, nullptr, 16) & 0xFFFFFF; }
		GetPrivateProfileStringA(sec, "Faction", "", tmp, sizeof(tmp), ini); p.numFactions = ParseForms(tmp, p.factions, 4);
		p.joinFaction = GetPrivateProfileIntA(sec, "JoinFaction", 0, ini) != 0;
		p.noFallDamage = GetPrivateProfileIntA(sec, "NoFallDamage", 0, ini) != 0;
		GetPrivateProfileStringA(sec, "GiveItems", "", tmp, sizeof(tmp), ini); p.numGive = ParseForms(tmp, p.give, 4);
		GetPrivateProfileStringA(sec, "GivePerks", "", tmp, sizeof(tmp), ini); p.numPerks = ParseForms(tmp, p.perks, 4);
		GetPrivateProfileStringA(sec, "TauntIdles", "", tmp, sizeof(tmp), ini); p.numTaunts = ParseForms(tmp, p.taunts, 4);
		GetPrivateProfileStringA(sec, "BodyPartData", "", tmp, sizeof(tmp), ini); ParseForms(tmp, &p.bodyParts, 1);
		GetPrivateProfileStringA(sec, "GhostMoveForms", "", tmp, sizeof(tmp), ini); ParseForms(tmp, p.ghostForms, 7);
		GetPrivateProfileStringA(sec, "LockedItems", "", tmp, sizeof(tmp), ini); p.numLocked = ParseForms(tmp, p.locked, 8);
		GetPrivateProfileStringA(sec, "UnlockGlobal", "", tmp, sizeof(tmp), ini); ParseForms(tmp, &p.unlockGlobal, 1);
		GetPrivateProfileStringA(sec, "LockedMessage", "You can't use that yet.", p.lockedMsg, sizeof(p.lockedMsg), ini);
		GetPrivateProfileStringA(sec, "FaceEyes", "", tmp, sizeof(tmp), ini); p.numFaces = ParseForms(tmp, p.faceEyes, 16);
		GetPrivateProfileStringA(sec, "FaceNodes", "", tmp, sizeof(tmp), ini);
		{ int n = 0; for (char* t = strtok(tmp, ","); t && n < 16; t = strtok(nullptr, ",")) {
			while (*t == ' ') t++; char* e = t + strlen(t); while (e > t && e[-1] == ' ') *--e = 0;
			strncpy(p.faceNodes[n++], t, 47); }
		  if (n < p.numFaces) p.numFaces = n; }
		GetPrivateProfileStringA(sec, "UnarmedEffect", "", tmp, sizeof(tmp), ini); ParseForms(tmp, &p.unarmedEffect, 1);
		GetPrivateProfileStringA(sec, "UnarmedEffectAnim", "0", tmp, sizeof(tmp), ini); p.unarmedAnim = (UInt16)strtoul(tmp, nullptr, 0);
		p.unarmedWeapons = GetPrivateProfileIntA(sec, "UnarmedEffectWeapons", 0, ini) != 0;
		GetPrivateProfileStringA(sec, "UnarmedEffectReachMult", "0", tmp, sizeof(tmp), ini); p.unarmedReachMult = (float)atof(tmp);
		GetPrivateProfileStringA(sec, "UnarmedEffectCone", "0", tmp, sizeof(tmp), ini); p.unarmedCone = (float)atof(tmp);
		p.ghostMoves = GetPrivateProfileIntA(sec, "GhostMoves", 0, ini) != 0;
		p.blockAnimOverrides = GetPrivateProfileIntA(sec, "BlockAnimOverrides", 1, ini) != 0;
		if (!p.plugin[0] || !p.localID || !p.skeleton[0] || !p.marker[0]) { Log("config: [%s] incomplete, skipped", sec); continue; }
		bool dup = false;
		for (int i = 0; i < g_numProf && !dup; i++)
			if (g_prof[i].localID == p.localID && !_stricmp(g_prof[i].plugin, p.plugin)) {
				Log("config: [%s] %s|%06X already set up by [%s] in %s - skipped", sec, p.plugin, p.localID, g_prof[i].section, g_prof[i].ini);
				dup = true;
			}
		if (dup) continue;
		Log("config: [%s] %s|%06X skeleton='%s' marker='%s' armorVisuals=%d show=%d",
			sec, p.plugin, p.localID, p.skeleton, p.marker, p.armorVisuals, p.numShow);
		p.showInMenu = GetPrivateProfileIntA(sec, "ShowInRaceMenu", 1, ini) != 0;
		p.resistCap = GetPrivateProfileIntA(sec, "ResistCap", 0, ini);
		GetPrivateProfileStringA(sec, "SneakCamera", "1", tmp, sizeof(tmp), ini); p.sneakCamera = (float)atof(tmp);
		ReadFirstPersonKeys(p);
		if (p.sneakCamera != 1.0f) Log("config: [%s] sneak camera drop x%.2f", sec, p.sneakCamera);
		if (p.resistCap) Log("config: [%s] resistCap=%d", sec, p.resistCap);
		Log("config: [%s] traits radImmune=%d cloudImmune=%d ghostEssential=%d", sec, p.radImmune, p.cloudImmune, p.ghostEssential);
		Log("config: [%s] loop=%06X voiceType=%06X firstPersonBody=%d", sec, p.loopSnd.localID, p.voiceType.localID, p.fpBody);
		g_numProf++; added++;
	}
	return added;
}
static void LoadConfig() {
	char dir[MAX_PATH], pat[MAX_PATH], path[MAX_PATH];
	snprintf(dir, sizeof(dir), "%sData\\NVSE\\Plugins\\PlayableCreatures\\", g_gameDir);
	snprintf(pat, sizeof(pat), "%s*.ini", dir);
	WIN32_FIND_DATAA fd;
	HANDLE h = FindFirstFileA(pat, &fd);
	if (h != INVALID_HANDLE_VALUE) {
		do {
			if (fd.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) continue;
			snprintf(path, sizeof(path), "%s%s", dir, fd.cFileName);
			int n = LoadConfigFile(path);
			Log("config: %s - %d race%s", fd.cFileName, n, n == 1 ? "" : "s");
		} while (FindNextFileA(h, &fd));
		FindClose(h);
	}
	if (!g_numProf) Log("config: no races - no pack config in %s", dir);
}


// ---------------- engine helpers ----------------
// A plugin's load index (to turn the ini's Plugin|local id into a form id): the TESFile with that name in the
// DataHandler's file list - the linked list DataHandler+0x210 (ModList.modInfoList; then the count +0x218 and the
// loadedMods array +0x21C) that xNVSE's own DataHandler::GetModIndex / LookupModByName walk, so the lookup sees
// exactly what xNVSE and other plugins see. Its load index is TESFile+0x40C (0xFF = not loaded).
// The loadedMods array itself is not read: in some setups it holds non-pointers inside its count. Each file is also
// checked to be readable memory before its name is read.
static bool Readable(const void* p, UInt32 n) {
	if ((UInt32)p < 0x10000) return false;
	MEMORY_BASIC_INFORMATION mbi;
	if (!VirtualQuery(p, &mbi, sizeof(mbi)) || mbi.State != MEM_COMMIT) return false;
	if (mbi.Protect & (PAGE_NOACCESS | PAGE_GUARD)) return false;
	if (!(mbi.Protect & (PAGE_READONLY | PAGE_READWRITE | PAGE_WRITECOPY | PAGE_EXECUTE_READ | PAGE_EXECUTE_READWRITE | PAGE_EXECUTE_WRITECOPY))) return false;
	UInt32 end = (UInt32)mbi.BaseAddress + mbi.RegionSize;
	return (UInt32)p + n <= end || Readable((const void*)end, (UInt32)p + n - end);
}
static UInt8 FindModIndex(const char* name) {
	UInt8* dh = *(UInt8**)kPtr_DataHandler;
	if (!dh) return 0xFF;
	struct Node { UInt8* data; Node* next; };
	static bool warned = false;
	int n = 0;
	for (Node* it = (Node*)(dh + 0x210); it && n < 4096; it = it->next, n++) {
		if (!Readable(it, sizeof(Node))) break;
		UInt8* m = it->data;
		if (!m) continue;
		if (!Readable(m, 0x410) || !memchr(m + 0x20, 0, MAX_PATH)) {
			if (!warned) { warned = true; Log("deps: file list entry %d = %p is not a plugin file - skipped", n, m); }
			continue;
		}
		if (!_stricmp((const char*)(m + 0x20), name)) return m[0x40C];
	}
	return 0xFF;
}
// One plugin per creature family (PlayableCreatures_<Family>.esp); each pack's config names its races' plugin and every
// form the code uses for them. A family that isn't installed leaves its sections / forms unresolved (logged).
static UInt8 GetModIndex(const char* name) { return FindModIndex(name); }
// Runtime form lookup = read the engine's form map (same as xNVSE/JIP). 0x4F9620 is the *GECK* address - never call it.
static void* LookupForm(UInt32 fid) {
	UInt8* map = *(UInt8**)kPtr_FormMap;
	if (!map || !fid) return nullptr;
	UInt32 nb = *(UInt32*)(map + 4);
	UInt8** buckets = *(UInt8***)(map + 8);
	if (!nb || !buckets) return nullptr;
	for (UInt8* e = buckets[fid % nb]; e; e = *(UInt8**)e)
		if (*(UInt32*)(e + 4) == fid) return *(void**)(e + 8);
	return nullptr;
}
static UInt32 ResolveFID(const char* plugin, UInt32 local) {
	UInt8 idx = GetModIndex(plugin);
	return idx == 0xFF ? 0 : (((UInt32)idx << 24) | local);
}
static void ResolveProfiles() {
	for (int i = 0; i < g_numProf; i++) {
		Profile& p = g_prof[i];
		UInt32 fid = ResolveFID(p.plugin, p.localID);
		void* form = LookupForm(fid);
		p.race = (form && *((UInt8*)form + 4) == kFormType_Race) ? form : nullptr;
		Log("resolve: [%s] race %08X -> %p%s", p.section, fid, p.race, p.race ? "" : "  ** NOT FOUND (plugin inactive?) **");
		// ShowInRaceMenu: the race menu lists races whose RACE DATA "Playable" flag is set (bit 0 of the DATA
		// flags; TESRace loads the 0x24-byte DATA chunk at +0x50, so the flags are at +0x70). Set here at
		// DeferredInit, before any menu opens; the flag is form data, not saved in the save game.
		if (p.race) {
			UInt32& raceFlags = *(UInt32*)((UInt8*)p.race + 0x70);
			UInt32 before = raceFlags;
			if (p.showInMenu) raceFlags |= 1; else raceFlags &= ~1u;
			Log("resolve: [%s] race menu %s (flags %X -> %X)", p.section, p.showInMenu ? "shown" : "HIDDEN (ShowInRaceMenu=0)", before, raceFlags);
		}
		for (int k = 0; k < p.numShow; k++) p.show[k].fid = ResolveFID(p.show[k].plugin, p.show[k].localID);
		for (int k = 0; k < p.numShow1st; k++) p.show1st[k].fid = ResolveFID(p.show1st[k].plugin, p.show1st[k].localID);
		if (p.voiceType.localID) {
			p.voiceType.fid = ResolveFID(p.voiceType.plugin, p.voiceType.localID);
			void* f = LookupForm(p.voiceType.fid);
			if (!f || *((UInt8*)f + 4) != kFormType_VTYP) { Log("resolve: [%s] voice type %s|%06X is not a loaded VTYP - disabled", p.section, p.voiceType.plugin, p.voiceType.localID); p.voiceType.fid = 0; }
			else Log("resolve: [%s] voice type %08X", p.section, p.voiceType.fid);
		}
		p.childRacePtr = nullptr;
		if (p.childRace.localID) {
			p.childRace.fid = ResolveFID(p.childRace.plugin, p.childRace.localID);
			void* f = LookupForm(p.childRace.fid);
			if (f && *((UInt8*)f + 4) == kFormType_Race) { p.childRacePtr = f; Log("resolve: [%s] child race %08X", p.section, p.childRace.fid); }
			else Log("resolve: [%s] child race %s|%06X is not a loaded RACE", p.section, p.childRace.plugin, p.childRace.localID);
		}
		for (int gi = 0; gi < p.numGive; gi++) {
			FormRef& g = p.give[gi];
			g.fid = ResolveFID(g.plugin, g.localID);
			if (!g.fid || !LookupForm(g.fid)) { Log("resolve: [%s] give item %s|%06X not loaded - skipped", p.section, g.plugin, g.localID); g.fid = 0; }
			else Log("resolve: [%s] give item %08X", p.section, g.fid);
		}
		for (int k = 0; k < p.numPerks; k++) {
			FormRef& g = p.perks[k]; g.fid = ResolveFID(g.plugin, g.localID); void* f = g.fid ? LookupForm(g.fid) : nullptr;
			if (!f || *((UInt8*)f + 4) != kFormType_Perk) { Log("resolve: [%s] perk %s|%06X not a loaded PERK - skipped", p.section, g.plugin, g.localID); g.fid = 0; }
			else Log("resolve: [%s] give perk %08X", p.section, g.fid);
		}
		for (int k = 0; k < p.numTaunts; k++) {
			FormRef& g = p.taunts[k]; g.fid = ResolveFID(g.plugin, g.localID);
			if (!g.fid || !LookupForm(g.fid)) { Log("resolve: [%s] taunt idle %s|%06X not loaded - skipped", p.section, g.plugin, g.localID); g.fid = 0; }
			else Log("resolve: [%s] taunt idle %08X", p.section, g.fid);
		}
		for (int fi = 0; fi < p.numFactions; fi++) {
			FormRef& fr = p.factions[fi];
			fr.fid = GetModIndex(fr.plugin) == 0xFF ? 0 : ResolveFID(fr.plugin, fr.localID);
			void* f = fr.fid ? LookupForm(fr.fid) : nullptr;
			if (!f || *((UInt8*)f + 4) != 0x08) { Log("resolve: [%s] faction %s|%06X not loaded - skipped", p.section, fr.plugin, fr.localID); fr.fid = 0; }
			else Log("resolve: [%s] faction %08X%s", p.section, fr.fid, p.joinFaction ? " (joined while in the race)" : " (JoinFaction=0: not joined)");
		}
		for (FormRef& r : p.ghostForms) r.fid = r.localID ? ResolveFID(r.plugin, r.localID) : 0;
		for (int k = 0; k < p.numLocked; k++) p.locked[k].fid = ResolveFID(p.locked[k].plugin, p.locked[k].localID);
		p.unlockGlobal.fid = p.unlockGlobal.localID ? ResolveFID(p.unlockGlobal.plugin, p.unlockGlobal.localID) : 0;
		for (int k = 0; k < p.numFaces; k++) p.faceEyes[k].fid = ResolveFID(p.faceEyes[k].plugin, p.faceEyes[k].localID);
		p.unarmedEffect.fid = p.unarmedEffect.localID ? ResolveFID(p.unarmedEffect.plugin, p.unarmedEffect.localID) : 0;
		if (p.ghostMoves) Log("resolve: [%s] ghost moves: spells %08X %08X, idles %08X %08X %08X %08X, dodge spell %08X", p.section, p.ghostForms[0].fid,
			p.ghostForms[1].fid, p.ghostForms[2].fid, p.ghostForms[3].fid, p.ghostForms[4].fid, p.ghostForms[5].fid, p.ghostForms[6].fid);
		if (p.numLocked) Log("resolve: [%s] %d locked item(s) until global %08X", p.section, p.numLocked, p.unlockGlobal.fid);
		if (p.numFaces) Log("resolve: [%s] %d faces chosen by eyes", p.section, p.numFaces);
		if (p.unarmedEffect.fid) Log("resolve: [%s] unarmed effect %08X on anim %02X (weapons %d, reach x%.2f, cone %.0f)", p.section,
			p.unarmedEffect.fid, p.unarmedAnim, p.unarmedWeapons, p.unarmedReachMult, p.unarmedCone);
		if (p.bodyParts.localID) {                                     // must be a BPTD (same form type as DefaultBodyPartData)
			FormRef& b = p.bodyParts;
			b.fid = GetModIndex(b.plugin) == 0xFF ? 0 : ResolveFID(b.plugin, b.localID);
			void* f = b.fid ? LookupForm(b.fid) : nullptr;
			void* def = *(void**)kPtr_DefaultBodyPartData;
			if (!f || !def || *((UInt8*)f + 4) != *((UInt8*)def + 4)) { Log("resolve: [%s] body part data %s|%06X is not a loaded BPTD - disabled", p.section, b.plugin, b.localID); b.fid = 0; }
			else Log("resolve: [%s] body part data %08X", p.section, b.fid);
		}
		if (FormRef* r = &p.loopSnd; r->localID) {
			r->fid = ResolveFID(r->plugin, r->localID);
			void* f = LookupForm(r->fid);
			if (!f || *((UInt8*)f + 4) != kFormType_SOUN) { Log("resolve: [%s] loop sound %s|%06X is not a loaded SOUN - disabled", p.section, r->plugin, r->localID); r->fid = 0; }
		}
	}
	g_jip = GetModuleHandleA("jip_nvse.dll") != nullptr;
	UInt32 qp = *(UInt32*)kSlot_QueuedPlayerRun;
	Log("deps: JIP LN NVSE %s; QueuedPlayer::Run slot=%08X (%s)", g_jip ? "loaded" : "NOT loaded",
		qp, qp == kAddr_VanillaQueuedPlayerRun ? "vanilla - live rebuild unavailable" : "patched - live rebuild available");
}
static Profile* ProfileForRace(void* race) {
	if (!race) return nullptr;
	for (int i = 0; i < g_numProf; i++) if (g_prof[i].race == race || g_prof[i].childRacePtr == race) return &g_prof[i];   // child race = same profile
	return nullptr;
}
static inline void* NPCRace(void* npc) { return *(void**)((UInt8*)npc + 0x110); }
static inline void* Player() { return *(void**)kPtr_Player; }
static inline void* PlayerNPC() { void* p = Player(); return p ? *(void**)((UInt8*)p + 0x20) : nullptr; }
static Profile* PlayerProfile() { void* n = PlayerNPC(); return n ? ProfileForRace(NPCRace(n)) : nullptr; }

// ---------------- hook 1: skeleton path ----------------
typedef const char* (__fastcall* GetModelPath_t)(void* model, void* edx);
static const char* __fastcall Hook_NPCGetModelPath(void* model, void* edx) {
	if (Profile* p = ProfileForRace(NPCRace((UInt8*)model - 0xDC))) return p->skeleton;
	return ((GetModelPath_t)kAddr_TESNPC_GetModelPath)(model, edx);
}

// ---------------- locked items ----------------
static bool InList(const FormRef* l, int n, UInt32 fid) { for (int i = 0; i < n; i++) if (l[i].fid && l[i].fid == fid) return true; return false; }
enum Verdict { kAllow = 0, kBlockLocked };
// LockedItems= stay refused until the UnlockGlobal= GLOB reaches 1 (TESGlobal value +0x24, see its save code 0x5A6488);
// the load-time equipment check unequips them too. (Securitrons: the Mk II weapons until the Securitron upgrade.)
static bool ItemLocked(Profile* p, UInt32 fid) {
	if (!p->numLocked || !InList(p->locked, p->numLocked, fid)) return false;
	void* g = p->unlockGlobal.fid ? LookupForm(p->unlockGlobal.fid) : nullptr;
	return !(g && *((UInt8*)g + 4) == kFormType_GLOB && *(float*)((UInt8*)g + 0x24) >= 1.0f);
}
static Verdict Judge(Profile* p, void* form) {
	if (!p || !form || !p->numLocked) return kAllow;
	return ItemLocked(p, *(UInt32*)((UInt8*)form + 0x0C)) ? kBlockLocked : kAllow;
}
typedef bool (__cdecl* QueueUIMessage_t)(const char*, UInt32, const char*, const char*, float, UInt8);

// Actor::EquipItem detour
typedef void (__fastcall* EquipItem_t)(void* actor, void* edx, void* form, UInt32 count, void* xl, UInt32 ench, UInt32 lock, UInt32 noMsg);
static EquipItem_t g_equipTramp = nullptr;
static void __fastcall Hook_EquipItem(void* actor, void* edx, void* form, UInt32 count, void* xl, UInt32 ench, UInt32 lock, UInt32 noMsg) {
	if (actor && actor == Player()) {
		Profile* p = PlayerProfile();
		if (Judge(p, form) == kBlockLocked) {
			bool shown = ((QueueUIMessage_t)kAddr_QueueUIMessage)(p->lockedMsg, 0, nullptr, nullptr, 3.0f, 0);
			Log("equip: locked %08X for [%s], message %s", *(UInt32*)((UInt8*)form + 0x0C), p->section, shown ? "queued" : "NOT queued");
			return;
		}
	}
	g_equipTramp(actor, edx, form, count, xl, ench, lock, noMsg);
}
typedef void (__fastcall* UnequipItem_t)(void* actor, void* edx, void* form, UInt32 count, void* xl, UInt32 ench, UInt32 lock, UInt32 noMsg);

// Walk the player's inventory changes and unequip the race's locked items.
static void EnforceEquipment(const char* why) {
	void* player = Player();
	Profile* p = PlayerProfile();
	if (!player || !p || !p->numLocked) return;
	UInt8* x = *(UInt8**)((UInt8*)player + 0x44 + 4);        // ExtraDataList::m_data
	while (x && *(x + 4) != 0x15) x = *(UInt8**)(x + 8);      // ExtraContainerChanges
	if (!x) return;
	UInt8* data = *(UInt8**)(x + 0xC);
	if (!data) return;
	struct Pending { void* form; void* xl; } todo[64]; int n = 0;
	for (UInt8** node = *(UInt8***)data; node && n < 64; node = (UInt8**)node[1]) {
		UInt8* entry = node[0];
		if (!entry) continue;
		void* form = *(void**)(entry + 8);
		if (!form || Judge(p, form) == kAllow) continue;
		for (UInt8** xn = *(UInt8***)entry; xn && n < 64; xn = (UInt8**)xn[1]) {
			UInt8* xl = xn[0];
			if (!xl) continue;
			UInt8 bits = *(xl + 8 + 2);                         // presence bits for types 0x10..0x17
			if (bits & 0xC0) todo[n++] = {form, xl};             // ExtraWorn (0x16) / ExtraWornLeft (0x17)
		}
	}
	for (int i = 0; i < n; i++) {
		Log("enforce(%s): unequip %08X (type %02X)", why, *(UInt32*)((UInt8*)todo[i].form + 0x0C), *((UInt8*)todo[i].form + 4));
		((UnequipItem_t)kAddr_UnequipItem)(player, nullptr, todo[i].form, 1, todo[i].xl, 1, 0, 1);
	}
}

// ---------------- live switch ----------------
static const char* RootMarker(void* root) {
	if (!root) return nullptr;
	UInt8* n = (UInt8*)root;
	void** data = *(void***)(n + 0xA0);
	UInt16 cnt = *(UInt16*)(n + 0xA6);
	for (UInt16 i = 0; data && i < cnt; i++) {
		UInt8* c = (UInt8*)data[i];
		if (!c) continue;
		const char* nm = *(const char**)(c + 0x08);
		if (nm && !strncmp(nm, "PCSkeleton:", 11)) return nm;
	}
	return "";
}
static void* PlayerRoot(void* player) {
	void* rs = *(void**)((UInt8*)player + 0x64);
	return rs ? *(void**)((UInt8*)rs + 0x14) : nullptr;
}
typedef void (__fastcall* QueueRef_t)(void* loader, void* edx, void* ref, UInt32 a, UInt32 b);
//
// Loading a save made in the same creature race keeps the player's existing 3D (no OnRefSet3D, same root), so after a
// death the skeleton the death ragdoll took over is reused, with the movement sequences that were playing at the death
// left in a broken state (forward roll: arms at the bind pose; sneak, not played at the death, fine). After the player
// died, the next game load rebuilds the player 3D (the same queued rebuild as a race switch) even when the skeleton
// already matches - a fresh skeleton, animation data and ragdoll, as a load of a different race gets.
static bool g_playerDied = false;
// The engine caches an actor's height on its process (+0x42C, getter 0x8853A0: bound box height x scale, kept once
// computed) and IsChild (vtbl 0x1A0, 0x8D40E0) calls anything under 110 a child (no furniture). Only a race / sex
// change through AgeRace / MatchRace / SexChange clears it (0x8D3FA0 -> 0x8854B0(0)); a race switched in the race menu,
// a live skeleton rebuild or a save of another race loaded into the same session kept the old height (a Deathclaw,
// 152 tall, refused chairs as a child after the player had been a Tunneler, 56). Cleared here the same way.
typedef int (__fastcall* ProcFn_t)(void* proc, void* edx);
typedef void (__fastcall* ProcSetF_t)(void* proc, void* edx, float v);
static void ResetPlayerHeight(const char* why) {
	void* player = Player(); if (!player) return;
	void* proc = *(void**)((UInt8*)player + 0x68); if (!proc) return;
	if (((ProcFn_t)0x0045CD60)(proc, nullptr)) return;               // as 0x8D3FA0: not for that process kind
	float old = *(float*)((UInt8*)proc + 0x42C);
	((ProcSetF_t)0x008854B0)(proc, nullptr, 0.0f);
	if (old != 0.0f) Log("height: cached player height %.1f cleared (%s)", old, why);
}
static void SyncPlayerSkeleton(const char* why) {
	void* player = Player();
	if (!player || !PlayerNPC()) return;
	Profile* want = PlayerProfile();
	const char* have = RootMarker(PlayerRoot(player));
	const char* wantMarker = want ? want->marker : "";
	Log("sync(%s): race=%p have='%s' want='%s'", why, NPCRace(PlayerNPC()), have ? have : "(no 3D)", wantMarker);
	ResetPlayerHeight(why);
	bool afterDeath = g_playerDied && !strcmp(why, "game loaded") && have && *wantMarker && !strcmp(have, wantMarker);
	if (!strcmp(why, "game loaded")) g_playerDied = false;
	if (afterDeath) Log("sync: the player died before this load - rebuilding the same skeleton");
	if (!have || (!afterDeath && !strcmp(have, wantMarker))) return;
	if (*(UInt32*)kSlot_QueuedPlayerRun == kAddr_VanillaQueuedPlayerRun) {
		Log("sync: live rebuild unavailable (JIP LN NVSE not installed) - new skeleton applies after save+load");
		((QueueUIMessage_t)kAddr_QueueUIMessage)("Playable Creatures: install JIP LN NVSE for the live race switch. Save and reload to apply.", 0, nullptr, nullptr, 6.0f, 0);
		return;
	}
	UInt8* flags5F = (UInt8*)player + 0x5F;
	if (*flags5F & 1) { Log("sync: rebuild already pending"); return; }
	*flags5F |= 1;
	((QueueRef_t)kAddr_QueueReference)(*(void**)kPtr_ModelLoader, nullptr, player, 1, 0);
	Log("sync: player 3D rebuild queued");
}
static void UpdateLoop(const char* why, void* newRoot = nullptr);
static void ApplyVoice(const char* why);
static void GiveRaceAbilities(const char* why);
static void GiveRaceItems(const char* why);
static void GiveRacePerks(const char* why);
static void CleanupFactions(const char* why);
typedef void* (__fastcall* MenuDtor_t)(void* menu, void* edx, UInt32 flags);
static MenuDtor_t g_prevMenuDtor = (MenuDtor_t)kAddr_RaceSexMenu_Dtor;
static void* __fastcall Hook_RaceSexMenuDtor(void* menu, void* edx, UInt32 flags) {
	void* r = g_prevMenuDtor(menu, edx, flags);                      // vanilla or another plugin's hook
	EnforceEquipment("race menu closed");
	SyncPlayerSkeleton("race menu closed");
	void* pl = Player();
	if (pl && (*((UInt8*)pl + 0x5F) & 1)) Log("voice: loop waits for the rebuilt 3D");   // OnRefSet3D will start it
	else UpdateLoop("race menu closed");
	CleanupFactions("race menu closed");
	GiveRaceAbilities("race menu closed");
	GiveRaceItems("race menu closed");
	GiveRacePerks("race menu closed");
	ApplyVoice("race menu closed");
	return r;
}

// ---------------- patching ----------------
static bool PatchPtr(UInt32 addr, UInt32 value, UInt32 expected, const char* what) {
	UInt32* p = (UInt32*)addr;
	if (*p != expected) { Log("patch: %s @%08X = %08X, expected %08X -> NOT patched", what, addr, *p, expected); return false; }
	DWORD old; VirtualProtect(p, 4, PAGE_EXECUTE_READWRITE, &old); *p = value; VirtualProtect(p, 4, old, &old);
	Log("patch: %s @%08X %08X -> %08X", what, addr, expected, value);
	return true;
}
// 6-byte prologue detour ("55 8B EC 83 EC xx"); chains to an existing entry jmp from another plugin.
static void* Detour(UInt32 addr, UInt8 frameSize, void* hook, const char* what) {
	UInt8* fn = (UInt8*)addr;
	const UInt8 vanilla[6] = {0x55, 0x8B, 0xEC, 0x83, 0xEC, frameSize};
	UInt8* tramp = (UInt8*)VirtualAlloc(nullptr, 32, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE);
	if (!tramp) return nullptr;
	bool isVanilla = !memcmp(fn, vanilla, 6);
	if (isVanilla) {
		memcpy(tramp, vanilla, 6);
		tramp[6] = 0xE9; *(SInt32*)(tramp + 7) = (SInt32)((UInt32)fn + 6 - ((UInt32)tramp + 11));
	} else if (fn[0] == 0xE9) {
		UInt32 target = (UInt32)fn + 5 + *(SInt32*)(fn + 1);
		tramp[0] = 0xE9; *(SInt32*)(tramp + 1) = (SInt32)(target - ((UInt32)tramp + 5));
		Log("patch: %s entry already detoured by another plugin -> chaining to %08X", what, target);
	} else {
		Log("patch: %s entry bytes unexpected (%02X %02X %02X %02X) -> NOT hooked", what, fn[0], fn[1], fn[2], fn[3]);
		VirtualFree(tramp, 0, MEM_RELEASE);
		return nullptr;
	}
	DWORD old; VirtualProtect(fn, 6, PAGE_EXECUTE_READWRITE, &old);
	fn[0] = 0xE9; *(SInt32*)(fn + 1) = (SInt32)((UInt32)hook - ((UInt32)fn + 5));
	if (isVanilla) fn[5] = 0x90;
	VirtualProtect(fn, 6, old, &old);
	FlushInstructionCache(GetCurrentProcess(), fn, 6);
	Log("patch: %s detour installed (trampoline %p)", what, tramp);
	return tramp;
}
// Entry hook that leaves the function's bytes after "push ebp; mov ebp, esp" untouched: a 2-byte short jump at the entry
// into the 5 int3 padding bytes before the function, which hold the jump to the hook; the trampoline re-runs the
// two instructions and continues at entry + 3. Other plugins hook Actor::EquipItem right after the frame setup
// (ShowOff NVSE at 0x88C653, checking those bytes are vanilla; Stewie's Tweaks at 0x88C659): a full 5-byte entry jump
// overwrote ShowOff's site, so it refused its hook. With this one both chain behind ours in any load order.
static void* DetourPadded(UInt32 addr, UInt8 frameSize, void* hook, const char* what) {
	UInt8* fn = (UInt8*)addr; UInt8* pad = fn - 5;
	const UInt8 frame[3] = {0x55, 0x8B, 0xEC};
	bool padFree = pad[0] == 0xCC && pad[1] == 0xCC && pad[2] == 0xCC && pad[3] == 0xCC && pad[4] == 0xCC;
	bool shortHooked = fn[0] == 0xEB && fn[1] == 0xF9 && pad[0] == 0xE9;        // another plugin used this same scheme
	if (!(padFree && !memcmp(fn, frame, 3)) && !shortHooked) return Detour(addr, frameSize, hook, what);
	UInt8* tramp = (UInt8*)VirtualAlloc(nullptr, 32, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE);
	if (!tramp) return nullptr;
	if (shortHooked) {
		UInt32 prev = (UInt32)pad + 5 + *(SInt32*)(pad + 1);
		tramp[0] = 0xE9; *(SInt32*)(tramp + 1) = (SInt32)(prev - ((UInt32)tramp + 5));
		Log("patch: %s entry already short-jumped by another plugin -> chaining to %08X", what, prev);
	} else {
		memcpy(tramp, frame, 3);
		tramp[3] = 0xE9; *(SInt32*)(tramp + 4) = (SInt32)((UInt32)fn + 3 - ((UInt32)tramp + 8));
	}
	DWORD old; VirtualProtect(pad, 7, PAGE_EXECUTE_READWRITE, &old);
	pad[0] = 0xE9; *(SInt32*)(pad + 1) = (SInt32)((UInt32)hook - ((UInt32)pad + 5));
	fn[0] = 0xEB; fn[1] = 0xF9;                                                  // jmp short entry - 5
	VirtualProtect(pad, 7, old, &old);
	FlushInstructionCache(GetCurrentProcess(), pad, 7);
	Log("patch: %s detour installed through its padding (entry + 3 left vanilla; trampoline %p)", what, tramp);
	return tramp;
}

// TESNPC::AddItemToBiped (0x6061B0, thiscall(npc, Character*, BipedAnim*, TESForm*) -> bool, ret 0xC).
// Single entry point for putting a worn item's model into a biped (full repopulate, equip refresh, 1st person).
// For creature races with ArmorVisuals=0 armor is reported as "added" but never placed, so the race's own
// body parts stay in those slots. Slot masks are untouched, so equip conflicts and stats behave normally.
typedef bool (__fastcall* AddItemToBiped_t)(void* npc, void* edx, void* character, void* biped, void* form);
static AddItemToBiped_t g_addBipedTramp = nullptr;
static bool __fastcall Hook_AddItemToBiped(void* npc, void* edx, void* character, void* biped, void* form) {
	if (npc && form && *((UInt8*)form + 4) == kFormType_ARMO) {
		Profile* p = ProfileForRace(NPCRace(npc));
		if (p && !p->armorVisuals) {
			UInt32 fid = *(UInt32*)((UInt8*)form + 0x0C);
			void* player = Player();
			bool firstPersonBiped = player && biped == *(void**)((UInt8*)player + 0x68C);
			bool visible = InList(p->show, p->numShow, fid) || (firstPersonBiped && InList(p->show1st, p->numShow1st, fid));
			if (!visible) return true;
		}
	}
	return g_addBipedTramp(npc, edx, character, biped, form);
}


// ---------------- creature players keep their own animation set ----------------
// Every anim-group lookup goes through NiTPointerMap<UInt16,AnimSequenceBase*>::GetAt (0x49C390) at the call sites
// below; kNVSE redirects these sites to add AnimGroupOverride anims (human "_male" overrides such as player ADS or
// locomotion packs). For any Character in a creature race (player 1st-person arms excepted) we answer from the creature's own
// map only, and chain to whatever was installed (kNVSE or vanilla) for everyone/everything else.
static const UInt32 kAddr_AnimMapGetAt = 0x0049C390;
struct LookupSite { UInt32 addr; int ebpOff; };
static const LookupSite kLookupSites[] = {
	{0x49575B, -0x10}, {0x495965, -0x10}, {0x4959B9, -0x10}, {0x495A03, -0x10}, {0x4948E6, -0x14}, {0x495DC6, -0x10},
	{0x4956CE, -0x14}, {0x49431B, -0x0C}, {0x493115, -0x18C}, {0x49472B, -0x08}, {0x49651B, -0x08}};
static const int kNumLookupSites = sizeof(kLookupSites) / sizeof(kLookupSites[0]);
static inline bool IsCreatureRaceAnim(void* animData) {
	// any Character whose race is a registered creature race (player 1st-person arms excluded)
	if (!animData) return false;
	UInt8* actor = *(UInt8**)((UInt8*)animData + 4);
	if (!actor) return false;
	void* player = Player();
	if (actor == player && animData == *(void**)((UInt8*)player + 0x690)) return false;
	UInt8* base = *(UInt8**)(actor + 0x20);
	if (!base || base[4] != 0x2A) return false;                           // TESNPC only
	return ProfileForRace(NPCRace(base)) != nullptr;
}
// The guard must NOT add a stack frame: kNVSE's hooks read the engine function's locals through the caller's ebp,
// so a C++ wrapper that calls them would hand them our frame (crashes). Each site therefore
// gets a tiny generated thunk that keeps ebp/return address intact and *jumps* to either vanilla GetAt or the
// previously installed hook.
static bool __cdecl IsCreatureRaceAnimC(void* animData) { return IsCreatureRaceAnim(animData); }

// Creature lookup: the creature's own map first. If a weapon asks for an attack group the creature has no
// animation for (e.g. a rifle set to Attack8 while the alien only has Attack4), answer with the creature's own
// attack of the same aim variant, so the weapon still fires with a creature animation. Every group the creature is
// asked for but doesn't have is logged once (tells us what else is missing, e.g. reloads).
typedef bool (__fastcall* MapGetAt_t)(void* map, void* edx, UInt32 key, void** out);
static UInt8 g_missLogged[0x10000 / 8];
static bool TryKey(void* map, UInt32 key, void** out) { return ((MapGetAt_t)kAddr_AnimMapGetAt)(map, nullptr, key & 0xFFFF, out) && *out; }
static bool __fastcall CreatureGetAt(void* map, void* edx, UInt32 key, void** out) {
	if (TryKey(map, key, out)) return true;
	UInt32 hi = key & 0xFF00, g = key & 0xFF;
	int base = -1, variant = 0;                                  // variant: 0 plain,1 Up,2 Down,3 IS,4 ISUp,5 ISDown
	if (g >= 0x1A && g <= 0x49) { base = 0x1A + ((g - 0x1A) / 6) * 6; variant = (g - 0x1A) % 6; }
	else if (g >= 0x90 && g <= 0x95) { base = 0x90; variant = g - 0x90; }
	if (base >= 0) {
		static const UInt8 order[] = {0x26, 0x2C, 0x20, 0x1A, 0x32, 0x38, 0x3E, 0x44, 0x90};   // Attack3, Attack4, Right, Left, 5..9
		const int tries[3] = {variant, variant >= 3 ? variant - 3 : -1, 0};                    // same variant, non-IS, plain
		for (int t = 0; t < 3; t++) {
			if (tries[t] < 0) continue;
			for (UInt8 b : order)
				// the same attack in another aim variant (e.g. Attack3IS -> Attack3) is the best substitute
				if ((b != base || tries[t] != variant) && TryKey(map, hi | (b + tries[t]), out)) {
					if (!(g_missLogged[key >> 3 & 0x1FFF] & (1 << (key & 7)))) {
						g_missLogged[key >> 3 & 0x1FFF] |= 1 << (key & 7);
						Log("anim: creature has no group %04X - using its %04X instead", key & 0xFFFF, hi | (b + tries[t]));
					}
					return true;
				}
		}
	}
	// reloads / jams: no runtime substitution — the creature folder carries its own files for every reload and jam
	// group (build_reload.py), because the engine completes a reload only on the exact group it requested.
	UInt32 k = key & 0xFFFF;
	if (!(g_missLogged[k >> 3] & (1 << (k & 7)))) { g_missLogged[k >> 3] |= 1 << (k & 7); Log("anim: creature has no group %04X (no substitute)", k); }
	*out = nullptr;
	return false;
}
static UInt8* BuildLookupThunk(UInt8* p, int ebpOff, UInt32 prev) {
	UInt8* start = p;
	*p++ = 0x51;                                              // push ecx
	*p++ = 0x52;                                              // push edx
	*p++ = 0xFF; *p++ = 0xB5; *(SInt32*)p = ebpOff; p += 4;   // push dword ptr [ebp+off]  (AnimData*)
	*p++ = 0xE8; *(SInt32*)p = (SInt32)((UInt32)IsCreatureRaceAnimC - ((UInt32)p + 4)); p += 4;
	*p++ = 0x83; *p++ = 0xC4; *p++ = 0x04;                    // add esp, 4
	*p++ = 0x5A;                                              // pop edx
	*p++ = 0x59;                                              // pop ecx
	*p++ = 0x84; *p++ = 0xC0;                                 // test al, al
	*p++ = 0x75; *p++ = 0x05;                                 // jnz +5 -> vanilla
	*p++ = 0xE9; *(SInt32*)p = (SInt32)(prev - ((UInt32)p + 4)); p += 4;               // jmp previous hook / vanilla
	*p++ = 0xE9; *(SInt32*)p = (SInt32)((UInt32)CreatureGetAt - ((UInt32)p + 4)); p += 4; // jmp creature lookup
	return start;
}
// (Mister Handy / Gutsy turned over while firing - the anim debug showed
// AnimGroupOverride\TNW_MinigunFire_TTW\_male\2hhattackspin.kf playing on the robot despite the 11 lookup guards)
// kNVSE has a second override point: it also redirects the 4 calls of AnimData::MorphOrBlendToSequence (0x4949A0 -
// play this sequence for this group; thiscall, ecx = AnimData) and there swaps the sequence for its AnimGroupOverride /
// SetActorAnimationPath / InterceptPlayAnimGroup result (kNVSE.dll 2024-11-12: hook at 0x1003C7xx, original called at
// 0x1003C983 / C9DC / C9FC). JSON overrides with no form and a condition such as "GetIsCreature == 0" (Titans of the
// New West) or "GetCreatureType == -1" (Enhanced Animations) match the player in any race. For an actor in a creature
// race with BlockAnimOverrides=1 these 4 calls go straight to the engine's function with the creature's own sequence
// (the one the guarded lookups returned); everyone else still goes through kNVSE (or whatever was installed).
static const UInt32 kAddr_MorphOrBlend = 0x004949A0;
static const UInt32 kPlaySites[] = {0x494989, 0x4956FF, 0x495E2A, 0x4973B4};
static const int kNumPlaySites = sizeof(kPlaySites) / sizeof(kPlaySites[0]);
// a temporary speed probe lived here (player movement groups timed between play calls); it measured the
// Robobrain at ref scale^2 (Forward 32 units/s), fixed natively by its race ability's SpeedMult ; removed.
static bool g_fpActive = false;                      // 1st person with the creature body shown (see "first person")
static bool __cdecl BlockOverridesC(void* animData, void* seq) {
	if (!IsCreatureRaceAnim(animData)) return false;
	UInt8* actor = *(UInt8**)((UInt8*)animData + 4);
	Profile* p = ProfileForRace(NPCRace(*(UInt8**)(actor + 0x20)));
	return p && p->blockAnimOverrides;
}
static UInt8* BuildPlayThunk(UInt8* p, UInt32 prev) {
	UInt8* start = p;
	*p++ = 0x51;                                              // push ecx
	*p++ = 0x52;                                              // push edx
	*p++ = 0xFF; *p++ = 0x74; *p++ = 0x24; *p++ = 0x0C;      // push [esp+0Ch] (the sequence: caller's arg 1)
	*p++ = 0x51;                                              // push ecx  (AnimData* this)
	*p++ = 0xE8; *(SInt32*)p = (SInt32)((UInt32)BlockOverridesC - ((UInt32)p + 4)); p += 4;
	*p++ = 0x83; *p++ = 0xC4; *p++ = 0x08;                    // add esp, 8
	*p++ = 0x5A;                                              // pop edx
	*p++ = 0x59;                                              // pop ecx
	*p++ = 0x84; *p++ = 0xC0;                                 // test al, al
	*p++ = 0x75; *p++ = 0x05;                                 // jnz +5 -> engine
	*p++ = 0xE9; *(SInt32*)p = (SInt32)(prev - ((UInt32)p + 4)); p += 4;                     // jmp previous hook / engine
	*p++ = 0xE9; *(SInt32*)p = (SInt32)(kAddr_MorphOrBlend - ((UInt32)p + 4)); p += 4;       // jmp engine MorphOrBlendToSequence
	return start;
}
static void InstallAnimPlayGuards() {
	UInt8* mem = (UInt8*)VirtualAlloc(nullptr, 64 * kNumPlaySites, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE);
	if (!mem) { Log("playguard: VirtualAlloc failed"); return; }
	int n = 0;
	for (int i = 0; i < kNumPlaySites; i++) {
		UInt8* site = (UInt8*)kPlaySites[i];
		if (site[0] != 0xE8) { Log("playguard: site %08X is not a call (%02X) - skipped", kPlaySites[i], site[0]); continue; }
		UInt32 prev = (UInt32)site + 5 + *(SInt32*)(site + 1);
		UInt8* thunk = BuildPlayThunk(mem + 64 * i, prev);
		DWORD old; VirtualProtect(site, 5, PAGE_EXECUTE_READWRITE, &old);
		*(SInt32*)(site + 1) = (SInt32)((UInt32)thunk - ((UInt32)site + 5));
		VirtualProtect(site, 5, old, &old);
		Log("playguard: site %08X previously -> %08X%s", kPlaySites[i], prev, prev == kAddr_MorphOrBlend ? " (vanilla)" : " (another plugin, chained)");
		n++;
	}
	FlushInstructionCache(GetCurrentProcess(), nullptr, 0);
	Log("playguard: %d/%d sequence-play sites guarded (kNVSE overrides off for creature races with BlockAnimOverrides=1)", n, kNumPlaySites);
}
static void InstallAnimLookupGuards() {
	UInt8* mem = (UInt8*)VirtualAlloc(nullptr, 64 * kNumLookupSites, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE);
	if (!mem) { Log("animguard: VirtualAlloc failed"); return; }
	int n = 0;
	for (int i = 0; i < kNumLookupSites; i++) {
		UInt8* site = (UInt8*)kLookupSites[i].addr;
		if (site[0] != 0xE8) { Log("animguard: site %08X is not a call (%02X) - skipped", kLookupSites[i].addr, site[0]); continue; }
		UInt32 prev = (UInt32)site + 5 + *(SInt32*)(site + 1);
		UInt8* thunk = BuildLookupThunk(mem + 64 * i, kLookupSites[i].ebpOff, prev);
		DWORD old; VirtualProtect(site, 5, PAGE_EXECUTE_READWRITE, &old);
		*(SInt32*)(site + 1) = (SInt32)((UInt32)thunk - ((UInt32)site + 5));
		VirtualProtect(site, 5, old, &old);
		Log("animguard: site %08X previously -> %08X%s", kLookupSites[i].addr, prev, prev == kAddr_AnimMapGetAt ? " (vanilla)" : " (another plugin, chained)");
		n++;
	}
	FlushInstructionCache(GetCurrentProcess(), nullptr, 0);
	Log("animguard: %d/%d lookup sites guarded (frame-transparent thunks)", n, kNumLookupSites);
}


// ---------------- 3rd-person camera height ----------------
// The engine's 3rd-person camera pivot (PlayerCharacter camera update, non-vanity path) is
//   pivot.z = root.z + scale * e0 + (Camera1st.world.z - Camera3rd.world.z)            (0x94B526..0x94B58B)
// e0 = [player+0x698], the human 1st-person skeleton's Camera1st height at bind (set at 0x94E60A); Camera1st
// (0x11E07D0) is in that 1st-person skeleton, Camera3rd (0x11E07D4) in the 3rd-person one. For a human,
// Camera3rd (118.4) ~ e0, so the term only carries the 1st-person crouch; the view sits at ~e0 above the feet whatever
// the skeleton, and a LOWER Camera3rd RAISES it (Tunneler: Camera3rd 49.7 -> 32 moved the view up).
// For our skeletons (PCSkeleton marker) the pivot is put at Camera3rd itself, plus the 1st-person crouch scaled by
// Camera3rd height / e0. Everything else (humans, vanity camera) runs the vanilla term.
static const UInt32 kSite_CamPivotTerm = 0x0094B55B, kAddr_CamPivotTermEnd = 0x0094B591;
static const UInt32 kPtr_Camera1stNode = 0x011E07D0, kPtr_Camera3rdNode = 0x011E07D4;
static inline float NodeWorldZ(void* node) { return *(float*)((UInt8*)node + 0x94); }   // NiAVObject world translate +0x8C
static UInt8* AllocExec(UInt32 n);
static void* g_camRoot = nullptr; static bool g_camOurs = false, g_camLogged = false; static float g_camSneak = 1.0f;
static void __cdecl CamPivotTerm(float* pz, void* player) {
	void* c1 = *(void**)kPtr_Camera1stNode; void* c3 = *(void**)kPtr_Camera3rdNode;
	if (!c1 || !c3) return;
	float vanillaTerm = NodeWorldZ(c1) - NodeWorldZ(c3);
	void* root = player ? PlayerRoot(player) : nullptr;
	if (root != g_camRoot) {                                     // new 3rd-person skeleton (load, race switch)
		g_camRoot = root; const char* m = RootMarker(root); g_camOurs = m && *m; g_camLogged = false;
		Profile* prof = PlayerProfile(); g_camSneak = prof ? prof->sneakCamera : 1.0f;   // per skeleton, not per frame
	}
	if (!g_camOurs) { *pz += vanillaTerm; return; }
	void* fp = *(void**)((UInt8*)player + 0x694);
	float e0 = *(float*)((UInt8*)player + 0x698);
	// e0 is the unscaled bind height; the 1st-person skeleton carries the player's scale (race height: the Mirelurk
	// 0.75, the Robobrain 0.33), so its standing eye is e0 x that scale (its root's world scale) - compared against the
	// unscaled e0, a small race read as crouched all the time
	float s = fp ? *(float*)((UInt8*)fp + 0x98) : 1.0f;              // NiAVObject world scale
	if (!(s > 0.01f && s < 100.0f)) s = 1.0f;
	float e0s = e0 * s;
	float rootZ = NodeWorldZ(root), h3 = NodeWorldZ(c3) - rootZ;
	float k = e0s > 1.0f ? h3 / e0s : 1.0f;
	if (k < 0.1f) k = 0.1f; else if (k > 3.0f) k = 3.0f;
	float eye = fp ? NodeWorldZ(c1) - NodeWorldZ(fp) : e0s;          // 1st-person eye height now (crouch lowers it)
	// the crouch drop is the 1st-person (human) skeleton's; SneakCamera= scales it per race (0 = none)
	float sc = g_camSneak;
	float vanilla = *pz + vanillaTerm;
	*pz = NodeWorldZ(c3) + (eye - e0s) * k * sc;
	if (!g_camLogged) {
		g_camLogged = true;
		Log("camera: '%s' feet %.1f, Camera3rd +%.1f, 1st-person eye %.1f (bind %.1f x scale %.2f) -> pivot +%.1f (vanilla would be +%.1f), sneak drop x%.2f",
			RootMarker(root), rootZ, h3, eye, e0, s, *pz - rootZ, vanilla - rootZ, sc);
	}
}
// ---------------- fall damage ----------------
// Actor fall damage (Actor vtbl 0x250 = 0x8A62B0, shared by Actor / Creature / Character / PlayerCharacter): after the
// damage is computed from fJumpFallHeightMin / Exponent / Mult it calls 0x5F0C40(baseForm) at 0x8A63DB - true for a CREA
// base with the ACBS "Flies" flag (0x20; every vanilla eyebot, cazador, bloatfly, Mister Gutsy) - and sets the damage
// to 0. A player base is a TESNPC, never a CREA, so it never qualifies. The call is redirected: same answer for every
// actor, plus true for the player's base while the race profile has NoFallDamage=1 (no health / limb damage, no
// landing-hurt sound - the engine's own exemption path).
static const UInt32 kSite_FallFlies = 0x008A63DB, kAddr_BaseFlies = 0x005F0C40;
typedef bool (__fastcall* FormBool_t)(void* form, void* edx);
static FormBool_t g_prevFlies = (FormBool_t)kAddr_BaseFlies;
static bool __fastcall Hook_BaseFlies(void* base, void*) {
	if (g_prevFlies(base, nullptr)) return true;
	if (base && base == PlayerNPC()) { Profile* p = ProfileForRace(NPCRace(base)); if (p && p->noFallDamage) return true; }
	return false;
}
static void InstallFallDamage() {
	bool any = false;
	for (int i = 0; i < g_numProf; i++) any |= g_prof[i].noFallDamage;
	if (!any) { Log("fall: no NoFallDamage race - not patched"); return; }
	UInt8* site = (UInt8*)kSite_FallFlies;
	if (site[0] != 0xE8) { Log("fall: site %08X is not a call (%02X) - NOT patched", kSite_FallFlies, site[0]); return; }
	UInt32 prev = (UInt32)site + 5 + *(SInt32*)(site + 1);
	g_prevFlies = (FormBool_t)prev;
	DWORD old; VirtualProtect(site, 5, PAGE_EXECUTE_READWRITE, &old);
	*(SInt32*)(site + 1) = (SInt32)((UInt32)Hook_BaseFlies - ((UInt32)site + 5));
	VirtualProtect(site, 5, old, &old);
	Log("fall: flying-creature exemption call %08X -> player NoFallDamage (was %08X%s)", kSite_FallFlies, prev, prev == kAddr_BaseFlies ? ", vanilla" : ", another plugin - chained");
}

// ---------------- ragdoll guard ----------------
// Securitron crash (twice, ~2 s after the race menu, standing still): AI linear task -> Actor eye position
// 0x8A2FA0 -> bhkRagdollController 0xC757B0 (call site 0x8A308D) reads the pose at controller+0xF0, which held an
// hkpConstraintInstance. Actor::InitHavok-ish 0x87E130 makes a new controller (0x2C0 bytes, ctor 0xC7F060), stores it
// at actor+0xAC, then checks its init flag (+0x42, 0x87EA20 at 0x87E39F); on failure it only prints "AI: Could not
// initialize Ragdoll Controller for %s." and keeps the half-built controller. The eye-position call is skipped (no
// ragdoll offset) for a player controller that isn't initialized or has no / a foreign pose, so it can't read the
// unset pose.
static const UInt32 kSite_RagEye = 0x008A308D, kAddr_RagEye = 0x00C757B0;
typedef bool (__fastcall* RagEye_t)(void* ctrl, void* edx, void* out);
static RagEye_t g_prevRagEye = (RagEye_t)kAddr_RagEye;
static void* PlayerRagdoll() { void* pl = Player(); return pl ? *(void**)((UInt8*)pl + 0xAC) : nullptr; }
static bool __fastcall Hook_RagEye(void* ctrl, void*, void* out) {
	if (ctrl && ctrl == PlayerRagdoll()) {
		UInt8* b = (UInt8*)ctrl;
		// the pose reference at +0xF0 must be the controller's own pose (+0x54); the securitron's ends up holding
		// an hkpConstraintInstance with init ok -> the ragdoll offset skipped. With no pose at all (the body part data's
		// headtracking IK node isn't a ragdoll bone: pose matching never set up) both can be null - equal, and the
		// vanilla code then reads bone data through the null pose (lakelurk save load).
		void* pose = *(void**)(b + 0x54);
		if (!b[0x42] || !pose || *(void**)(b + 0xF0) != pose) {
			static int n = 0;
			if (n < 3) { n++; Log("ragdoll: eye position skipped (%s)", !b[0x42] ? "controller not initialized" : !pose ? "no ragdoll pose" : "pose reference is not the controller's pose"); }
			return false;
		}
	}
	return g_prevRagEye(ctrl, nullptr, out);
}
static bool RedirectCall(UInt32 site, void* hook, UInt32 vanilla, UInt32* prevOut, const char* what) {
	UInt8* p = (UInt8*)site;
	if (p[0] != 0xE8) { Log("patch: %s @%08X not a call (%02X) - NOT patched", what, site, p[0]); return false; }
	UInt32 prev = site + 5 + *(SInt32*)(p + 1); *prevOut = prev;
	DWORD old; VirtualProtect(p, 5, PAGE_EXECUTE_READWRITE, &old);
	*(SInt32*)(p + 1) = (SInt32)((UInt32)hook - (site + 5)); VirtualProtect(p, 5, old, &old);
	Log("patch: %s @%08X -> hook (was %08X%s)", what, site, prev, prev == vanilla ? ", vanilla" : ", another plugin - chained");
	return true;
}
static void InstallRagdollGuard() {
	UInt32 prev;
	if (RedirectCall(kSite_RagEye, (void*)Hook_RagEye, kAddr_RagEye, &prev, "ragdoll eye position")) g_prevRagEye = (RagEye_t)prev;
}

static void InstallCameraPivot() {
	UInt8* site = (UInt8*)kSite_CamPivotTerm;
	static const UInt8 expect[11] = {0x8B, 0x0D, 0xD0, 0x07, 0x1E, 0x01, 0xE8, 0x1A, 0x06, 0xB1, 0xFF};   // mov ecx,[Camera1st]; call 0x45BB80
	if (memcmp(site, expect, sizeof(expect))) {
		Log("camera: pivot site %08X bytes unexpected (%02X %02X %02X %02X %02X %02X) -> NOT patched (vanilla camera height)",
			kSite_CamPivotTerm, site[0], site[1], site[2], site[3], site[4], site[5]);
		return;
	}
	UInt8* p = AllocExec(32); if (!p) { Log("camera: VirtualAlloc failed"); return; }
	UInt8* stub = p;
	*p++ = 0x60;                                                             // pushad
	*p++ = 0xFF; *p++ = 0xB5; *(SInt32*)p = -0x414; p += 4;                   // push [ebp-0x414]  (PlayerCharacter*)
	*p++ = 0x8D; *p++ = 0x85; *(SInt32*)p = -0x13C; p += 4;                   // lea eax,[ebp-0x13C] (pivot z)
	*p++ = 0x50;                                                             // push eax
	*p++ = 0xE8; *(SInt32*)p = (SInt32)((UInt32)CamPivotTerm - ((UInt32)p + 4)); p += 4;
	*p++ = 0x83; *p++ = 0xC4; *p++ = 0x08;                                   // add esp,8
	*p++ = 0x61;                                                             // popad
	*p++ = 0xE9; *(SInt32*)p = (SInt32)(kAddr_CamPivotTermEnd - ((UInt32)p + 4)); p += 4;
	DWORD old; VirtualProtect(site, 6, PAGE_EXECUTE_READWRITE, &old);
	site[0] = 0xE9; *(SInt32*)(site + 1) = (SInt32)((UInt32)stub - ((UInt32)site + 5)); site[5] = 0x90;
	VirtualProtect(site, 6, old, &old);
	FlushInstructionCache(GetCurrentProcess(), nullptr, 0);
	Log("camera: 3rd-person pivot term at %08X -> Camera3rd for creature skeletons (stub %p)", kSite_CamPivotTerm, stub);
}

// ---------------- first person: the creature's own body ----------------
// The player's 1st person runs on the human 1st-person skeleton (player+0x694) with the human 1st-person animations;
// a creature body bound to it is a stretched mess. With FirstPersonBody=1 (the default) the engine still runs 1st person (aiming,
// iron sights zoom, VATS, the view toggle), but what is drawn is the 3rd-person creature (its own animations, kept
// updated in 1st person - PlayerCharacter::Update updates both): the 3rd-person root is shown, the 1st-person root
// hidden (the view setter 0x951A10 does the opposite), the FirstPersonHide node is shrunk to nothing (the head), and
// the camera sits at FirstPersonNode + FirstPersonOffset (right, forward, up in the actor's heading frame) - behind
// the creature's hands, like the vanilla view behind the human hands. Menus (Pip-Boy) get the vanilla view back.
// The camera update (0x94AE40) ends with the camera position at [ebp-0x60] (1st person: Camera1st of the 1st-person
// skeleton, 0x94B1F1) and at 0x94BDB4 puts it on the scene camera (and the audio listener, 0x94BE05); the hook
// replaces it there in 1st person. No per-frame work outside the camera update itself.
static const UInt32 kSite_CamFinal = 0x0094BDB4, kAddr_CamFinalCont = 0x0094BDBB;
static const UInt32 kPtr_InterfaceManager = 0x011D8A80, kAddr_FindNodeByName2 = 0x004AAE30;
typedef void* (__cdecl* FindNode_t)(void* root, const char* name);
static void* g_fpRoot = nullptr; static void* g_fpAnchor = nullptr; static void* g_fpHideNode = nullptr;
static float g_fpHideScale = 1.0f; static Profile* g_fpProf = nullptr; static bool g_fpWanted = false, g_fpFlags = false;
static inline UInt32& AVFlags(void* n) { return *(UInt32*)((UInt8*)n + 0x30); }
static inline float* WorldRot(void* n) { return (float*)((UInt8*)n + 0x68); }
static inline float* WorldPos(void* n) { return (float*)((UInt8*)n + 0x8C); }
// Our root visibility in 1st person (3rd-person root shown, 1st-person root hidden) is the engine's 3rd-person
// state, and the view setter 0x951A10 compares the roots' hidden flags first: going back to 3rd person it saw "already
// 3rd person" and returned before its 3rd-person setup (the body stayed missing until VATS rebuilt it). So the
// vanilla 1st-person flags are put back before the engine changes the view (hook on 0x951A10) or opens a menu.
static void FPVanillaFlags(void* player) {
	if (!g_fpFlags || !player) return;
	g_fpFlags = false;
	void* r3 = PlayerRoot(player); void* r1 = *(void**)((UInt8*)player + 0x694);
	if (r3) AVFlags(r3) |= 1;
	if (r1) AVFlags(r1) &= ~1u;
}
static void FPRestore(void* player, const char* why) {
	if (!g_fpActive) return;
	g_fpActive = false;
	if (g_fpHideNode) *(float*)((UInt8*)g_fpHideNode + 0x64) = g_fpHideScale;
	if (player && !*((UInt8*)player + 0x64A)) FPVanillaFlags(player);   // still 1st person (menu)
	else g_fpFlags = false;                                          // 3rd person: our flags are its own
	Log("first person: creature body off (%s)", why);
}
typedef void (__fastcall* ApplyView_t)(void* player, void* edx, UInt8 firstPerson);
static ApplyView_t g_applyViewTramp = nullptr;
static void __fastcall Hook_ApplyView(void* player, void* edx, UInt8 firstPerson) {
	if (g_fpFlags && player == Player()) {
		FPVanillaFlags(player);
		if (g_fpActive) {
			g_fpActive = false; g_fpWanted = false;
			if (g_fpHideNode) *(float*)((UInt8*)g_fpHideNode + 0x64) = g_fpHideScale;
			Log("first person: creature body off (view change to %s)", firstPerson ? "1st person" : "3rd person");
		}
	}
	g_applyViewTramp(player, edx, firstPerson);
}
static void ShrinkSubtreeOnce(void* n) {                                  // this frame: the node and its children
	float* wp = WorldPos(n);
	*(float*)((UInt8*)n + 0x98) = 0.001f;
	void** data = *(void***)((UInt8*)n + 0xA0); UInt16 cnt = *(UInt16*)((UInt8*)n + 0xA6);
	for (UInt16 i = 0; data && i < cnt && i < 64; i++) if (void* c = data[i]) {
		*(float*)((UInt8*)c + 0x98) = 0.001f;
		float* cp = WorldPos(c); cp[0] = wp[0]; cp[1] = wp[1]; cp[2] = wp[2];
	}
}
static void __cdecl FPCamera(float* pos, void* player) {
	if (!player) return;
	Profile* p = PlayerProfile();
	void* im = *(void**)kPtr_InterfaceManager;
	bool menu = im && *(UInt32*)((UInt8*)im + 0x0C) == 2;
	bool first = !*((UInt8*)player + 0x64A) && !*((UInt8*)player + 0x64C) && !*(UInt8*)0x011E07B8;
	void* r3 = PlayerRoot(player); void* r1 = *(void**)((UInt8*)player + 0x694);
	bool want = first && !menu && p && r3 && r1;
	if (!want) { FPRestore(player, !first ? "3rd person" : menu ? "menu" : "not a creature race"); g_fpWanted = false; return; }
	if (!g_fpWanted || r3 != g_fpRoot || p != g_fpProf) {                // 1st person starts (or new skeleton / race)
		if (g_fpActive) FPRestore(player, "skeleton changed");
		g_fpWanted = true; g_fpRoot = r3; g_fpProf = p;
		ReadFirstPersonKeys(*p);                                         // once per start, not per frame
		if (!p->fpBody) return;
		g_fpAnchor = ((FindNode_t)kAddr_FindNodeByName2)(r3, p->fpNode);
		g_fpHideNode = p->fpHide[0] ? ((FindNode_t)kAddr_FindNodeByName2)(r3, p->fpHide) : nullptr;
		if (!g_fpAnchor) { Log("first person: [%s] node '%s' not in the skeleton - vanilla view", p->section, p->fpNode); return; }
		g_fpHideScale = g_fpHideNode ? *(float*)((UInt8*)g_fpHideNode + 0x64) : 1.0f;
		g_fpActive = true;
		Log("first person: [%s] creature body on - camera '%s' %+.1f,%+.1f,%+.1f, hide '%s'%s", p->section, p->fpNode,
			p->fpOff[0], p->fpOff[1], p->fpOff[2], p->fpHide, g_fpHideNode ? "" : " (not found)");
	}
	if (!g_fpActive) return;
	AVFlags(r3) &= ~1u; AVFlags(r1) |= 1; g_fpFlags = true;
	if (g_fpHideNode) { *(float*)((UInt8*)g_fpHideNode + 0x64) = 0.001f; ShrinkSubtreeOnce(g_fpHideNode); }
	const float* m = WorldRot(r3); const float* a = WorldPos(g_fpAnchor); const float* o = p->fpOff;
	pos[0] = a[0] + m[0] * o[0] + m[1] * o[1] + m[2] * o[2];
	pos[1] = a[1] + m[3] * o[0] + m[4] * o[1] + m[5] * o[2];
	pos[2] = a[2] + m[6] * o[0] + m[7] * o[1] + m[8] * o[2];
}
static void InstallFirstPersonBody() {
	UInt8* site = (UInt8*)kSite_CamFinal;
	static const UInt8 expect[7] = {0x8D, 0x55, 0xA0, 0x52, 0x8B, 0x4D, 0x98};   // lea edx,[ebp-0x60]; push edx; mov ecx,[ebp-0x68]
	if (memcmp(site, expect, sizeof(expect))) {
		Log("first person: camera site %08X bytes unexpected (%02X %02X %02X %02X) -> NOT patched", kSite_CamFinal, site[0], site[1], site[2], site[3]);
		return;
	}
	UInt8* p = AllocExec(48); if (!p) { Log("first person: VirtualAlloc failed"); return; }
	UInt8* stub = p;
	*p++ = 0x60;                                                             // pushad
	*p++ = 0xFF; *p++ = 0xB5; *(SInt32*)p = -0x414; p += 4;                   // push [ebp-0x414]  (PlayerCharacter*)
	*p++ = 0x8D; *p++ = 0x45; *p++ = 0xA0;                                   // lea eax,[ebp-0x60]  (camera position)
	*p++ = 0x50;                                                             // push eax
	*p++ = 0xE8; *(SInt32*)p = (SInt32)((UInt32)FPCamera - ((UInt32)p + 4)); p += 4;
	*p++ = 0x83; *p++ = 0xC4; *p++ = 0x08;                                   // add esp,8
	*p++ = 0x61;                                                             // popad
	memcpy(p, expect, sizeof(expect)); p += sizeof(expect);                  // the replaced instructions
	*p++ = 0xE9; *(SInt32*)p = (SInt32)(kAddr_CamFinalCont - ((UInt32)p + 4)); p += 4;
	DWORD old; VirtualProtect(site, 7, PAGE_EXECUTE_READWRITE, &old);
	site[0] = 0xE9; *(SInt32*)(site + 1) = (SInt32)((UInt32)stub - ((UInt32)site + 5));
	site[5] = 0x90; site[6] = 0x90;
	VirtualProtect(site, 7, old, &old);
	FlushInstructionCache(GetCurrentProcess(), nullptr, 0);
	Log("first person: camera position hook at %08X (stub %p)", kSite_CamFinal, stub);
	// view setter 0x951A10 (thiscall(player, bool firstPerson), ret 4): prologue 55 8B EC 6A FF (5 bytes) copied
	UInt8* fn = (UInt8*)0x00951A10;
	static const UInt8 pro[5] = {0x55, 0x8B, 0xEC, 0x6A, 0xFF};
	if (memcmp(fn, pro, 5)) { Log("first person: view setter 00951A10 bytes unexpected (%02X %02X %02X) -> NOT hooked", fn[0], fn[1], fn[2]); return; }
	UInt8* t = AllocExec(16); if (!t) return;
	memcpy(t, pro, 5); t[5] = 0xE9; *(SInt32*)(t + 6) = (SInt32)((UInt32)fn + 5 - ((UInt32)t + 10));
	g_applyViewTramp = (ApplyView_t)t;
	DWORD o2; VirtualProtect(fn, 5, PAGE_EXECUTE_READWRITE, &o2);
	fn[0] = 0xE9; *(SInt32*)(fn + 1) = (SInt32)((UInt32)Hook_ApplyView - ((UInt32)fn + 5));
	VirtualProtect(fn, 5, o2, &o2);
	FlushInstructionCache(GetCurrentProcess(), fn, 5);
	Log("first person: view setter 00951A10 hooked (trampoline %p)", t);
}


// ---------------- creature voices ----------------
// BSSoundHandle (0xC) and the engine calls JIP LN uses for PlaySound3D/PlaySound3DNode (1.4.0.525):
//   BSAudioManager (object @0x11F6EF0)::InitSoundForm 0xAE5870(this, handle*, formID, flags)
//   handle: SetPos 0xAD8B60(x,y,z)  SetNiNode 0xAD8F20(node; the audio thread holds a NiPointer)  Play 0xAD8830(0)
//   Stop 0xAD88F0() - queues audio message 4 (0xAD88B0 queues 3 = pause; menus use that one).
struct SoundHandle { UInt32 key; UInt8 ok; UInt8 pad[3]; UInt32 unk8; };
static const UInt32 kObj_AudioManager = 0x011F6EF0, kAddr_InitSoundForm = 0x00AE5870;
static const UInt32 kAddr_SoundSetPos = 0x00AD8B60, kAddr_SoundSetNode = 0x00AD8F20, kAddr_SoundPlay = 0x00AD8830, kAddr_SoundStop = 0x00AD88F0;
static const UInt32 kSoundFlags_3D = 0x102, kSoundFlag_Loop = 0x10;
typedef void (__fastcall* InitSoundForm_t)(void* mgr, void* edx, SoundHandle* s, UInt32 formID, UInt32 flags);
typedef void (__fastcall* SoundSetPos_t)(SoundHandle* s, void* edx, float x, float y, float z);
typedef void (__fastcall* SoundSetNode_t)(SoundHandle* s, void* edx, void* node);
typedef void (__fastcall* SoundPlay_t)(SoundHandle* s, void* edx, UInt32 a);
typedef void (__fastcall* SoundStop_t)(SoundHandle* s, void* edx);

static bool StartSound(UInt32 fid, void* node, UInt32 flags, SoundHandle* out) {
	if (!fid || !node) return false;
	SoundHandle h; h.key = 0xFFFFFFFF; h.ok = 0; h.unk8 = 0;
	((InitSoundForm_t)kAddr_InitSoundForm)((void*)kObj_AudioManager, nullptr, &h, fid, flags);
	if (h.key == 0xFFFFFFFF) return false;
	const float* wt = (const float*)((UInt8*)node + 0x8C);                // NiAVObject world translate
	((SoundSetPos_t)kAddr_SoundSetPos)(&h, nullptr, wt[0], wt[1], wt[2]);
	((SoundSetNode_t)kAddr_SoundSetNode)(&h, nullptr, node);
	((SoundPlay_t)kAddr_SoundPlay)(&h, nullptr, 0);
	if (out) *out = h;
	return true;
}
static UInt32 g_rng = 0;
static UInt32 Roll100() {                                                  // xorshift32, 0..99
	if (!g_rng) g_rng = GetTickCount() | 1;
	g_rng ^= g_rng << 13; g_rng ^= g_rng >> 17; g_rng ^= g_rng << 5;
	return g_rng % 100;
}
static bool Gate(UInt32 chance, UInt32 cooldownMs, DWORD* last) {
	DWORD now = GetTickCount();
	if (*last && now - *last < cooldownMs) return false;
	if (Roll100() >= chance) return false;
	*last = now;
	return true;
}

// looping voice (e.g. Ghost People's ConsciousLoop wheeze), attached to the player's 3rd-person root
static SoundHandle g_loop = {0xFFFFFFFF, 0, {0, 0, 0}, 0};
static void* g_loopNode = nullptr;
static UInt32 g_loopFid = 0;
static void StopLoop(const char* why) {
	if (g_loop.key != 0xFFFFFFFF) {
		((SoundStop_t)kAddr_SoundStop)(&g_loop, nullptr);
		Log("voice: loop stopped (%s)", why);
	}
	g_loop.key = 0xFFFFFFFF; g_loopNode = nullptr; g_loopFid = 0;
}
static inline bool PlayerDead(void* player) {
	UInt32 life = *(UInt32*)((UInt8*)player + 0x108);                   // Actor::lifeState: 1 dying, 2 dead
	return life == 1 || life == 2;
}
// newRoot: the node from OnRefSet3D. That message arrives before the player's render state points at the new root
// (the render state is still null there).
static void UpdateLoop(const char* why, void* newRoot) {
	void* player = Player();
	Profile* p = player ? PlayerProfile() : nullptr;
	void* node = newRoot ? newRoot : (player ? PlayerRoot(player) : nullptr);
	UInt32 fid = (p && p->loopSnd.fid && node && !PlayerDead(player)) ? p->loopSnd.fid : 0;
	if (fid == g_loopFid && node == g_loopNode && g_loop.key != 0xFFFFFFFF) return;
	StopLoop(why);
	if (!fid) return;
	if (StartSound(fid, node, kSoundFlags_3D | kSoundFlag_Loop, &g_loop)) {
		g_loopNode = node; g_loopFid = fid;
		Log("voice: loop %08X started on %p (%s)", fid, node, why);
	} else Log("voice: loop %08X could not start (%s)", fid, why);
}

// ======================================================================================================
// race traits: radiation immunity, Dead Money cloud immunity, Ghost People's essential "semi-dead" state
// ======================================================================================================
static UInt8* AllocExec(UInt32 n) { return (UInt8*)VirtualAlloc(nullptr, n, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE); }
template <typename T> static inline T& At(void* p, UInt32 off) { return *(T*)((UInt8*)p + off); }
static inline void* VFn(void* obj, UInt32 off) { return (*(void***)obj)[off / 4]; }
typedef float (__fastcall* GetAV_t)(void*, void*, UInt32);
static float GetAV(void* actor, UInt32 av) {
	void* owner = (UInt8*)actor + 0xA4;
	return ((GetAV_t)VFn(owner, 0x0C))(owner, nullptr, av);
}
enum { kAV_Health = 0x10, kAV_RadResist = 0x14, kAV_PerceptionCond = 0x19, kAV_EnduranceCond = 0x1A, kAV_LeftAttackCond = 0x1B,
       kAV_RightAttackCond = 0x1C, kAV_LeftMobilityCond = 0x1D, kAV_RightMobilityCond = 0x1E };

// ---- race abilities live on the RACE records (SPLO, "<Race> Physiology": the creature's own effects + radiation
// immunity); the DLL no longer adds or removes abilities. It only raises the resistance cap below while the player is
// a RadImmune / ResistCap race, and logs the resistances after the race menu (shows whether the engine applied them).
static void ApplyMaxResist(const char* why);
// The engine loads a RACE's SPLO into its TESSpellList (race+0x2C; list = +4 -> race+0x30, {data, next} nodes,
// 0x717e50) but never gives those spells to the player (-30: unhooded Ghost Person after the race menu,
// Rad Resist 8 / Fire 0). So when the race menu closes the DLL adds the player's race abilities once with the engine's
// AddSpell (Actor vtbl 0x3E0; false = already known). Nothing is removed and race changes aren't tracked:
// the only later change is Tranquility Lane's AgeRace to the child race, which lists the same ability.
typedef bool (__fastcall* SpellFn_t)(void* actor, void* edx, void* spell);
// GiveItems=: the race's own items (robots: a playable, undroppable copy of their built-in weapon) - exactly one
// each, not equipped. Through xNVSE's console interface (RemoveItem / AddItem, messages suppressed): a copy already
// carried is replaced, so closing the race menu again never stacks them.
static NVSEConsoleInterface* g_console = nullptr;
static void GiveRaceItems(const char* why) {
	void* npc = PlayerNPC(); if (!npc) return;
	Profile* p = ProfileForRace(NPCRace(npc));
	if (!p || !p->numGive) return;
	if (!g_console || !g_console->RunScriptLine2) { Log("give: no console interface - items not given (%s)", why); return; }
	for (int i = 0; i < p->numGive; i++) {
		UInt32 fid = p->give[i].fid; if (!fid) continue;
		char line[96];
		snprintf(line, sizeof(line), "player.removeitem %08X 99 1", fid); g_console->RunScriptLine2(line, nullptr, true);
		snprintf(line, sizeof(line), "player.additem %08X 1 1", fid); bool ok = g_console->RunScriptLine2(line, nullptr, true);
		Log("give: %08X %s (%s)", fid, ok ? "given" : "FAILED", why);
	}
}
// GivePerks=: perks the race's player gets, once (the HasPerk command's own check, Actor vtbl 0x4A0(perk, teammate) =
// rank, so closing the race menu again never adds a second rank); added through the console's AddPerk (messages off).
// Nothing is removed on a later race change.
typedef UInt8 (__fastcall* PerkRank_t)(void* actor, void* edx, void* perk, bool teammate);
static void GiveRacePerks(const char* why) {
	void* pl = Player(); void* npc = PlayerNPC(); if (!pl || !npc) return;
	Profile* p = ProfileForRace(NPCRace(npc));
	if (!p || !p->numPerks) return;
	if (!g_console || !g_console->RunScriptLine2) { Log("perks: no console interface - not given (%s)", why); return; }
	for (int i = 0; i < p->numPerks; i++) {
		UInt32 fid = p->perks[i].fid; void* perk = fid ? LookupForm(fid) : nullptr; if (!perk) continue;
		if (((PerkRank_t)VFn(pl, 0x4A0))(pl, nullptr, perk, false)) { Log("perks: %08X already had (%s)", fid, why); continue; }
		char line[64]; snprintf(line, sizeof(line), "player.addperk %08X", fid);
		bool ok = g_console->RunScriptLine2(line, nullptr, true);
		Log("perks: %08X %s (%s)", fid, ok ? "added" : "FAILED", why);
	}
}
static void GiveRaceAbilities(const char* why) {
	void* player = Player(); void* npc = PlayerNPC(); if (!player || !npc) return;
	void* race = NPCRace(npc);
	if (!race || !ProfileForRace(race)) return;                      // only Playable Creatures races
	struct Node { void* data; Node* next; };
	int n = 0;
	for (Node* it = (Node*)((UInt8*)race + 0x30); it && n < 16; it = it->next, n++) {
		void* sp = it->data;
		if (!sp || *((UInt8*)sp + 4) != kFormType_SPEL) continue;
		bool added = ((SpellFn_t)VFn(player, 0x3E0))(player, nullptr, sp);
		Log("race ability: %08X %s (%s)", *(UInt32*)((UInt8*)sp + 0x0C), added ? "added" : "already known", why);
	}
}
// fPlayerMaxResistance (Setting 0x11D0AD8, default 85) caps the player's resistances. While the player is a
// RadImmune race its value is raised to 100 at runtime (the setting's float, via its accessor 0x403E20) and the
// original value is put back when leaving the race. With the ability's +100 Rad Resistance that is full immunity from
// every source the engine resists (environment, food / water / chems, attacks); no code paths are patched.
static const UInt32 kSetting_PlayerMaxResist = 0x011D0AD8, kAddr_SettingGetPtr = 0x00403E20;
typedef float* (__fastcall* SettingPtr_t)(void* setting, void* edx);
static float g_origMaxResist = 0.0f; static bool g_maxResistRaised = false;
static void ApplyMaxResist(const char* why) {
	float* v = ((SettingPtr_t)kAddr_SettingGetPtr)((void*)kSetting_PlayerMaxResist, nullptr);
	if (!v) return;
	Profile* p = Player() ? PlayerProfile() : nullptr;
	float cap = p ? (p->radImmune ? 100.0f : (p->resistCap > 0 ? (float)p->resistCap : 0.0f)) : 0.0f;   // ResistCap
	if (cap > 0.0f) {
		if (!g_maxResistRaised) { g_origMaxResist = *v; g_maxResistRaised = true; }
		if (*v != cap) { Log("rad: fPlayerMaxResistance %.0f -> %.0f (%s)", *v, cap, why); *v = cap; }
	} else if (g_maxResistRaised) {
		Log("rad: fPlayerMaxResistance restored to %.0f (%s)", g_origMaxResist, why);
		*v = g_origMaxResist; g_maxResistRaised = false;
	}
}

// a per-race over-the-shoulder offset (fOverShoulderPosX / PosZ game settings, ini CameraOffsetX / Z) was tried
// for the Securitron and removed in (their 3rd-person camera mod handles the camera).

// ---- Dead Money toxic cloud: the cloud's scripts don't run while the player's race is CloudImmune ----
// Script::Execute (0x5AC1E0, thiscall(thisObj, eventList, containingObj, bool) ret 0x10) is the entry every script
// run goes through (object / quest / effect scripts, event blocks). For three Dead Money scripts it returns at once:
//   NVDLC01ToxicCloudTriggerSCRIPT 00C544 (cloud triggers: OnTriggerEnter/Leave Player -> counters, ISFX, weather,
//   message, StartQuest), NVDLC01ToxicCloudSCRIPT 00C542 (the quest's damage loop), NVDLC01GlobalToxicDamageSCRIPT
//   00E883 (hardcore Villa damage + hit flash). So the cloud never starts for an immune player - no damage, no screen
//   effect, no weather swap, no message (what Ghostification does by editing the trigger script). Data untouched.
static const UInt32 kAddr_ScriptExecute = 0x005AC1E0;
typedef bool (__fastcall* ScriptExec_t)(void* script, void* edx, void* thisObj, void* eventList, void* containing, bool arg);
static ScriptExec_t g_scriptExecTramp = nullptr;
static UInt32 g_cloudScripts[3] = {0, 0, 0};
static UInt32 g_cloudSkipped = 0;
static bool __fastcall Hook_ScriptExecute(void* script, void* edx, void* thisObj, void* eventList, void* containing, bool arg) {
	if (script && g_cloudScripts[0]) {
		UInt32 sid = At<UInt32>(script, 0x0C);
		if (sid == g_cloudScripts[0] || sid == g_cloudScripts[1] || sid == g_cloudScripts[2]) {
			Profile* p = Player() ? PlayerProfile() : nullptr;
			if (p && p->cloudImmune) {
				if (!(g_cloudSkipped++ % 200)) Log("cloud: script %08X skipped for [%s] (x%u)", sid, p->section, g_cloudSkipped);
				return true;
			}
		}
	}
	return g_scriptExecTramp(script, edx, thisObj, eventList, containing, arg);
}
static void InstallCloudHook() {                                     // at load (address only)
	bool any = false; for (int i = 0; i < g_numProf; i++) any |= g_prof[i].cloudImmune;
	if (!any) return;
	g_scriptExecTramp = (ScriptExec_t)Detour(kAddr_ScriptExecute, 0x08, (void*)Hook_ScriptExecute, "Script::Execute");
}
static void ResolveCloudScripts() {                                  // at DeferredInit (load order known)
	if (!g_scriptExecTramp) return;
	UInt32 t = ResolveFID("DeadMoney.esm", 0x00C544), q = ResolveFID("DeadMoney.esm", 0x00C542), g = ResolveFID("DeadMoney.esm", 0x00E883);
	if (!t) { Log("cloud: DeadMoney.esm not loaded - nothing to skip"); return; }
	g_cloudScripts[1] = q; g_cloudScripts[2] = g; g_cloudScripts[0] = t;
	Log("cloud: scripts %08X / %08X / %08X skipped for CloudImmune races", t, q, g);
}

// ---- race factions: Faction=Plugin|FormID[,...] = the species' in-game factions; with JoinFaction=1 they
// are joined (rank 0) while in the race and left again afterwards. JoinFaction=0 (default): never joined or left.
// Actor::SetFactionRank 0x8B8580 thiscall(faction, rank; -1 = leave) and GetFactionRank 0x8B8290 thiscall(faction,
// isPlayer) - the functions the SetFactionRank / GetFactionRank commands use. A faction the player was already in
// (e.g. from a quest) is never removed by ApplyFaction.
typedef void (__fastcall* SetFactionRank_t)(void* actor, void* edx, void* faction, SInt32 rank);
typedef SInt32 (__fastcall* GetFactionRank_t)(void* actor, void* edx, void* faction, bool isPlayer);
static UInt32 g_factionJoined[8] = {0}; static int g_numJoined = 0;
static bool ProfileWantsFaction(Profile* p, UInt32 fid) {
	if (!p || !p->joinFaction) return false;
	for (int i = 0; i < p->numFactions; i++) if (p->factions[i].fid == fid) return true;
	return false;
}
static void ApplyFaction(const char* why) {
	void* player = Player(); if (!player) return;
	Profile* p = PlayerProfile();
	int keep = 0;
	for (int i = 0; i < g_numJoined; i++) {                          // leave what this session joined and no longer applies
		UInt32 fid = g_factionJoined[i];
		if (ProfileWantsFaction(p, fid)) { g_factionJoined[keep++] = fid; continue; }
		if (void* f = LookupForm(fid)) { ((SetFactionRank_t)0x008B8580)(player, nullptr, f, -1); Log("faction: left %08X (%s)", fid, why); }
	}
	g_numJoined = keep;
	if (!p || !p->joinFaction) return;
	for (int i = 0; i < p->numFactions; i++) {
		UInt32 want = p->factions[i].fid; if (!want) continue;
		bool have = false; for (int j = 0; j < g_numJoined; j++) if (g_factionJoined[j] == want) have = true;
		if (have) continue;
		void* f = LookupForm(want); if (!f) continue;
		SInt32 rank = ((GetFactionRank_t)0x008B8290)(player, nullptr, f, true);
		if (rank >= 0) { Log("faction: already in %08X (rank %d) - left as is (%s)", want, rank, why); continue; }
		((SetFactionRank_t)0x008B8580)(player, nullptr, f, 0);
		if (g_numJoined < 8) g_factionJoined[g_numJoined++] = want;
		Log("faction: joined %08X (%s)", want, why);
	}
}
// On an explicit race change (race menu closed) leave every faction of a JoinFaction=1 race that the new race doesn't
// use - also one joined in an earlier session (membership is saved, our bookkeeping isn't). Races with JoinFaction=0
// are never touched.
static void CleanupFactions(const char* why) {
	void* player = Player(); if (!player) return;
	Profile* cur = PlayerProfile();
	for (int i = 0; i < g_numProf; i++) {
		if (!g_prof[i].joinFaction) continue;
		for (int k = 0; k < g_prof[i].numFactions; k++) {
			UInt32 fid = g_prof[i].factions[k].fid;
			if (!fid || ProfileWantsFaction(cur, fid)) continue;
			void* f = LookupForm(fid); if (!f) continue;
			if (((GetFactionRank_t)0x008B8290)(player, nullptr, f, true) < 0) continue;
			((SetFactionRank_t)0x008B8580)(player, nullptr, f, -1);
			for (int j = 0; j < g_numJoined; j++) if (g_factionJoined[j] == fid) g_factionJoined[j] = g_factionJoined[--g_numJoined];
			Log("faction: left %08X (%s)", fid, why);
		}
	}
}

// ---- ghost moves on the jump key ----
// The player's jump starts in Actor vtbl slot 0x254 (Character/PlayerCharacter 0x884AA0: puts fJumpHeightMin on the
// character controller, then the jump-start event 0x838780). PlayerCharacter::Update calls that slot only when the
// jump key was pressed and the controller can jump (0x942158 -> 0x944400). Replacing the call for the player's vtable
// (0x108AA3C + 0x254) means the jump is never started - no jump height, no airborne state - when a move is chosen:
//   strafing (left/right)              -> hop: Dead Money's HopLeft / HopRight idle + PCGhostMoveSpell
//                                         (Turbo + crit 1 s, SetGhost 1 s)
//   walking backward, holstered -> search: trash-pick idle (PCGhostTrashPick, whole body) + PCGhostSearchSpell (loot after 5 s)
//   walking backward, weapon out -> back dodge: PCGhostDodgeBack (whole body; the body shrinks out of sight in its gas
//                                         cloud and slips back, its root motion) + its own spell (the hop's + a short
//                                         speed boost: root motion moves the player no faster than its move speed)
// anything else jumps normally.
static const UInt32 kSlot_PlayerJump = 0x0108AA3C + 0x254, kAddr_ActorJump = 0x00884AA0;
static const UInt32 kAddr_GetMovementFlags = 0x008846E0, kAddr_IsWeaponOut = 0x008A16D0, kAddr_IsSneaking = 0x004997B0,
	kAddr_ActorAnimData = 0x008B70D0, kAddr_CasterPrep = 0x00815B00;
typedef void* (__fastcall* Jump_t)(void*, void*);
typedef UInt32 (__fastcall* U32_t)(void*, void*);
typedef bool (__fastcall* B_t)(void*, void*);
typedef UInt32 (__fastcall* Dodge_t)(void*, void*, UInt32);
typedef void* (__fastcall* P_t)(void*, void*);
typedef void (__fastcall* V_t)(void*, void*);
typedef void (__fastcall* Cast_t)(void* caster, void*, void* spell, UInt32, void* target, float, UInt32);
typedef void (__fastcall* QueueIdle_t)(void*, void*, void*, UInt32);
static Jump_t g_origJump = (Jump_t)kAddr_ActorJump;
static void CastOnSelf(void* actor, UInt32 spellFid) {             // the CastImmediateOnSelf command's steps (0x5C1FE0)
	void* spell = LookupForm(spellFid); if (!spell) return;
	void* caster = ((P_t)VFn(actor, 0x198))(actor, nullptr);
	void* target = ((P_t)VFn(actor, 0x19C))(actor, nullptr);
	if (!caster || !target) return;
	((V_t)kAddr_CasterPrep)(caster, nullptr);
	// MagicCaster::CastSpell (0x815740) takes the MagicItem sub-object (SpellItem + 0x18, RTTI), as the
	// command's ExtractArgs hands it over (the form pointer crashes in the cast, 0x8160CF)
	((Cast_t)VFn(caster, 0x0C))(caster, nullptr, (UInt8*)spell + 0x18, 0, target, 1.0f, 0);
}
// the PlayIdle script command's own mechanism (exec 0x5CB2D0): the process keeps the idle to force
// (HighProcess vtbl 0x71C -> process + 0x350) and the "play forced idle" flag 0x80 (vtbl 0x614 ORs process + 0x424).
// The actor's next update (0x8BA600, also run by the player's update at 0x94380E) takes it (vtbl 0x718) and starts it
// with 0x497F20 - no idle-tree / skeleton-folder check, so Dead Money's ghost idles play on our Ghost skeleton.
// (0x497CA0, the knock-down get-up queue, is only drained in the knocked-state handler: idles queued there never
// start.)
typedef void (__fastcall* SetPtr_t)(void*, void*, void*);
typedef void (__fastcall* SetU32_t)(void*, void*, UInt32);
static bool PlayIdleForm(void* actor, UInt32 idleFid) {
	void* idle = LookupForm(idleFid); if (!idle) return false;
	void* proc = At<void*>(actor, 0x68); if (!proc) return false;
	((SetPtr_t)VFn(proc, 0x71C))(proc, nullptr, idle);
	((SetU32_t)VFn(proc, 0x614))(proc, nullptr, 0x80);
	return true;
}
// the scan / search idles are stand-still animations, but the key that triggered the scan (back) is usually still
// held: the next movement update starts the walk and the walk replaces the idle. The engine's own way to keep the player
// still is to mask the movement bits it hands to the PlayerMover (PlayerCharacter::Update 0x941D26 clears bits 0-5 -
// directions + walk/run - while in VATS). Same here: PlayerMover::SetMovementFlags (vtbl 0x0C, 0x9EA3E0; the player is
// the only PlayerMover) gets the direction / walk / run bits cleared while the player's current special idle (anim data
// +0x128 -> sequence +0x18 = IDLE form) is the scan or search idle - the lock ends with the idle itself. The forced idle
// starts in the actor update that follows the next movement update, so that one update is covered by g_holdPending.
static const UInt32 kSlot_PlayerMoverSetFlags = 0x0109297C + 0x0C, kAddr_PlayerMoverSetFlags = 0x009EA3E0;
typedef void (__fastcall* MoverFlags_t)(void*, void*, UInt32);
static MoverFlags_t g_origMoverFlags = (MoverFlags_t)kAddr_PlayerMoverSetFlags;
static int g_holdPending = 0;
static bool IsHoldIdle(void* idle, UInt32 holdFid) {
	if (!idle) return false;
	UInt32 id = At<UInt32>(idle, 0x0C);
	return id && id == holdFid;
}
// anim data +0x124 = the idle being played, +0x128 = the forced idle waiting to start (0x497F20 stores it there,
// 0x498290 starts it); both hold an idle-play object (ctor 0x4965D0) whose IDLE form is at +0x2C (+0x14 section,
// +0x18 the anim sequence; the sequence at +0x18 is not the idle).
// -> 1 the search idle, 2 the back dodge, 0 neither
static int HoldIdlePlaying(void* actor, void* ad) {
	Profile* p = PlayerProfile();
	if (!ad || !p) return 0;
	for (UInt32 off = 0x124; off <= 0x128; off += 4) {
		void* obj = At<void*>(ad, off);
		void* idle = obj ? At<void*>(obj, 0x2C) : nullptr;
		if (IsHoldIdle(idle, p->ghostForms[2].fid)) return 1;
		if (IsHoldIdle(idle, p->ghostForms[5].fid)) return 2;
		for (int k = 0; k < p->numTaunts; k++) if (IsHoldIdle(idle, p->taunts[k].fid)) return 1;
	}
	return 0;
}
static int HoldIdleKind(void* pl) {
	int a = HoldIdlePlaying(pl, ((P_t)kAddr_ActorAnimData)(pl, nullptr)), b = HoldIdlePlaying(pl, ((P_t)VFn(pl, 0x1E4))(pl, nullptr));
	return a > b ? a : b;
}
// The search is held still (movement bits cleared); the back dodge is not held - like the hops it moves the player by
// its own root motion (Bip01 keys) with the movement keys left alone.
static bool g_holdLogged = false;
static void __fastcall Hook_PlayerMoverSetFlags(void* mover, void* edx, UInt32 flags) {
	if (flags & 0x3F) {
		void* pl = Player(); Profile* p = pl ? PlayerProfile() : nullptr;
		if (p && (p->ghostMoves || p->numTaunts)) {
			bool hold = HoldIdleKind(pl) == 1;
			if (hold || g_holdPending > 0) flags &= ~0x3Fu;
			if (hold != g_holdLogged) { g_holdLogged = hold; Log("ghost move: movement hold %s", hold ? "on (search idle playing)" : "off"); }
		}
	}
	if (g_holdPending > 0) g_holdPending--;
	g_origMoverFlags(mover, edx, flags);
}
static void* __fastcall Hook_PlayerJump(void* actor, void* edx) {
	Profile* p = (actor == Player()) ? PlayerProfile() : nullptr;
	if (!p || (!p->ghostMoves && !p->numTaunts)) return g_origJump(actor, edx);
	// while the scan / search idle plays (or is about to start) the jump key does nothing: the hold keeps the movement
	// bits at 0 during the idle, otherwise a second press reads "standing still, not sneaking" and starts a real jump,
	// which replaces the idle.
	if (g_holdPending > 0 || HoldIdleKind(actor)) {
		Log("ghost move: jump ignored - search / dodge idle playing"); return nullptr;
	}
	UInt32 mv = ((U32_t)kAddr_GetMovementFlags)(actor, nullptr) & 0xF;
	bool out = ((B_t)kAddr_IsWeaponOut)(actor, nullptr), sneak = ((B_t)kAddr_IsSneaking)(actor, nullptr);
	if (!p->ghostMoves) {
		// TauntIdles=: back + jump plays the race's taunts in turn, held still like the search (a stand-still idle: the
		// held back key would start the walk, which replaces it); anything else jumps normally
		static int next = 0;
		if (mv == 2) {
			for (int tries = 0; tries < p->numTaunts; tries++) {
				UInt32 fid = p->taunts[(next + tries) % p->numTaunts].fid; if (!fid) continue;
				if (PlayIdleForm(actor, fid)) {
					next = (next + tries + 1) % p->numTaunts; g_holdPending = 2; Log("taunt: %08X", fid); return nullptr;
				}
			}
		}
		return g_origJump(actor, edx);
	}
	if (mv & 0xC) {
		// the hop is Dead Money's own HopLeft / HopRight idle (the ghosts' combat hop), played like the scan /
		// search idles (the engine dodge's DodgeLeft/Right groups never reach the player's anim map).
		bool left = (mv & 4) != 0;
		if (PlayIdleForm(actor, p->ghostForms[left ? 3 : 4].fid)) {
			CastOnSelf(actor, p->ghostForms[0].fid); Log("ghost move: hop %s", left ? "left" : "right"); return nullptr;
		}
		Log("ghost move: hop idle missing - normal jump");
	} else if (mv == 2 && !out) {
		// the search (trash pick) is back + jump with the weapon holstered
		if (PlayIdleForm(actor, p->ghostForms[2].fid)) { g_holdPending = 2; CastOnSelf(actor, p->ghostForms[1].fid); Log("ghost move: search"); return nullptr; }
	} else if (mv == 2 && out && p->ghostForms[5].fid) {
		// the back dodge: played as the hops (no hold), its root motion carries the player back
		if (PlayIdleForm(actor, p->ghostForms[5].fid)) {
			CastOnSelf(actor, p->ghostForms[p->ghostForms[6].fid ? 6 : 0].fid); Log("ghost move: back dodge"); return nullptr;
		}
	}
	Log("ghost move: normal jump (movement %X, weapon out %d, sneaking %d)", mv, out, sneak);
	return g_origJump(actor, edx);
}
static void InstallGhostMoves() {                                    // at load
	bool any = false; for (int i = 0; i < g_numProf; i++) any |= g_prof[i].ghostMoves || g_prof[i].numTaunts;
	if (!any) return;
	UInt32 cur = *(UInt32*)kSlot_PlayerJump;
	g_origJump = (Jump_t)cur;
	PatchPtr(kSlot_PlayerJump, (UInt32)Hook_PlayerJump, cur, cur == kAddr_ActorJump ? "PlayerCharacter jump start (vtbl 0x254)" : "PlayerCharacter jump start (chained)");
	cur = *(UInt32*)kSlot_PlayerMoverSetFlags;
	g_origMoverFlags = (MoverFlags_t)cur;
	PatchPtr(kSlot_PlayerMoverSetFlags, (UInt32)Hook_PlayerMoverSetFlags, cur, cur == kAddr_PlayerMoverSetFlags ? "PlayerMover::SetMovementFlags (vtbl 0x0C)" : "PlayerMover::SetMovementFlags (chained)");
}

// ---- Ghost People: NVDLC01GhostSCRIPT for the player ----
// Essential = ref flag Actor+0x140 bit31 (set via 0x8C1AC0, as SetActorRefEssential; not saved, so re-applied on load).
static const UInt32 kAddr_SetRefEssential = 0x008C1AC0, kAddr_SetLifeState = 0x008A1800, kAddr_Kill = 0x0089D900,
	kAddr_Dismember = 0x008B51B0, kAddr_KillDeferCheck = 0x008C7AA0, kAddr_TaskQueue = 0x004537B0, kAddr_QueueKill = 0x0087AFF0,
	kAddr_FormHeapAlloc = 0x00401000;
typedef void (__fastcall* SetEss_t)(void*, void*, bool);
typedef void (__fastcall* SetLife_t)(void*, void*, UInt32);
typedef void (__fastcall* Kill_t)(void*, void*, void* killer, float);
typedef void (__fastcall* Dismember_t)(void*, void*, SInt32 cause, SInt32 limb, void* killer);
typedef bool (__cdecl* Bool0_t)();
typedef void* (__cdecl* Ptr0_t)();
typedef void (__fastcall* QueueKill_t)(void* queue, void*, void* actor, void* fdata, void* ldata);
typedef void* (__cdecl* Alloc_t)(UInt32);
typedef void (__fastcall* ModAV_t)(void* actor, void*, UInt32 av, float delta, void* attacker);
typedef bool (__fastcall* VBool1_t)(void*, void*, UInt32);
static bool g_essentialSet = false;      // we set the flag (so we clear it again when leaving the race)
static bool g_ghostDown = false;         // down (essential knockdown) until the revive
static inline bool RefEssential(void* a) { return (At<UInt32>(a, 0x140) & 0x80000000u) != 0; }
static void SetRefEssential(void* a, bool on, const char* why) {
	if (RefEssential(a) == on) return;
	((SetEss_t)kAddr_SetRefEssential)(a, nullptr, on);
	Log("ghost: player essential %d (%s)", on, why);
}
// GhostEssential=1: the player is always essential (set at race
// menu / load / 3D set, never touched while down). A hit that leaves a body part crippled (xNVSE OnHit, after
// the damage) clears essential and kills with that limb dismembered (KillActor's steps). Nothing else is checked.
static bool g_ghostRealDeath = false;
static const char* kLimbName(SInt32 l) {
	switch (l) { case 1: return "head"; case 3: return "left arm"; case 5: return "right arm"; case 7: return "left leg"; case 10: return "right leg"; default: return "none"; }
}
// KillActor <killer> <limb> on the player (same steps as the KillActor command, 0x5BE2A0)
static void GhostRealDeath(void* killer, SInt32 limb, const char* why) {
	void* player = Player(); if (!player || g_ghostRealDeath) return;
	g_ghostRealDeath = true; g_ghostDown = false;
	SetRefEssential(player, false, "real death");
	Log("ghost: real death (%s), killer %08X, dismember %s", why, killer ? At<UInt32>(killer, 0x0C) : 0, kLimbName(limb));
	if (((VBool1_t)VFn(player, 0x1A0))(player, nullptr, 0)) limb = -1;
	if (At<UInt32>(player, 0x108) == 6) ((SetLife_t)kAddr_SetLifeState)(player, nullptr, 0);
	if (((Bool0_t)kAddr_KillDeferCheck)()) {                              // off the main thread: the engine's queued kill
		UInt32* ld = nullptr;
		if (limb != -1) { ld = (UInt32*)((Alloc_t)kAddr_FormHeapAlloc)(12); ld[0] = (UInt32)limb; ld[1] = (UInt32)-1; ld[2] = (UInt32)killer; }
		float* fd = (float*)((Alloc_t)kAddr_FormHeapAlloc)(4); *fd = 0.0f;
		At<void*>(player, 0xC0) = killer;
		((QueueKill_t)kAddr_QueueKill)(((Ptr0_t)kAddr_TaskQueue)(), nullptr, player, fd, ld);
		Log("ghost: kill queued (off main thread)");
		return;
	}
	((Kill_t)kAddr_Kill)(player, nullptr, killer, 0.0f);
	if (limb != -1) ((Dismember_t)kAddr_Dismember)(player, nullptr, -1, limb, killer);
}
static const struct { UInt32 av; SInt32 limb; } kLimbAVs[] = {
	{kAV_PerceptionCond, 1}, {kAV_RightAttackCond, 5}, {kAV_LeftAttackCond, 3}, {kAV_RightMobilityCond, 10},
	{kAV_LeftMobilityCond, 7}, {kAV_EnduranceCond, 1}};
static void ApplyEssential(const char* why) {
	void* player = Player(); if (!player) return;
	Profile* p = PlayerProfile();
	if (!p || !p->ghostEssential) {
		if (g_essentialSet) { SetRefEssential(player, false, why); g_essentialSet = false; }
		g_ghostDown = g_ghostRealDeath = false;
		return;
	}
	UInt32 life = At<UInt32>(player, 0x108);
	if (life == 0) g_ghostRealDeath = false;
	if (life == 1 || life == 2 || g_ghostDown || g_ghostRealDeath) return;     // dead / dying / down: leave it
	SetRefEssential(player, true, why); g_essentialSet = true;
}
static void GhostDowned() {
	void* player = Player(); Profile* p = PlayerProfile();
	if (!player || !p || !p->ghostEssential || g_ghostRealDeath) return;
	g_ghostDown = true;
	if (UInt32 snd = ResolveFID("DeadMoney.esm", 0x012271)) StartSound(snd, PlayerRoot(player), kSoundFlags_3D, nullptr);   // NPCGhostDeath
	Log("ghost: down (health %.1f)", GetAV(player, kAV_Health));
}
static void GhostRevived() {
	Profile* p = PlayerProfile();
	if (!p || !p->ghostEssential) return;
	g_ghostDown = false;
	ApplyEssential("revived");
	Log("ghost: back up");
}
static void GhostCheckLimbs(void* attacker, const char* why) {
	void* player = Player();
	if (!player || g_ghostRealDeath) return;
	Profile* p = PlayerProfile();
	if (!p || !p->ghostEssential) return;
	UInt32 life = At<UInt32>(player, 0x108);
	if (life == 1 || life == 2) return;
	for (const auto& l : kLimbAVs)
		if (GetAV(player, l.av) <= 0.0f) { GhostRealDeath(attacker, l.limb, why); return; }
}
static void GhostOnHit(void* victim, void* attacker) {
	if (victim == Player()) GhostCheckLimbs(attacker, "limb crippled (hit)");
}
// (a grenade crippled a limb without killing; the next grenade killed) The xNVSE OnHit event comes
// before the hit's limb damage, so the crippling hit itself was only seen at the next hit, and fall damage (no hit
// event) never. The player's damage call (PlayerCharacter vtbl 0x3AC = 0x93B7A0, ModActorValue damage (av, delta,
// attacker); only reached through that vtable slot) is where every limb loss lands: hits, explosions and the fall's
// leg damage (0x8A65A4 / 0x8A65DF). After it, a limb condition that dropped to 0 or less clears essential and kills
// with that limb dismembered, at once. Only the player's slot is changed; only limb conditions are looked at.
static const UInt32 kSlot_PlayerModAV = 0x0108AA3C + 0x3AC, kAddr_PlayerModAV = 0x0093B7A0;
typedef void (__fastcall* PlayerModAV_t)(void*, void*, UInt32, float, void*);
static PlayerModAV_t g_origPlayerModAV = nullptr;
static void __fastcall Hook_PlayerModAV(void* actor, void* edx, UInt32 av, float delta, void* attacker) {
	g_origPlayerModAV(actor, edx, av, delta, attacker);
	if (delta >= 0.0f || g_ghostRealDeath || actor != Player()) return;
	bool limb = false; for (const auto& l : kLimbAVs) limb |= l.av == av;
	if (!limb || GetAV(actor, av) > 0.0f) return;
	GhostCheckLimbs(attacker, attacker ? "limb crippled (damage)" : "limb crippled (no attacker: fall / environment)");
}
static void InstallGhostLimbHook() {                                 // at load, when some race has GhostEssential=1
	bool any = false; for (int i = 0; i < g_numProf; i++) any |= g_prof[i].ghostEssential;
	if (!any) return;
	UInt32 cur = *(UInt32*)kSlot_PlayerModAV;
	g_origPlayerModAV = (PlayerModAV_t)cur;
	PatchPtr(kSlot_PlayerModAV, (UInt32)Hook_PlayerModAV, cur, cur == kAddr_PlayerModAV ? "PlayerCharacter damage ModAV (vtbl 0x3AC)" : "PlayerCharacter damage ModAV (chained)");
}
// Actor::IsChild (Character / PlayerCharacter vtbl 0x1A0 = 0x8D40E0, thiscall(bool noHeight), ret 4): the race's Child
// flag (+0x70 & 4), else a body / hand model path containing "child", else (noHeight 0) an actor shorter than 110 units
// for its scale. The short creatures (Tunneler / Spore Carrier and Trogs, 56 tall) were children by that height:
// furniture refused ("Children cannot use that.", 0x5732B7) - the Vault 112 pods of TTW's main quest included - and
// everything else the engine keeps from children. For the player in one of our races only the race's Child flag counts
// (the child races of Tranquility Lane stay children).
static const UInt32 kSlot_PlayerIsChild = 0x0108AA3C + 0x1A0, kAddr_ActorIsChild = 0x008D40E0;
typedef bool (__fastcall* IsChild_t)(void*, void*, UInt8);
static IsChild_t g_origIsChild = (IsChild_t)kAddr_ActorIsChild;
static bool __fastcall Hook_PlayerIsChild(void* actor, void* edx, UInt8 noHeight) {
	if (actor && actor == Player()) {
		void* npc = PlayerNPC(); void* race = npc ? NPCRace(npc) : nullptr;
		if (race && ProfileForRace(race)) return (*(UInt32*)((UInt8*)race + 0x70) & 4) != 0;
	}
	return g_origIsChild(actor, edx, noHeight);
}
static void InstallIsChild() {
	UInt32 cur = *(UInt32*)kSlot_PlayerIsChild;
	g_origIsChild = (IsChild_t)cur;
	PatchPtr(kSlot_PlayerIsChild, (UInt32)Hook_PlayerIsChild, cur, cur == kAddr_ActorIsChild ? "PlayerCharacter IsChild (vtbl 0x1A0)" : "PlayerCharacter IsChild (chained)");
}
static void PEFMessage(NVSEMessage* msg) {
	if (msg->type == 1) { Log("ghost: PlayerEssentialFix -> downed"); GhostDowned(); }
	else if (msg->type == 2) { Log("ghost: PlayerEssentialFix -> revived"); GhostRevived(); }
}

// ---- dialogue voice ----
// Player voice type: TESNPC -> TESActorBaseData (+0x30) -> voiceType (+0x20).
static const UInt32 kOff_NPCVoiceType = 0x50;
static const UInt32 kTopic_Attack = 0xDC, kTopic_Hit = 0xDD, kTopic_Death = 0xEF;    // FalloutNV.esm combat topics
static void* g_origVoice = nullptr; static bool g_voiceSwapped = false;
static const UInt32 kOff_NPCImpactMaterial = 0x1E4;
static UInt32 g_origMaterial = 0; static bool g_materialSwapped = false;
static void ApplyMaterial(const char* why) {
	void* npc = PlayerNPC(); if (!npc) return;
	Profile* p = PlayerProfile();
	UInt32* slot = (UInt32*)((UInt8*)npc + kOff_NPCImpactMaterial);
	if (p && p->impactMaterial >= 0 && p->impactMaterial <= 11) {
		if (*slot == (UInt32)p->impactMaterial) return;
		if (!g_materialSwapped) { g_origMaterial = *slot; g_materialSwapped = true; }
		Log("blood: player impact material %u -> %d (%s)", *slot, p->impactMaterial, why);
		*slot = (UInt32)p->impactMaterial;
	} else if (g_materialSwapped) {
		Log("blood: player impact material restored to %u (%s)", g_origMaterial, why);
		*slot = g_origMaterial; g_materialSwapped = false;
	}
}
// Gore / dismemberment comes from the actor's body part data (BPTD: per limb the
// explodable debris, explosion, impact data set, limb replacement model). An NPC's comes from 0x5F0F80: the player's
// base gets the global PlayerBodyPartData (form 0x1C, pointer 0x11CAFF0), everyone else DefaultBodyPartData (0x1D,
// 0x11CAFEC); both use GoreBits01 + BloodSpoutRedDataSet. While the player is in one of our races that global points at
// the race's BodyPartData= BPTD (Ghost People: NVDLC01GhostBodyPartData, InsectGoreBits01 + BloodSpoutBugDataSet),
// and puts the original back when leaving. Applied with the other race traits, before the race menu's 3D rebuild.
static const UInt32 kPtr_PlayerBodyPartData = 0x011CAFF0;
static void* g_origBodyParts = nullptr; static bool g_bodyPartsSwapped = false;
static void ApplyBodyParts(const char* why) {
	Profile* p = PlayerProfile();
	void** slot = (void**)kPtr_PlayerBodyPartData;
	void* want = (p && p->bodyParts.fid) ? LookupForm(p->bodyParts.fid) : nullptr;
	if (want) {
		if (*slot == want) return;
		if (!g_bodyPartsSwapped) { g_origBodyParts = *slot; g_bodyPartsSwapped = true; }
		Log("gore: player body part data %08X -> %08X (%s)", *slot ? At<UInt32>(*slot, 0x0C) : 0, p->bodyParts.fid, why);
		*slot = want;
	} else if (g_bodyPartsSwapped) {
		Log("gore: player body part data restored to %08X (%s)", g_origBodyParts ? At<UInt32>(g_origBodyParts, 0x0C) : 0, why);
		*slot = g_origBodyParts; g_bodyPartsSwapped = false;
	}
}
// Faces chosen with the race menu's Eyes: FaceEyes= lists eyes forms, FaceNodes= the skeleton nodes they show (the
// n-th eyes form shows the n-th node; the others get the NiAVObject hidden flag, +0x30 bit 0). Eyes not in the list
// leave the skeleton file's default. The player's eyes = TESNPC +0x1C0 (see the NPC save code 0x602150). Applied with
// the other race traits (race menu closed, game load, player 3D set). Node lookup = the engine's by-name search
// 0x4AAE30(root, name). (Securitrons: the 8 vanilla screens as 'PCFace:<name>' nodes under Screen01Root.)
static const UInt32 kAddr_FindNodeByName = 0x004AAE30;
typedef void* (__cdecl* FindByName_t)(void* root, const char* name);
static void ApplyFace(const char* why, void* root = nullptr) {    // root: the new 3D at OnRefSet3D (render state not yet on it)
	void* player = Player(); void* npc = PlayerNPC(); Profile* p = PlayerProfile();
	if (!p || !p->numFaces) return;
	if (!root) root = player ? PlayerRoot(player) : nullptr;
	if (!root || !npc) return;
	void* nodes[16]; int have = 0;
	for (int i = 0; i < p->numFaces; i++) { nodes[i] = ((FindByName_t)kAddr_FindNodeByName)(root, p->faceNodes[i]); have += nodes[i] != nullptr; }
	if (!have) return;
	void* eyes = At<void*>(npc, 0x1C0);
	UInt32 efid = eyes ? At<UInt32>(eyes, 0x0C) : 0;
	int pick = -1;
	for (int i = 0; i < p->numFaces && efid; i++) if (efid == p->faceEyes[i].fid) { pick = i; break; }
	if (pick < 0) { Log("face: eyes %08X are not a face - skeleton default kept (%s)", efid, why); return; }
	for (int i = 0; i < p->numFaces; i++) if (nodes[i]) {
		UInt32& fl = At<UInt32>(nodes[i], 0x30);
		if (i == pick) fl &= ~1u; else fl |= 1u;
	}
	Log("face: %s (%s)", p->faceNodes[pick], why);
}
// UnarmedEffect= / UnarmedEffectAnim=: vanilla creatures carry an unarmed attack effect as CREA EITM + EAMT (the attack
// animation it fires on). An NPC_ base has the same fields (TESEnchantableForm at TESNPC +0x70: item +0x74, EAMT u16
// +0x78; see the NPC_ load code 0x6027BE / 0x6027E8; the player's record has EAMT 0xFF = none). While the player is in
// the race its base gets them; they are put back when leaving it. (Glowing One: GlowingOneAttack 06191A ->
// GlowOneBurstMagicEffect, on AttackBackPower 0x5E - its radiation burst.)
static void* g_origUnarmedItem = nullptr; static UInt16 g_origUnarmedAnim = 0; static bool g_unarmedSwapped = false;
static void ApplyUnarmedEffect(const char* why) {
	void* npc = PlayerNPC(); if (!npc) return;
	Profile* p = PlayerProfile();
	void* item = p && p->unarmedEffect.fid ? LookupForm(p->unarmedEffect.fid) : nullptr;
	UInt16 anim = p ? p->unarmedAnim : 0;
	void*& slot = At<void*>(npc, 0x74); UInt16& aslot = At<UInt16>(npc, 0x78);
	if (item) {
		if (slot == item && aslot == anim) return;
		if (!g_unarmedSwapped) { g_origUnarmedItem = slot; g_origUnarmedAnim = aslot; g_unarmedSwapped = true; }
		Log("unarmed effect: %08X / anim %u -> %08X / anim %u (%s)", slot ? At<UInt32>(slot, 0x0C) : 0, aslot, At<UInt32>(item, 0x0C), anim, why);
		slot = item; aslot = anim;
	} else if (g_unarmedSwapped) {
		Log("unarmed effect restored to %08X / anim %u (%s)", g_origUnarmedItem ? At<UInt32>(g_origUnarmedItem, 0x0C) : 0, g_origUnarmedAnim, why);
		slot = g_origUnarmedItem; aslot = g_origUnarmedAnim; g_unarmedSwapped = false;
	}
}
// The on-hit function 0x8C2190 (thiscall attacker; weapon entry, target, projectile, out) casts the attacker base's
// unarmed effect on the actor hit - only with no weapon (bare fists) - when the playing attack's group (0x5F2420, low
// byte) equals EAMT, read through the getter 0x4A8AE0 at 0x8C2387 (0xFF = any). The unarmed special-move perks (Legion
// Assault / Ranger Takedown / Khan Trick: entry points 0x3D / 0x3E / 0x41 / 0x42) make the player play AttackCustom1 /
// 2 / 4 / 5Power (0x61 / 62 / 64 / 65) in place of AttackForward / Back / Left / RightPower (0x5D-0x60) with bare fists or
// an Unarmed-skill weapon (+0x15C == 0x2D), so an effect set on a directional power attack stopped firing once the perk
// was taken (one EAMT value; no data route). That call is redirected: for the player's base the getter answers the
// playing group when it is EAMT's perk replacement.
// Per race (all off unless the race's settings set them; Ghost People: the gas spray):
//  * UnarmedEffectWeapons=1: with a weapon the on-hit function never considers the unarmed effect. After it ran for the
//    player's hit with an unarmed / melee weapon (DNAM animation type, TESObjectWEAP +0xF4: H2H 0 / 1HM 1 / 2HM 2), it
//    is run once more without weapon and projectile - its bare-fists pass, which casts the unarmed effect alone, through
//    the same EAMT check. Which group a weapon's forward power attack plays (PlayerCharacter 0x949A5D..0x949AD5): with
//    an override (+0x198, WEAP DNAM byte 164) other than 0xFF that group (vanilla melee weapons: AttackCustom1-5Power), so
//    the getter also answers that group for EAMT 0x5D.
//  * UnarmedEffectReachMult=: the hit's target search 0x8990F0 works the reach out inline - a weapon: its reach
//    (0x6447F0) x fCombatDistance (0x6463E0), none: Actor vtbl 0x380 (PlayerCharacter 0x88B850 = fHandReachMult 0.5 x
//    fCombatDistance 128 = 64); x the actor's scale (x the VATS melee mult in VATS) - and passes it to the search
//    0x9A60E0(actor, reach) at 0x8991E2 (GetMeleeReach 0x9A69C0 is the AI's, never on the player's hit). That call is
//    redirected: while the attack stands for the effect's, the reach is at least the unarmed reach x this x scale.
//  * UnarmedEffectCone=: the player's hit cone 0x9A6A40(playing group) at 0x9A6CA5 (forward / standing power 40, back /
//    sides 100, Custom1 50, others 35); while the attack stands for the effect's, at least this.
static const UInt32 kSite_UnarmedAnimGet = 0x008C2387, kAddr_UnarmedAnimGet = 0x004A8AE0;
static const UInt32 kAddr_SeqAnimGroup = 0x0048F7F0, kAddr_AnimGroupId = 0x005F2420, kAddr_EquippedWeapon = 0x008A1710;
static const UInt32 kAddr_HitEnchant = 0x008C2190, kAddr_PlayerUnarmedReach = 0x0088B850;
static const UInt32 kSite_MeleeTargets = 0x008991E2, kAddr_MeleeTargets = 0x009A60E0;
static const UInt32 kAddr_GetScale = 0x00567400, kSite_PlayerHitCone = 0x009A6CA5, kAddr_PlayerHitCone = 0x009A6A40;
typedef UInt16 (__fastcall* AnimGet_t)(void* ench, void* edx);
typedef float (__fastcall* FThis_t)(void*, void*);
static AnimGet_t g_prevUnarmedAnimGet = (AnimGet_t)kAddr_UnarmedAnimGet;
static UInt32 PlayerAttackGroup() {                                  // the engine's own steps at 0x8C23F0..0x8C2414
	void* pl = Player(); if (!pl) return 0xFFFF;
	void* proc = At<void*>(pl, 0x68); if (!proc) return 0xFFFF;
	void* seq = ((P_t)VFn(proc, 0x3E8))(proc, nullptr); if (!seq) return 0xFFFF;
	void* grp = ((P_t)kAddr_SeqAnimGroup)(seq, nullptr); if (!grp) return 0xFFFF;
	return ((U32_t)kAddr_AnimGroupId)(grp, nullptr);
}
static void* PlayerWeapon() { void* pl = Player(); return pl ? ((P_t)kAddr_EquippedWeapon)(pl, nullptr) : nullptr; }
static inline bool MeleeWeapon(void* w) { return w && At<UInt8>(w, 0xF4) <= 2; }        // H2H / 1HM / 2HM
static inline UInt8 PerkGroup(UInt16 a) { static const UInt8 k[4] = {0x61, 0x62, 0x64, 0x65}; return k[a - 0x5D]; }
static inline bool PerkStandIn(UInt16 a, UInt32 g, void* w) {       // the special-move perk's group for direction a
	return a >= 0x5D && a <= 0x60 && g == PerkGroup(a) && (!w || At<UInt32>(w, 0x15C) == 0x2D);
}
static inline bool WeaponForward(UInt16 a, UInt32 g, void* w) {      // a weapon's forward power override for EAMT 0x5D
	return a == 0x5D && w && At<UInt8>(w, 0x198) != 0xFF && g == At<UInt8>(w, 0x198);
}
// the player's profile while its base carries that race's unarmed effect (what ApplyUnarmedEffect gave it)
static Profile* UnarmedProfile() {
	Profile* p = PlayerProfile(); if (!p || !p->unarmedEffect.fid) return nullptr;
	void* npc = PlayerNPC(); void* item = npc ? At<void*>(npc, 0x74) : nullptr;
	return item && At<UInt32>(item, 0x0C) == p->unarmedEffect.fid ? p : nullptr;
}
// that profile, when the playing attack stands for its effect attack with what the player holds
static Profile* EffectAttack(UInt32 g) {
	Profile* p = UnarmedProfile(); if (!p) return nullptr;
	void* w = PlayerWeapon(); if (w && !(p->unarmedWeapons && MeleeWeapon(w))) return nullptr;
	UInt16 a = At<UInt16>(PlayerNPC(), 0x78); if (!a || a == 0xFF) return nullptr;
	if (g == 0xFFFF) g = PlayerAttackGroup();
	return (g == a || WeaponForward(a, g, w) || PerkStandIn(a, g, w)) ? p : nullptr;
}
static UInt16 __fastcall Hook_UnarmedAnimGet(void* ench, void* edx) {
	UInt16 a = g_prevUnarmedAnimGet(ench, edx);
	void* npc = PlayerNPC();
	if (npc && ench == (UInt8*)npc + 0x70 && a >= 0x5D && a <= 0x60) {
		void* w = PlayerWeapon();
		UInt32 g = PlayerAttackGroup();
		if (PerkStandIn(a, g, w)) { Log("unarmed effect: perk attack %02X stands for %02X", g, a); return (UInt16)g; }
		Profile* p = UnarmedProfile();
		if (p && p->unarmedWeapons && g != a && WeaponForward(a, g, w)) { Log("unarmed effect: weapon attack %02X stands for %02X", g, a); return (UInt16)g; }
	}
	return a;
}
typedef bool (__fastcall* HitEnchant_t)(void* attacker, void* edx, void* entry, void* target, void* proj, UInt8* out);
static HitEnchant_t g_hitEnchant = nullptr;
static bool __fastcall Hook_HitEnchant(void* attacker, void* edx, void* entry, void* target, void* proj, UInt8* out) {
	bool r = g_hitEnchant(attacker, edx, entry, target, proj, out);
	if (entry && attacker == Player()) {
		Profile* p = UnarmedProfile();
		if (p && p->unarmedWeapons && MeleeWeapon(PlayerWeapon())) {
			UInt8 o = 0;
			if (g_hitEnchant(attacker, edx, nullptr, target, nullptr, &o)) r = true;   // its bare-fists pass
			if (o && out) *out = 1;
		}
	}
	return r;
}
typedef void* (__cdecl* MeleeTargets_t)(void* actor, float reach);
static MeleeTargets_t g_prevMeleeTargets = (MeleeTargets_t)kAddr_MeleeTargets;
static void* __cdecl Hook_MeleeTargets(void* actor, float reach) {
	if (actor == Player()) {
		Profile* p = EffectAttack(0xFFFF);
		if (p && p->unarmedReachMult > 0) {
			float min = ((FThis_t)kAddr_PlayerUnarmedReach)(actor, nullptr) * p->unarmedReachMult * ((FThis_t)kAddr_GetScale)(actor, nullptr);
			if (min > reach) reach = min;
		}
	}
	return g_prevMeleeTargets(actor, reach);
}
typedef float (__cdecl* Cone_t)(UInt32 group);
static Cone_t g_prevCone = (Cone_t)kAddr_PlayerHitCone;
static float __cdecl Hook_PlayerHitCone(UInt32 group) {
	float c = g_prevCone(group);
	Profile* p = EffectAttack(group & 0xFF);
	return (p && p->unarmedCone > c) ? p->unarmedCone : c;
}
static void InstallUnarmedPerkAnims() {                              // at load, only for what some race's settings use
	bool dir = false, weap = false, reach = false, cone = false;
	for (int i = 0; i < g_numProf; i++) {
		const Profile& p = g_prof[i]; if (!p.unarmedEffect.localID) continue;
		dir |= p.unarmedAnim >= 0x5D && p.unarmedAnim <= 0x60;
		weap |= p.unarmedWeapons; reach |= p.unarmedReachMult > 0; cone |= p.unarmedCone > 0;
	}
	UInt32 prev;
	if (!dir && !weap) Log("unarmed effect: no race's effect is on a directional power attack or weapons - getter not hooked");
	else if (RedirectCall(kSite_UnarmedAnimGet, (void*)Hook_UnarmedAnimGet, kAddr_UnarmedAnimGet, &prev, "unarmed effect anim (perk moves / weapons)"))
		g_prevUnarmedAnimGet = (AnimGet_t)prev;
	if (weap) g_hitEnchant = (HitEnchant_t)Detour(kAddr_HitEnchant, 0x64, (void*)Hook_HitEnchant, "on-hit enchantments (UnarmedEffectWeapons)");
	if (reach && RedirectCall(kSite_MeleeTargets, (void*)Hook_MeleeTargets, kAddr_MeleeTargets, &prev, "melee hit reach (UnarmedEffectReachMult)"))
		g_prevMeleeTargets = (MeleeTargets_t)prev;
	if (cone && RedirectCall(kSite_PlayerHitCone, (void*)Hook_PlayerHitCone, kAddr_PlayerHitCone, &prev, "player hit cone (UnarmedEffectCone)"))
		g_prevCone = (Cone_t)prev;
	if (!weap && !reach && !cone) Log("unarmed effect: no race sets UnarmedEffectWeapons / ReachMult / Cone - those not hooked");
}
static void ApplyEssential(const char* why);
static void ApplyFaction(const char* why);
static void ApplyVoice(const char* why) {
	ApplyUnarmedEffect(why);
	ApplyMaterial(why);
	ApplyBodyParts(why);
	ApplyFace(why);
	ApplyMaxResist(why);
	ApplyEssential(why);
	ApplyFaction(why);
	void* npc = PlayerNPC(); if (!npc) return;
	Profile* p = PlayerProfile();
	void** slot = (void**)((UInt8*)npc + kOff_NPCVoiceType);
	void* want = (p && p->voiceType.fid) ? LookupForm(p->voiceType.fid) : nullptr;
	if (want) {
		if (*slot == want) return;
		if (!g_voiceSwapped) { g_origVoice = *slot; g_voiceSwapped = true; }
		Log("voice: player voice type %08X -> %08X (%s)", *slot ? *(UInt32*)((UInt8*)*slot + 0x0C) : 0, *(UInt32*)((UInt8*)want + 0x0C), why);
		*slot = want;
	} else if (g_voiceSwapped) {
		Log("voice: player voice type restored to %08X (%s)", g_origVoice ? *(UInt32*)((UInt8*)g_origVoice + 0x0C) : 0, why);
		*slot = g_origVoice; g_voiceSwapped = false; g_origVoice = nullptr;
	}
}
// The Say *command* (via an xNVSE UDF) compiles and returns success, but for high-process actors
// (the player) the command only queues the line on the AI process (Say handler 0x5C8A50: Actor::GetProcessLevel
// 0x931850 == 0 -> vtable 0x674/0x648/0x628 queue), which the player never runs -> silence.
// So Actor::Say is called directly (vtable +0x408 = 0x8A1BD0, thiscall, ret 0x1C):
//   (BSSoundHandle* out, TESTopic* topic, TESObjectREFR* target, bool, bool, 0, 0)
// It evaluates TESTopic::GetInfo (0x61B320) for the speaker, builds the voice file path, and plays it (0xAD8830).
typedef void (__fastcall* ActorSay_t)(void* actor, void* edx, SoundHandle* out, void* topic, void* target, UInt32 b1, UInt32 b2, UInt32 a6, UInt32 a7);
static bool SayTopic(UInt32 topicLocal, const char* what) {
	void* player = Player();
	if (!player) return false;
	void* topic = LookupForm(ResolveFID("FalloutNV.esm", topicLocal));
	if (!topic || *((UInt8*)topic + 4) != kFormType_DIAL) { Log("voice: topic %06X not found", topicLocal); return false; }
	SoundHandle snd; snd.key = 0xFFFFFFFF; snd.ok = 0; snd.unk8 = 0;
	ActorSay_t fn = (ActorSay_t)((*(UInt32**)player)[0x408 / 4]);
	fn(player, nullptr, &snd, topic, player, 0, 0, 0, 0);
	Log("voice: Say %s -> sound %s", what, snd.key != 0xFFFFFFFF ? "playing" : "none (no INFO / voice file)");
	return snd.key != 0xFFFFFFFF;
}

static void OnHitHandler(void* thisObj, void* parameters) {
	void** a = (void**)parameters;
	void* victim = a[0]; void* attacker = a[1];
	void* player = Player();
	if (!player || (victim != player && attacker != player)) return;
	GhostOnHit(victim, attacker);
	Profile* p = PlayerProfile();
	if (!p || !p->voiceType.fid) return;
	if (victim == player) {                                              // pain: 60 %, at most every 1.5 s
		if (PlayerDead(player) || !Gate(60, 1500, &p->lastHit)) return;
		SayTopic(kTopic_Hit, "Hit");
		return;
	}
	// the player hit something: ranged weapons only (melee / throws are voiced by their animations' text keys)
	UInt8* proc = *(UInt8**)((UInt8*)player + 0x68);                     // BaseProcess; weapon info valid for levels 0/1
	if (!proc || proc[0x28] > 1) return;
	UInt8* info = *(UInt8**)(proc + 0x114);                             // ContChangesEntry* (equipped weapon)
	UInt8* weap = info ? *(UInt8**)(info + 8) : nullptr;
	if (!weap || weap[4] != kFormType_WEAP) return;
	UInt8 wt = weap[0xF4];
	if (wt < 3 || wt > 9) return;                                       // 1HP..2HL
	if (!Gate(25, 6000, &p->lastRanged)) return;                       // bark: 25 %, at most every 6 s
	SayTopic(kTopic_Attack, "Attack");
}
static void OnDeathHandler(void* thisObj, void* parameters) {
	void** a = (void**)parameters;
	void* player = Player();
	if (!player || a[0] != player) return;
	StopLoop("player died");
	g_ghostDown = false; g_ghostRealDeath = true;
	g_playerDied = true;                                           // rebuild the 3D at the next load
	Profile* p = PlayerProfile();
	if (p && p->voiceType.fid) SayTopic(kTopic_Death, "Death");
}
static NVSEEventManagerInterface* g_events = nullptr;
static NVSEMessagingInterface* g_msgIF = nullptr;
static UInt32 g_handle = 0;
// OnHit: voices + Ghost People's semi-dead rules; OnDeath: voice, loop stop, 3D rebuild on the next load
static void InstallEventHandlers() {
	if (!g_events) { Log("events: xNVSE event manager unavailable - hit / death voices and ghost rules disabled"); return; }
	bool h = g_events->SetNativeEventHandler("OnHit", OnHitHandler);
	bool d = g_events->SetNativeEventHandler("OnDeath", OnDeathHandler);
	Log("events: native handlers OnHit=%d OnDeath=%d", h, d);
}

static void MessageHandler(NVSEMessage* msg) {
	switch (msg->type) {
	case kMessage_PostLoad:
		if (g_msgIF) Log("ghost: PlayerEssentialFix listener %s", g_msgIF->RegisterListener(g_handle, "PlayerEssentialFix", PEFMessage) ? "registered" : "NOT registered");
		break;
	case kMessage_PostPostLoad: InstallAnimLookupGuards(); InstallAnimPlayGuards(); break;
	case kMessage_DeferredInit: {
		ResolveProfiles(); InstallEventHandlers(); ResolveCloudScripts();
		if (GetModuleHandleA("PlayerEssentialFix.dll")) Log("deps: PlayerEssentialFix loaded");
		else for (int i = 0; i < g_numProf; i++) if (g_prof[i].ghostEssential) { Log("deps: PlayerEssentialFix.dll NOT loaded - an essential player stays ragdolled after the revive"); break; }
		break; }
	case kMessage_PostLoadGame:
		EnforceEquipment("game loaded");
		SyncPlayerSkeleton("game loaded");
		UpdateLoop("game loaded");
		ApplyVoice("game loaded");                                      // no-op if OnRefSet3D already started it during the load
		break;
	case kMessage_PreLoadGame: case kMessage_ExitToMainMenu: case kMessage_NewGame:
		// the player is dying (life 1) or dead (2) as the next save loads: the load must rebuild the 3D. The
		// xNVSE OnDeath event only comes at the end of the dying animation, so a quick reload after a death missed it.
		if (msg->type == kMessage_PreLoadGame && Player()) {
			UInt32 life = At<UInt32>(Player(), 0x108);
			if (life == 1 || life == 2) { g_playerDied = true; Log("load: the player is %s - the 3D is rebuilt after the load", life == 1 ? "dying" : "dead"); }
		}
		StopLoop("leaving the game");
		g_ghostDown = g_ghostRealDeath = false; g_essentialSet = false; // the flag isn't saved
		g_numJoined = 0;       // faction membership is saved; the race check on the next 3D set / load decides again
		break;
	case kMessage_OnRefSet3D:
		if (msg->data && ((void**)msg->data)[0] == Player() && Player()) {
			void* node = ((void**)msg->data)[1];
			const char* m = RootMarker(node);
			Log("player 3D set: root=%p marker='%s'", node, m ? m : "");
			ResetPlayerHeight("player 3D set");
			UpdateLoop("player 3D set", node);
			ApplyVoice("player 3D set");
			ApplyFace("player 3D set (new root)", node);
		}
		break;
	default: break;
	}
}

extern "C" {
__declspec(dllexport) bool NVSEPlugin_Query(const NVSEInterface* nvse, PluginInfo* info) {
	info->infoVersion = 1; info->name = "PlayableCreatures"; info->version = kPluginVersion;
	return !nvse->isEditor && nvse->runtimeVersion == kRuntime_1_4_0_525;
}
__declspec(dllexport) bool NVSEPlugin_Load(const NVSEInterface* nvse) {
	GetModuleFileNameA(nullptr, g_gameDir, MAX_PATH);
	if (char* s = strrchr(g_gameDir, '\\')) s[1] = 0;
	char lp[MAX_PATH]; snprintf(lp, sizeof(lp), "%sPlayableCreatures.log", g_gameDir);
	g_log = fopen(lp, "w");
	Log("Playable Creatures v%u; nvse %08X runtime %08X", kPluginVersion, nvse->nvseVersion, nvse->runtimeVersion);
	LoadConfig();
	g_handle = nvse->GetPluginHandle();
	g_msgIF = (NVSEMessagingInterface*)nvse->QueryInterface(kInterface_Messaging);
	g_console = (NVSEConsoleInterface*)nvse->QueryInterface(kInterface_Console);
	Log("console interface %s (v%u)", g_console ? "ok" : "missing", g_console ? g_console->version : 0);
	if (g_msgIF) g_msgIF->RegisterListener(g_handle, "NVSE", MessageHandler);
	g_events = (NVSEEventManagerInterface*)nvse->QueryInterface(kInterface_EventManager);
	InstallCloudHook();
	InstallGhostMoves();
	InstallCameraPivot(); InstallFirstPersonBody();
	InstallFallDamage();
	InstallGhostLimbHook();
	InstallIsChild();
	InstallRagdollGuard();
	InstallUnarmedPerkAnims();

	PatchPtr(kVtbl_TESNPC_TESModel + 5 * 4, (UInt32)Hook_NPCGetModelPath, kAddr_TESNPC_GetModelPath, "TESNPC::GetModelPath");
	{   // chain: another plugin (UI mods) may already own this slot
		UInt32 cur = *(UInt32*)kVtbl_RaceSexMenu;
		g_prevMenuDtor = (MenuDtor_t)cur;
		PatchPtr(kVtbl_RaceSexMenu, (UInt32)Hook_RaceSexMenuDtor, cur, cur == kAddr_RaceSexMenu_Dtor ? "RaceSexMenu::~RaceSexMenu" : "RaceSexMenu::~RaceSexMenu (chained to another plugin)");
	}
	{ bool locks = false; for (int i = 0; i < g_numProf; i++) locks |= g_prof[i].numLocked > 0;
	  if (locks) g_equipTramp = (EquipItem_t)DetourPadded(kAddr_EquipItem, 0x08, (void*)Hook_EquipItem, "Actor::EquipItem");
	  else Log("equip: no race has LockedItems - Actor::EquipItem not hooked"); }
	g_addBipedTramp = (AddItemToBiped_t)Detour(kAddr_AddItemToBiped, 0x1C, (void*)Hook_AddItemToBiped, "TESNPC::AddItemToBiped");
	return true;
}
}
BOOL WINAPI DllMain(HINSTANCE, DWORD, LPVOID) { return TRUE; }
