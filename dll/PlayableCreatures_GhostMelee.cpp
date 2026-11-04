// PlayableCreatures_GhostMelee — xNVSE plugin (FNV 1.4.0.525), shipped with the Ghost People pack (and the merged
// packs). Hook driven only (no per-frame code). Needs PlayableCreatures.dll (Core), which gives the player's base the
// race's unarmed attack effect (TESNPC +0x74 item / +0x78 EAMT, ini UnarmedEffect= / UnarmedEffectAnim=) while the
// player is in that race; this plugin only widens when that effect lands. It reads the same settings files
// (Data\NVSE\Plugins\PlayableCreatures\*.ini): a section with UnarmedEffect= and any of the keys below takes part, and is
// active while the player's base carries that section's effect (so nothing here acts for any other race).
//   UnarmedEffectWeapons=1   the effect also on hits with an unarmed or melee weapon (Ghost People: the gas spray)
//   UnarmedEffectReachMult=  that attack's melee reach is at least the unarmed reach x this
//   UnarmedEffectCone=       that attack's hit cone is at least this (degrees either side of the facing)
//
// Engine (verified in the exe):
//  * The on-hit function 0x8C2190 (thiscall attacker; weapon entry, target, projectile, out*) casts, each independently
//    from the attacker's MagicCaster (+0x88) on the actor hit: the attacker base's unarmed effect - only when the weapon
//    entry is null, and only if the playing attack's group (0x5F2420, low byte) equals EAMT (getter 0x4A8AE0 at 0x8C2387;
//    0xFF = any) - then the weapon's enchantment, its poison and the ammo's effect. With a weapon the unarmed effect is
//    never considered. Weapons: after the function ran for the player's hit with an unarmed / melee weapon (DNAM
//    animation type, TESObjectWEAP +0xF4: H2H 0 / 1HM 1 / 2HM 2), it is run once more without weapon and projectile -
//    its bare-fists pass, which casts the unarmed effect alone, through the same EAMT check.
//  * Which group a forward power attack plays (PlayerCharacter 0x949A5D..0x949AD5): with a weapon whose override
//    (+0x198, WEAP DNAM byte 164) isn't 0xFF, that group (vanilla melee weapons: AttackCustom1-5Power); bare fists or an
//    Unarmed-skill weapon (+0x15C == 0x2D): the special-move perks' AttackCustom1 / 2 / 4 / 5Power for Forward / Back /
//    Left / Right (Core answers those). Here: a weapon's forward override stands for EAMT 0x5D (the EAMT getter call,
//    chained after / before Core's).
//  * Reach: GetMeleeReach 0x9A69C0(actor, weapon) - no weapon: Actor vtbl 0x380 (PlayerCharacter 0x88B850 =
//    fHandReachMult 0.5 x fCombatDistance 128 = 64), a weapon: its reach x fCombatDistance; x the actor's scale. Hit
//    cone: for the player 0x9A6A40(playing group) at 0x9A6CA5 (forward / standing power 40, back / sides 100, Custom1 50,
//    others 35). Both GMST driven for everyone; answered here only while the attack stands for the active section's.
#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <stdarg.h>

typedef uint32_t UInt32; typedef uint8_t UInt8; typedef uint16_t UInt16; typedef int32_t SInt32;

struct PluginInfo { UInt32 infoVersion; const char* name; UInt32 version; };
struct NVSEInterface {
	UInt32 nvseVersion, runtimeVersion, editorVersion, isEditor;
	void* RegisterCommand; void* SetOpcodeBase; void* (*QueryInterface)(UInt32 id); UInt32 (*GetPluginHandle)(void);
};
static const UInt32 kRuntime_1_4_0_525 = 0x040020D0;
static const UInt32 kVersion = 1;

