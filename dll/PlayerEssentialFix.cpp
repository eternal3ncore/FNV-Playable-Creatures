// PlayerEssentialFix — xNVSE plugin (FNV 1.4.0.525). Event/hook driven only (no per-frame code).
//
// Vanilla bug: an essential player who goes down regains health when the essential timer runs out
// (Actor::Update: SetLifeState(0) + 0x8A0960 restore), but stays ragdolled.
//
// Fixes:
//   1. Revive: on the player's engine revive (SetLifeState 6 -> 0, then the restore call 0x8A0960 that follows it),
//      reset the hit data (a stale hit location blocks the KnockedDownIdles get-up tree: GetHitLocation == -1); if the
//      player is knocked (knock state 1 or 3), do the engine's own get-up step now (as ProcessKnockedState 0x920150
//      case 1/3: FindIdle -> QueueSpecialIdle 0x14, release ragdoll, knock = 5), or, when no get-up idle exists, the
//      engine's no-animation stand-up (process vtbl 0x420).
//   2. Knock-over: the engine never knocks the player over when it goes essential-down. Actor::Kill's essential branch
//      (0x89E057: SetLifeState 6, ragdoll start 0x8A5EB0, restore 0x8A0960) leaves the player's knock state at 0, so
//      the player stays upright / slides with no animation, and the revive in Actor::Update (0x889065: life state 6 AND
//      knock state 1 or 3, then the essential timer) never fires. In the restore that follows the ragdoll start: if the
//      player is still not knocked, push it over the way the PushActorAway command does (process vtbl 0x418: actor,
//      source point, force from 0x646580). Knock 1 -> ragdoll -> 3, the timer runs, the engine revives, and the
//      get-up follows.
//   3. Knocked-state processing: the player's update never runs the knocked-state machine (HighProcess vtbl 0x41C,
//      ProcessKnockedState 0x920150; NPCs get it from Actor vtbl 0x268 0x888070, the player only in one special branch
//      at 0x9426C5). So a knocked-down player stays ragdolled forever: knock 2 never settles to 1, the revive (needs
//      knock 1 or 3) never fires, and a queued get-up never plays. While - and only while - the player is down, PEF
//      patches the player's per-frame Character update calls (all four branches, see kSites_PlayerCharUpdate) to run
//      that same engine step after it, as NPCs do. The patch is put back as soon as the player is up again (knock 0,
//      alive) or dead; nothing runs outside a knockdown.
//   4. Weapon ready state: after the get-up the player's weapon is still "out" but attacks do nothing until it is
//      holstered and drawn again (the ready state isn't rebuilt for the player). A drawn weapon is put away when the
//      player goes down (Actor::SetWeaponOut 0x8A6840(false), the ready-key's own call) and drawn again once the player
//      is back up (0x8A6840(true)), so the equip runs and the weapon is ready.
//   5. Death camera: after an essential down from a fall the engine's player-death VATS camera starts (slow motion,
//      camera swinging around the player, no menus). PlayerCharacter::Update's normal branch, at 0x9438A7, starts it
//      (0x9CA1F0: VATS camera data type 0xF on the player, VATS mode 4) whenever Actor vtbl 0x22C(0) is true - which
//      includes life state 6 (essential down). A down from a hit happens outside the player's update, and from the next
//      frame on the update takes its dead/special branch, so that line is never reached; fall damage is applied inside
//      the normal branch (character controller landing), so the same frame goes on to 0x9438A7 with life 6 and the
//      death camera starts, and nothing ends it after the revive. The call at 0x9438F1 goes through PEF, which skips it
//      while the player is essential-down (life 6); dead (1 / 2) unchanged. A snapshot (update branch, life, knock,
//      PlayerCharacter +0x798..+0x79B, player controls +0x680, sit state +0x1AC, idle camera 0x11E0788, VATS mode) is
//      logged at the down / revive / get-up.
//
// Broadcasts NVSE messages from "PlayerEssentialFix": 1 = Downed (player entered life state 6), 2 = Revived.
// Message data = Actor* (the player).
#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <stdarg.h>
#include <math.h>