static const UInt32 kPtr_DataHandler = 0x011C3F2C, kPtr_Player = 0x011DEA3C;
static const UInt32 kSite_UnarmedAnimGet = 0x008C2387, kAddr_UnarmedAnimGet = 0x004A8AE0, kAddr_HitEnchant = 0x008C2190;
static const UInt32 kAddr_SeqAnimGroup = 0x0048F7F0, kAddr_AnimGroupId = 0x005F2420, kAddr_GetScale = 0x00567400;
static const UInt32 kAddr_PlayerUnarmedReach = 0x0088B850, kAddr_MeleeReach = 0x009A69C0;
static const UInt32 kSite_PlayerHitCone = 0x009A6CA5, kAddr_PlayerHitCone = 0x009A6A40, kAddr_EquippedWeapon = 0x008A1710;

static FILE* g_log = nullptr;
static void Log(const char* fmt, ...) {
	if (!g_log) return;
	va_list a; va_start(a, fmt); vfprintf(g_log, fmt, a); va_end(a); fputc('\n', g_log); fflush(g_log);
}
template <typename T> static inline T& At(void* p, UInt32 off) { return *(T*)((UInt8*)p + off); }
static inline void* VFn(void* obj, UInt32 off) { return (*(void***)obj)[off / 4]; }
typedef void* (__fastcall* P_t)(void*, void*);
typedef UInt32 (__fastcall* U32_t)(void*, void*);
typedef float (__fastcall* F_t)(void*, void*);
static inline void* Player() { return *(void**)kPtr_Player; }
static inline void* PlayerNPC() { void* p = Player(); return p ? At<void*>(p, 0x20) : nullptr; }

// ---------------- settings ----------------
struct Section { char name[64], plugin[128]; UInt32 local, fid; bool weapons; float reachMult, cone; };
static Section g_sec[32]; static int g_numSec = 0; static bool g_resolved = false;
static void LoadFile(const char* ini) {
	char names[8192], tmp[256];
	if (!GetPrivateProfileSectionNamesA(names, sizeof(names), ini)) return;
	for (char* sec = names; *sec && g_numSec < 32; sec += strlen(sec) + 1) {
		GetPrivateProfileStringA(sec, "UnarmedEffect", "", tmp, sizeof(tmp), ini);
		char* bar = strchr(tmp, '|'); if (!bar) continue;
		Section s = {}; *bar = 0;
		snprintf(s.name, sizeof(s.name), "%s", sec); snprintf(s.plugin, sizeof(s.plugin), "%s", tmp); s.local = strtoul(bar + 1, nullptr, 16) & 0xFFFFFF;
		s.weapons = GetPrivateProfileIntA(sec, "UnarmedEffectWeapons", 0, ini) != 0;
		GetPrivateProfileStringA(sec, "UnarmedEffectReachMult", "0", tmp, sizeof(tmp), ini); s.reachMult = (float)atof(tmp);
		GetPrivateProfileStringA(sec, "UnarmedEffectCone", "0", tmp, sizeof(tmp), ini); s.cone = (float)atof(tmp);
		if (!s.weapons && s.reachMult <= 0 && s.cone <= 0) continue;
		g_sec[g_numSec++] = s;
		Log("config: [%s] %s|%06X weapons %d, reach x%.2f, cone %.0f", s.name, s.plugin, s.local, s.weapons, s.reachMult, s.cone);
	}
}
static void LoadConfig() {
	char dir[MAX_PATH], pat[MAX_PATH], path[MAX_PATH];
	GetModuleFileNameA(nullptr, dir, MAX_PATH); char* sl = strrchr(dir, '\\'); if (sl) sl[1] = 0;
	strncat(dir, "Data\\NVSE\\Plugins\\PlayableCreatures\\", MAX_PATH - strlen(dir) - 1);
	snprintf(pat, sizeof(pat), "%s*.ini", dir);
	WIN32_FIND_DATAA fd; HANDLE h = FindFirstFileA(pat, &fd);
	if (h == INVALID_HANDLE_VALUE) return;
	do {
		if (fd.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) continue;
		snprintf(path, sizeof(path), "%s%s", dir, fd.cFileName); LoadFile(path);
	} while (FindNextFileA(h, &fd));
	FindClose(h);
}
// a plugin's load index: the DataHandler's file list (+0x210), TESFile name +0x20, index +0x40C (as Core reads it)
static bool Readable(const void* p, UInt32 n) {
	if ((UInt32)p < 0x10000) return false;
	MEMORY_BASIC_INFORMATION mbi;
	if (!VirtualQuery(p, &mbi, sizeof(mbi)) || mbi.State != MEM_COMMIT || (mbi.Protect & (PAGE_NOACCESS | PAGE_GUARD))) return false;
	UInt32 end = (UInt32)mbi.BaseAddress + mbi.RegionSize;
	return (UInt32)p + n <= end || Readable((const void*)end, (UInt32)p + n - end);
}
static UInt8 ModIndex(const char* name) {
	UInt8* dh = *(UInt8**)kPtr_DataHandler; if (!dh) return 0xFF;
	struct Node { UInt8* data; Node* next; };
	int n = 0;
	for (Node* it = (Node*)(dh + 0x210); it && n < 4096; it = it->next, n++) {
		if (!Readable(it, sizeof(Node))) break;
		UInt8* m = it->data;
		if (!m || !Readable(m, 0x410) || !memchr(m + 0x20, 0, MAX_PATH)) continue;
		if (!_stricmp((const char*)(m + 0x20), name)) return m[0x40C];
	}
	return 0xFF;
}
static const Section* Active() {                                     // the section whose effect the player's base carries
	void* npc = PlayerNPC(); if (!npc) return nullptr;
	void* item = At<void*>(npc, 0x74); if (!item) return nullptr;
	if (!g_resolved) {
		g_resolved = true;
		for (int i = 0; i < g_numSec; i++) {
			UInt8 idx = ModIndex(g_sec[i].plugin); g_sec[i].fid = idx == 0xFF ? 0 : ((UInt32)idx << 24) | g_sec[i].local;
			Log("resolve: [%s] effect %08X%s", g_sec[i].name, g_sec[i].fid, g_sec[i].fid ? "" : "  (plugin not loaded)");
		}
	}
	UInt32 fid = At<UInt32>(item, 0x0C);
	for (int i = 0; i < g_numSec; i++) if (g_sec[i].fid && g_sec[i].fid == fid) return &g_sec[i];
	return nullptr;
}