typedef uint32_t UInt32; typedef uint8_t UInt8; typedef uint16_t UInt16; typedef int32_t SInt32; typedef int8_t SInt8;

struct PluginInfo { UInt32 infoVersion; const char* name; UInt32 version; };
struct NVSEInterface {
	UInt32 nvseVersion, runtimeVersion, editorVersion, isEditor;
	void* RegisterCommand; void* SetOpcodeBase; void* (*QueryInterface)(UInt32 id); UInt32 (*GetPluginHandle)(void);
};
struct NVSEMessage { const char* sender; UInt32 type; UInt32 dataLen; void* data; };
typedef void (*NVSEEventCallback)(NVSEMessage*);
struct NVSEMessagingInterface {
	UInt32 version;
	bool (*RegisterListener)(UInt32, const char*, NVSEEventCallback);
	bool (*Dispatch)(UInt32 sender, UInt32 messageType, void* data, UInt32 dataLen, const char* receiver);
};
enum { kInterface_Messaging = 2 };
static const UInt32 kRuntime_1_4_0_525 = 0x040020D0, kVersion = 8;
enum { kPEF_Downed = 1, kPEF_Revived = 2 };

static const UInt32 kPtr_Player = 0x011DEA3C, kPtr_IdleManager = 0x011CB6A0;
static const UInt32 kAddr_SetLifeState = 0x008A1800, kAddr_ReviveRestore = 0x008A0960;
static const UInt32 kAddr_FindIdle = 0x00600950, kAddr_QueueSpecialIdle = 0x00497CA0, kAddr_GetRagdollObj = 0x008ADCB0;
static const UInt32 kOff_LifeState = 0x108, kOff_Process = 0x68, kOff_ThirdPerson = 0x64A, kOff_KnockState = 0x13C,
	kOff_HitData = 0x240, kOff_ProcLevel = 0x28, kOff_AVOwner = 0xA4;
static const UInt32 kVtbl_ProcResetHitData = 0x778, kVtbl_ProcNoAnimGetUp = 0x420, kVtbl_ActorGetAnimData = 0x1E4,
	kVtbl_AVOwnerGetAV = 0x0C, kVtbl_ActorIsParalyzed = 0x234, kVtbl_RagdollSetMode = 0xD8;

static FILE* g_log = nullptr;
static NVSEMessagingInterface* g_msg = nullptr;
static UInt32 g_handle = 0;
static bool g_revivePending = false;

static void Log(const char* fmt, ...) {
	if (!g_log) return;
	SYSTEMTIME t; GetLocalTime(&t);
	fprintf(g_log, "%02d:%02d:%02d ", t.wHour, t.wMinute, t.wSecond);
	va_list a; va_start(a, fmt); vfprintf(g_log, fmt, a); va_end(a);
	fputc('\n', g_log); fflush(g_log);
}

template <typename T> static inline T& At(void* p, UInt32 off) { return *(T*)((UInt8*)p + off); }
static inline void* VFn(void* obj, UInt32 off) { return (*(void***)obj)[off / 4]; }
static inline void* Player() { return *(void**)kPtr_Player; }

typedef float (__fastcall* GetAV_t)(void*, void*, UInt32);
static float GetAV(void* actor, UInt32 av) {
	void* owner = (UInt8*)actor + kOff_AVOwner;
	return ((GetAV_t)VFn(owner, kVtbl_AVOwnerGetAV))(owner, nullptr, av);
}

// ---- detours -------------------------------------------------------------------------------------
static UInt8* AllocExec(UInt32 n) { return (UInt8*)VirtualAlloc(nullptr, n, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE); }
static void WriteJmp(UInt32 at, UInt32 to) {
	DWORD old; VirtualProtect((void*)at, 5, PAGE_EXECUTE_READWRITE, &old);
	*(UInt8*)at = 0xE9; *(UInt32*)(at + 1) = to - at - 5;
	VirtualProtect((void*)at, 5, old, &old);
}
// Copies a verified, position-independent prologue to a trampoline (or chains an existing E9 detour).
static void* DetourCopy(UInt32 addr, const UInt8* expect, UInt32 len, void* hook, const char* what) {
	UInt8* fn = (UInt8*)addr; UInt8* tr = AllocExec(32);
	if (fn[0] == 0xE9) {
		UInt32 prev = addr + 5 + *(UInt32*)(fn + 1);
		tr[0] = 0xE9; *(UInt32*)(tr + 1) = prev - (UInt32)tr - 5;
		Log("detour: %s already detoured by another plugin (-> %08X), chaining", what, prev);
	} else {
		if (memcmp(fn, expect, len)) { Log("detour: %s prologue mismatch, NOT installed", what); return nullptr; }
		memcpy(tr, fn, len);
		tr[len] = 0xE9; *(UInt32*)(tr + len + 1) = (addr + len) - ((UInt32)tr + len) - 5;
	}
	DWORD old; VirtualProtect(fn, len, PAGE_EXECUTE_READWRITE, &old);
	fn[0] = 0xE9; *(UInt32*)(fn + 1) = (UInt32)hook - addr - 5;
	for (UInt32 i = 5; i < len; i++) fn[i] = 0x90;
	VirtualProtect(fn, len, old, &old);
	FlushInstructionCache(GetCurrentProcess(), fn, len);
	Log("detour: %s installed", what);
	return tr;
}

static void Broadcast(UInt32 type) {
	void* p = Player();
	if (g_msg) g_msg->Dispatch(g_handle, type, &p, sizeof(p), nullptr);
}

// ---- stand-up ------------------------------------------------------------------------------------
typedef void* (__fastcall* FindIdle_t)(void*, void*, void*, void*);
typedef void  (__fastcall* Queue_t)(void*, void*, void*, UInt32);
typedef void* (__fastcall* GetRag_t)(void*, void*);
typedef void  (__fastcall* F2_t)(void*, void*, UInt32, UInt32);
typedef void  (__fastcall* NoAnim_t)(void*, void*, void*);
typedef void* (__fastcall* GetAnim_t)(void*, void*);
typedef void  (__fastcall* V0_t)(void*, void*);
typedef bool  (__fastcall* B0_t)(void*, void*);

static void StandUp(void* player) {
	void* proc = At<void*>(player, kOff_Process);
	if (!proc) { Log("standup: no process"); return; }
	UInt32 level = At<UInt32>(proc, kOff_ProcLevel);
	if (level > 1) { Log("standup: process level %u, skipped", level); return; }
	SInt8 knock = At<SInt8>(proc, kOff_KnockState);
	void* hd = At<void*>(proc, kOff_HitData);
	SInt32 hitLoc = hd ? At<SInt32>(hd, 0x10) : -99;
	bool para = ((B0_t)VFn(player, kVtbl_ActorIsParalyzed))(player, nullptr);
	Log("standup: knock=%d life=%u health=%.1f fatigue=%.1f paralyzed=%d hitLoc=%d 3rd=%d",
		knock, At<UInt32>(player, kOff_LifeState), GetAV(player, 0x10), GetAV(player, 0x16), para, hitLoc,
		At<UInt8>(player, kOff_ThirdPerson));
	((V0_t)VFn(proc, kVtbl_ProcResetHitData))(proc, nullptr);
	hd = At<void*>(proc, kOff_HitData);
	if (hd) At<SInt32>(hd, 0x10) = -1;
	if (knock != 1 && knock != 3) { Log("standup: not knocked, nothing to do"); return; }

	UInt8 third = At<UInt8>(player, kOff_ThirdPerson);
	At<UInt8>(player, kOff_ThirdPerson) = 1;           // get-up idles play on the 3rd-person AnimData
	void* animData = ((GetAnim_t)VFn(player, kVtbl_ActorGetAnimData))(player, nullptr);
	At<SInt8>(proc, kOff_KnockState) = 3;              // KnockedDownIdles need GetKnockedState != 0 (engine sets 3 too)
	void* idle = ((FindIdle_t)kAddr_FindIdle)(*(void**)kPtr_IdleManager, nullptr, player, nullptr);
	void* rag = ((GetRag_t)kAddr_GetRagdollObj)(player, nullptr);
	if (rag) ((F2_t)VFn(rag, kVtbl_RagdollSetMode))(rag, nullptr, 0, 0);
	if (idle && animData) {
		At<SInt8>(proc, kOff_KnockState) = 5;
		((Queue_t)kAddr_QueueSpecialIdle)(animData, nullptr, idle, 0x14);
		Log("standup: get-up idle %08X queued (animData %p, ragdoll %p)", At<UInt32>(idle, 0x0C), animData, rag);
	} else {
		((NoAnim_t)VFn(proc, kVtbl_ProcNoAnimGetUp))(proc, nullptr, player);
		Log("standup: no get-up idle found, engine stand-up without animation (ragdoll %p)", rag);
	}
	At<UInt8>(player, kOff_ThirdPerson) = third;
}