// ---------------- the attack ----------------
static UInt32 PlayerAttackGroup() {                                  // the engine's own steps at 0x8C23F0..0x8C2414
	void* pl = Player(); if (!pl) return 0xFFFF;
	void* proc = At<void*>(pl, 0x68); if (!proc) return 0xFFFF;
	void* seq = ((P_t)VFn(proc, 0x3E8))(proc, nullptr); if (!seq) return 0xFFFF;
	void* grp = ((P_t)kAddr_SeqAnimGroup)(seq, nullptr); if (!grp) return 0xFFFF;
	return ((U32_t)kAddr_AnimGroupId)(grp, nullptr);
}
static void* PlayerWeapon() { void* pl = Player(); return pl ? ((P_t)kAddr_EquippedWeapon)(pl, nullptr) : nullptr; }
static inline bool MeleeWeapon(void* w) { return w && At<UInt8>(w, 0xF4) <= 2; }        // H2H / 1HM / 2HM
static inline bool WeaponForward(UInt16 a, UInt32 g, void* w) {      // a weapon's forward power override for EAMT 0x5D
	return a == 0x5D && w && At<UInt8>(w, 0x198) != 0xFF && g == At<UInt8>(w, 0x198);
}
static bool StandsFor(UInt16 a, UInt32 g, void* w) {
	if (g == a || WeaponForward(a, g, w)) return true;
	static const UInt8 kPerkGroup[4] = {0x61, 0x62, 0x64, 0x65};
	return a >= 0x5D && a <= 0x60 && (!w || At<UInt32>(w, 0x15C) == 0x2D) && g == kPerkGroup[a - 0x5D];
}
// the active section, when the playing attack stands for its effect attack with what the player holds
static const Section* EffectAttack(UInt32 g) {
	const Section* s = Active(); if (!s) return nullptr;
	void* w = PlayerWeapon(); if (w && !(s->weapons && MeleeWeapon(w))) return nullptr;
	UInt16 a = At<UInt16>(PlayerNPC(), 0x78); if (!a || a == 0xFF) return nullptr;
	if (g == 0xFFFF) g = PlayerAttackGroup();
	return StandsFor(a, g, w) ? s : nullptr;
}

// ---------------- hooks ----------------
static bool RedirectCall(UInt32 site, void* hook, UInt32 vanilla, UInt32* prevOut, const char* what) {
	UInt8* p = (UInt8*)site;
	if (p[0] != 0xE8) { Log("patch: %s @%08X not a call (%02X) - NOT patched", what, site, p[0]); return false; }
	UInt32 prev = site + 5 + *(SInt32*)(p + 1); *prevOut = prev;
	DWORD old; VirtualProtect(p, 5, PAGE_EXECUTE_READWRITE, &old);
	*(SInt32*)(p + 1) = (SInt32)((UInt32)hook - (site + 5)); VirtualProtect(p, 5, old, &old);
	Log("patch: %s @%08X -> hook (was %08X%s)", what, site, prev, prev == vanilla ? ", vanilla" : ", another plugin - chained");
	return true;
}
static void* Detour(UInt32 addr, UInt8 frameSize, void* hook, const char* what) {
	UInt8* fn = (UInt8*)addr;
	const UInt8 vanilla[6] = {0x55, 0x8B, 0xEC, 0x83, 0xEC, frameSize};
	UInt8* tramp = (UInt8*)VirtualAlloc(nullptr, 32, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE);
	if (!tramp) return nullptr;
	bool isVanilla = !memcmp(fn, vanilla, 6);
	if (isVanilla) {
		memcpy(tramp, vanilla, 6); tramp[6] = 0xE9; *(SInt32*)(tramp + 7) = (SInt32)((UInt32)fn + 6 - ((UInt32)tramp + 11));
	} else if (fn[0] == 0xE9) {
		UInt32 target = (UInt32)fn + 5 + *(SInt32*)(fn + 1);
		tramp[0] = 0xE9; *(SInt32*)(tramp + 1) = (SInt32)(target - ((UInt32)tramp + 5));
		Log("patch: %s entry already detoured by another plugin -> chaining to %08X", what, target);
	} else {
		Log("patch: %s entry bytes unexpected (%02X %02X %02X %02X) -> NOT hooked", what, fn[0], fn[1], fn[2], fn[3]);
		VirtualFree(tramp, 0, MEM_RELEASE); return nullptr;
	}
	DWORD old; VirtualProtect(fn, 6, PAGE_EXECUTE_READWRITE, &old);
	fn[0] = 0xE9; *(SInt32*)(fn + 1) = (SInt32)((UInt32)hook - ((UInt32)fn + 5));
	if (isVanilla) fn[5] = 0x90;
	VirtualProtect(fn, 6, old, &old); FlushInstructionCache(GetCurrentProcess(), fn, 6);
	Log("patch: %s detour installed (trampoline %p)", what, tramp);
	return tramp;
}