// ---- hooks ---------------------------------------------------------------------------------------
typedef void (__fastcall* SetLifeState_t)(void*, void*, UInt32);
static SetLifeState_t g_SetLifeState = nullptr;
static void __fastcall Hook_SetLifeState(void* actor, void* edx, UInt32 state) {
	UInt32 before = At<UInt32>(actor, kOff_LifeState);
	g_SetLifeState(actor, edx, state);
	if (actor != Player()) return;
	UInt32 after = At<UInt32>(actor, kOff_LifeState);
	if (before == after) return;
	Log("life state %u -> %u", before, after);
	g_revivePending = false;
	if (after == 6) Broadcast(kPEF_Downed);
	else if (before == 6 && after == 0) g_revivePending = true;   // Actor::Update calls the restore (0x8A0960) next
}

static void KnockProcessingOn();
static void Snap(const char* where, int site, bool force);
static const UInt32 kAddr_SetWeaponOut = 0x008A6840, kAddr_IsWeaponOut = 0x008A6970;
typedef void (__fastcall* SetWeaponOut_t)(void*, void*, bool);
static bool g_redrawWeapon = false;
// ---- knock-over on going down ---------------------------------------------------------------
static const UInt32 kAddr_PushForce = 0x00646580, kAddr_CanBePushed = 0x008845A0, kVtbl_ProcPushActorAway = 0x418,
	kVtbl_ProcGetUnconsciousTimer = 0xE4;
typedef float (__cdecl* PushForce_t)(void* avOwner, SInt32 force);
typedef void  (__fastcall* Push_t)(void* proc, void*, void* actor, float x, float y, float z, float force);
typedef float (__fastcall* F0_t)(void*, void*);
static void KnockOver(void* player) {
	void* proc = At<void*>(player, kOff_Process);
	if (!proc || At<UInt32>(proc, kOff_ProcLevel) > 1) { Log("down: no high process"); return; }
	SInt8 knock = At<SInt8>(proc, kOff_KnockState);
	bool canPush = ((B0_t)kAddr_CanBePushed)(player, nullptr);
	float timer = ((F0_t)VFn(proc, kVtbl_ProcGetUnconsciousTimer))(proc, nullptr);
	void* rag = ((GetRag_t)kAddr_GetRagdollObj)(player, nullptr);
	Log("down: knock=%d canPush=%d timer=%.1f ragdoll=%p 3rd=%d health=%.1f", knock, canPush, timer, rag,
		At<UInt8>(player, kOff_ThirdPerson), GetAV(player, 0x10));
	Snap("down", -1, true);
	KnockProcessingOn();
	if (((B0_t)kAddr_IsWeaponOut)(player, nullptr)) {               // put the weapon away; drawn again when up
		((SetWeaponOut_t)kAddr_SetWeaponOut)(player, nullptr, false);
		g_redrawWeapon = true;
		Log("weapon: put away while down");
	}
	if (knock != 0) return;                                        // the engine knocked it over itself
	// push from just in front of the player (it falls backward), PushActorAway force 2
	float rz = At<float>(player, 0x2C), x = At<float>(player, 0x30), y = At<float>(player, 0x34), z = At<float>(player, 0x38);
	float fx = x + 40.0f * sinf(rz), fy = y + 40.0f * cosf(rz);
	float force = ((PushForce_t)kAddr_PushForce)((UInt8*)player + kOff_AVOwner, 2);
	((Push_t)VFn(proc, kVtbl_ProcPushActorAway))(proc, nullptr, player, fx, fy, z, force);
	Log("down: pushed over (force %.1f) -> knock=%d", force, At<SInt8>(proc, kOff_KnockState));
}

// ---- knocked-state processing for the player while down -----------------------------------
// PlayerCharacter::Update (0x93E840) has four branches, each calling Character::Update 0x8D3550 twice (1st- and
// 3rd-person view). The normal branch (0x9437DB) is not taken while the player is down, so the second call of every
// pair is redirected.
static const UInt32 kSites_PlayerCharUpdate[] = { 0x0093CA81, 0x0093F9D1, 0x00940113, 0x009437DB };
static const UInt32 kAddr_CharacterUpdate = 0x008D3550, kVtbl_ProcKnockedState = 0x41C;
static bool g_sitePatched[4];
typedef void (__fastcall* CharUpdate_t)(void*, void*, float);
static const CharUpdate_t g_charUpdate = (CharUpdate_t)kAddr_CharacterUpdate;
static bool g_knockActive = false;
static void SetCallTarget(UInt32 site, UInt32 target) {
	DWORD old; VirtualProtect((void*)(site + 1), 4, PAGE_EXECUTE_READWRITE, &old);
	*(UInt32*)(site + 1) = target - site - 5;
	VirtualProtect((void*)(site + 1), 4, old, &old);
	FlushInstructionCache(GetCurrentProcess(), (void*)site, 5);
}
static void KnockProcessingOff(const char* why);
typedef float (__cdecl* Rest_t)(void*);
static void Snap(const char* where, int site, bool force);
static void CharUpdateCommon(void* actor, void* edx, float dt, int site) {
	g_charUpdate(actor, edx, dt);
	if (actor != Player()) return;
	if (!g_knockActive) return;
	void* proc = At<void*>(actor, kOff_Process);
	UInt32 life = At<UInt32>(actor, kOff_LifeState);
	if (!proc || At<UInt32>(proc, kOff_ProcLevel) > 1 || life == 1 || life == 2) { KnockProcessingOff("player dead / no process"); return; }
	SInt8 before = At<SInt8>(proc, kOff_KnockState);
	if (before == 0 && life != 6) { KnockProcessingOff("player up"); return; }
	UInt8 third = At<UInt8>(actor, kOff_ThirdPerson);
	// diagnostics while down: first call, then every 60th - which knocked-state check holds the player
	static UInt32 calls = 0;
	if (calls++ % 60 == 0) {
		At<UInt8>(actor, kOff_ThirdPerson) = 1;
		void* ad = ((GetAnim_t)VFn(actor, kVtbl_ActorGetAnimData))(actor, nullptr);
		void* ad1st = At<void*>(actor, 0x690);
		void* root = ad ? At<void*>(ad, 0x0C) : nullptr;
		float rest = root ? ((Rest_t)0x00C82580)(root) : -1.0f;
		Log("down tick %u: knock=%d life=%u fatigue=%.1f paralyzed=%d timer=%.2f animData=%p (1st %p) root=%p ragdollBlend=%.3f canPush=%d",
			calls - 1, before, life, GetAV(actor, 0x16), ((B0_t)VFn(actor, kVtbl_ActorIsParalyzed))(actor, nullptr),
			((F0_t)VFn(proc, kVtbl_ProcGetUnconsciousTimer))(proc, nullptr), ad, ad1st, root, rest,
			((B0_t)kAddr_CanBePushed)(actor, nullptr));
	}
	At<UInt8>(actor, kOff_ThirdPerson) = 1;                   // the state machine skips the 1st-person anim data
	((NoAnim_t)VFn(proc, kVtbl_ProcKnockedState))(proc, nullptr, actor);
	At<UInt8>(actor, kOff_ThirdPerson) = third;
	SInt8 after = At<SInt8>(proc, kOff_KnockState);
	if (after != before) Log("knocked state %d -> %d (life %u)", before, after, At<UInt32>(actor, kOff_LifeState));
}
static void __fastcall Hook_CharUpdate0(void* a, void* e, float dt) { CharUpdateCommon(a, e, dt, 0); }
static void __fastcall Hook_CharUpdate1(void* a, void* e, float dt) { CharUpdateCommon(a, e, dt, 1); }
static void __fastcall Hook_CharUpdate2(void* a, void* e, float dt) { CharUpdateCommon(a, e, dt, 2); }
static void __fastcall Hook_CharUpdate3(void* a, void* e, float dt) { CharUpdateCommon(a, e, dt, 3); }
static void* const kSiteHooks[4] = { (void*)Hook_CharUpdate0, (void*)Hook_CharUpdate1, (void*)Hook_CharUpdate2, (void*)Hook_CharUpdate3 };
typedef bool (__fastcall* IsDead_t)(void*, void*, bool);
typedef UInt32 (__fastcall* VatsMode_t)(void*, void*);
struct SnapState { int site; UInt32 life; SInt32 knock; UInt8 f798, f799, f79A, f79B, controls, third; UInt32 sit, idleCam, vatsMode; bool dead; };
static SnapState g_last; static bool g_haveLast = false;
static void Snap(const char* where, int site, bool force) {
	void* pl = Player(); if (!pl) return;
	void* proc = At<void*>(pl, kOff_Process);
	SnapState n; memset(&n, 0, sizeof(n));
	n.site = site; n.life = At<UInt32>(pl, kOff_LifeState);
	n.knock = (proc && At<UInt32>(proc, kOff_ProcLevel) <= 1) ? At<SInt8>(proc, kOff_KnockState) : -99;
	n.f798 = At<UInt8>(pl, 0x798); n.f799 = At<UInt8>(pl, 0x799); n.f79A = At<UInt8>(pl, 0x79A); n.f79B = At<UInt8>(pl, 0x79B);
	n.controls = At<UInt8>(pl, 0x680); n.third = At<UInt8>(pl, kOff_ThirdPerson);
	n.sit = At<UInt32>(pl, 0x1AC); n.idleCam = *(UInt32*)0x011E0788;
	n.dead = ((IsDead_t)VFn(pl, 0x22C))(pl, nullptr, false);
	n.vatsMode = ((VatsMode_t)0x0044DDC0)((void*)0x011F2250, nullptr);
	if (!force && g_haveLast && !memcmp(&n, &g_last, sizeof(n))) return;
	g_last = n; g_haveLast = true;
	static const char* kSite[] = { "CA81", "F9D1", "0113", "37DB(normal)" };
	Log("snap %s: update %s life=%u knock=%d dead=%d vats=%u flags798-79B=%u%u%u%u controls=%02X sit=%u idleCam=%08X 3rd=%u flagTimer=%.2f deathTimer=%.2f",
		where, site >= 0 ? kSite[site] : "-", n.life, n.knock, n.dead, n.vatsMode, n.f798, n.f799, n.f79A, n.f79B, n.controls, n.sit, n.idleCam, n.third,
		*(float*)0x011E0798, *(float*)0x011A3B34);
}
static void KnockProcessingOn() {
	if (g_knockActive) return;
	int n = 0;
	for (int i = 0; i < 4; i++) {
		UInt32 a = kSites_PlayerCharUpdate[i]; UInt8* site = (UInt8*)a;
		g_sitePatched[i] = false;
		if (site[0] != 0xE8) { Log("knock processing: site %08X is not a call - skipped", a); continue; }
		UInt32 cur = a + 5 + *(UInt32*)(site + 1);
		if (cur == (UInt32)kSiteHooks[i]) { g_sitePatched[i] = true; n++; continue; }
		if (cur != kAddr_CharacterUpdate) { Log("knock processing: site %08X redirected by another plugin (-> %08X) - skipped", a, cur); continue; }
		SetCallTarget(a, (UInt32)kSiteHooks[i]);
		g_sitePatched[i] = true; n++;
	}
	g_knockActive = n > 0;
	Log("knock processing: on (%d of 4 call sites)", n);
}
static void KnockProcessingOff(const char* why) {
	if (!g_knockActive) return;
	g_knockActive = false;
	Log("knock processing: off (%s)", why);
	Snap("player up", -1, true);
	for (int i = 0; i < 4; i++) if (g_sitePatched[i]) { SetCallTarget(kSites_PlayerCharUpdate[i], kAddr_CharacterUpdate); g_sitePatched[i] = false; }
	void* pl = Player();
	if (g_redrawWeapon && pl && At<UInt32>(pl, kOff_LifeState) == 0) {
		((SetWeaponOut_t)kAddr_SetWeaponOut)(pl, nullptr, true);
		Log("weapon: drawn again after the get-up");
	}
	g_redrawWeapon = false;
}