typedef UInt16 (__fastcall* AnimGet_t)(void* ench, void* edx);
static AnimGet_t g_prevAnimGet = (AnimGet_t)kAddr_UnarmedAnimGet;
static UInt16 __fastcall Hook_AnimGet(void* ench, void* edx) {       // a weapon's forward power stands for 0x5D
	UInt16 a = g_prevAnimGet(ench, edx);
	void* npc = PlayerNPC();
	if (npc && ench == (UInt8*)npc + 0x70 && a == 0x5D && Active()) {
		UInt32 g = PlayerAttackGroup();
		if (g != a && WeaponForward(a, g, PlayerWeapon())) { Log("unarmed effect: weapon attack %02X stands for %02X", g, a); return (UInt16)g; }
	}
	return a;
}
typedef bool (__fastcall* HitEnchant_t)(void* attacker, void* edx, void* entry, void* target, void* proj, UInt8* out);
static HitEnchant_t g_hitEnchant = nullptr;
static bool __fastcall Hook_HitEnchant(void* attacker, void* edx, void* entry, void* target, void* proj, UInt8* out) {
	bool r = g_hitEnchant(attacker, edx, entry, target, proj, out);
	if (entry && attacker == Player()) {
		const Section* s = Active();
		if (s && s->weapons && MeleeWeapon(PlayerWeapon())) {
			UInt8 o = 0;
			if (g_hitEnchant(attacker, edx, nullptr, target, nullptr, &o)) r = true;   // its bare-fists pass
			if (o && out) *out = 1;
		}
	}
	return r;
}
typedef float (__cdecl* MeleeReach_t)(void* actor, void* weapon);
static MeleeReach_t g_meleeReach = nullptr;
static float __cdecl Hook_MeleeReach(void* actor, void* weapon) {
	float r = g_meleeReach(actor, weapon);
	if (actor == Player()) {
		const Section* s = EffectAttack(0xFFFF);
		if (s && s->reachMult > 0) {
			float gas = ((F_t)kAddr_PlayerUnarmedReach)(actor, nullptr) * s->reachMult * ((F_t)kAddr_GetScale)(actor, nullptr);
			if (gas > r) return gas;
		}
	}
	return r;
}
typedef float (__cdecl* Cone_t)(UInt32 group);
static Cone_t g_prevCone = (Cone_t)kAddr_PlayerHitCone;
static float __cdecl Hook_PlayerHitCone(UInt32 group) {
	float c = g_prevCone(group);
	const Section* s = EffectAttack(group & 0xFF);
	return (s && s->cone > c) ? s->cone : c;
}

extern "C" {
__declspec(dllexport) bool NVSEPlugin_Query(const NVSEInterface* nvse, PluginInfo* info) {
	info->infoVersion = 1; info->name = "PlayableCreatures_GhostMelee"; info->version = kVersion;
	return !nvse->isEditor && nvse->runtimeVersion == kRuntime_1_4_0_525;
}
__declspec(dllexport) bool NVSEPlugin_Load(const NVSEInterface* nvse) {
	g_log = fopen("PlayableCreatures_GhostMelee.log", "w");
	Log("PlayableCreatures_GhostMelee v%u", kVersion);
	LoadConfig();
	bool weap = false, reach = false, cone = false;
	for (int i = 0; i < g_numSec; i++) { weap |= g_sec[i].weapons; reach |= g_sec[i].reachMult > 0; cone |= g_sec[i].cone > 0; }
	if (!g_numSec) { Log("config: no section sets UnarmedEffectWeapons / ReachMult / Cone - nothing hooked"); return true; }
	UInt32 prev;
	if (weap) {
		if (RedirectCall(kSite_UnarmedAnimGet, (void*)Hook_AnimGet, kAddr_UnarmedAnimGet, &prev, "unarmed effect anim (weapon forward power)"))
			g_prevAnimGet = (AnimGet_t)prev;
		g_hitEnchant = (HitEnchant_t)Detour(kAddr_HitEnchant, 0x64, (void*)Hook_HitEnchant, "on-hit enchantments");
	}
	if (reach) g_meleeReach = (MeleeReach_t)Detour(kAddr_MeleeReach, 0x10, (void*)Hook_MeleeReach, "melee reach");
	if (cone && RedirectCall(kSite_PlayerHitCone, (void*)Hook_PlayerHitCone, kAddr_PlayerHitCone, &prev, "player hit cone"))
		g_prevCone = (Cone_t)prev;
	return true;
}
}
BOOL WINAPI DllMain(HINSTANCE, DWORD, LPVOID) { return TRUE; }