// ---- player-death VATS camera while essential-down --------------------------------------------
static const UInt32 kSite_PlayerDeathCam = 0x009438F1, kAddr_StartPlayerDeathCam = 0x009CA1F0;
typedef void (__fastcall* Thiscall0_t)(void*, void*);
static Thiscall0_t g_prevDeathCam = (Thiscall0_t)kAddr_StartPlayerDeathCam;
static void __fastcall Hook_StartPlayerDeathCam(void* vats, void* edx) {
	void* pl = Player();
	if (pl && At<UInt32>(pl, kOff_LifeState) == 6) {
		static UInt32 n = 0;
		if (n++ < 5) Log("death camera: not started (player essential-down, life 6)");
		return;
	}
	g_prevDeathCam(vats, edx);
}
static void InstallDeathCamGuard() {
	UInt8* site = (UInt8*)kSite_PlayerDeathCam;
	if (site[0] != 0xE8) { Log("death camera guard: site %08X is not a call - NOT installed", kSite_PlayerDeathCam); return; }
	UInt32 cur = kSite_PlayerDeathCam + 5 + *(UInt32*)(site + 1);
	g_prevDeathCam = (Thiscall0_t)cur;
	SetCallTarget(kSite_PlayerDeathCam, (UInt32)Hook_StartPlayerDeathCam);
	Log("death camera guard: call %08X -> PEF (was %08X%s)", kSite_PlayerDeathCam, cur, cur == kAddr_StartPlayerDeathCam ? ", vanilla" : ", another plugin - chained");
}
typedef void (__fastcall* Restore_t)(void*, void*);
static Restore_t g_Restore = nullptr;
static void __fastcall Hook_Restore(void* actor, void* edx) {
	g_Restore(actor, edx);
	if (actor != Player()) return;
	if (!g_revivePending && At<UInt32>(actor, kOff_LifeState) == 6) { KnockOver(actor); return; }   // Kill's essential branch
	if (!g_revivePending) return;
	g_revivePending = false;
	Log("revive: health/fatigue restored");
	Snap("revive", -1, true);
	StandUp(actor);
	Snap("after get-up queued", -1, true);
	Broadcast(kPEF_Revived);
}

// ---- NVSE entry points ---------------------------------------------------------------------------
extern "C" {
__declspec(dllexport) bool NVSEPlugin_Query(const NVSEInterface* nvse, PluginInfo* info) {
	info->infoVersion = 1; info->name = "PlayerEssentialFix"; info->version = kVersion;
	if (nvse->isEditor) return false;
	if (nvse->runtimeVersion != kRuntime_1_4_0_525) return false;
	return true;
}
__declspec(dllexport) bool NVSEPlugin_Load(const NVSEInterface* nvse) {
	g_log = fopen("PlayerEssentialFix.log", "w");
	Log("PlayerEssentialFix v%u", kVersion);
	g_handle = nvse->GetPluginHandle();
	g_msg = (NVSEMessagingInterface*)nvse->QueryInterface(kInterface_Messaging);
	static const UInt8 pSet[] = { 0x55, 0x8B, 0xEC, 0x6A, 0xFF, 0x68, 0x58, 0x4E, 0xF1, 0x00 };
	static const UInt8 pRes[] = { 0x55, 0x8B, 0xEC, 0x83, 0xEC, 0x10 };
	g_SetLifeState = (SetLifeState_t)DetourCopy(kAddr_SetLifeState, pSet, sizeof(pSet), (void*)Hook_SetLifeState, "Actor::SetLifeState");
	g_Restore = (Restore_t)DetourCopy(kAddr_ReviveRestore, pRes, sizeof(pRes), (void*)Hook_Restore, "Actor revive restore 0x8A0960");
	InstallDeathCamGuard();
	return true;
}
}
