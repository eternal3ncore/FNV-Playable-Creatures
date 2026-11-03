"""The creature families: one plugin (and one download pack) each.

  plugin    the family's plugin, PlayableCreatures_<name>.esp
  races     local ids of its RACE records (adult + child races) in the build output
  prefixes  EDID prefixes of every record that belongs to the family (checked in that order; `exclude` wins)
  meshes    folders under meshes\\PlayableCreatures shipped with the pack (the first gets the family's Empty.nif)
  fx        folders under sound\\fx\\npc\\playablecreatures shipped with the pack
  ttw       True = Tale of Two Wastelands only (built with the TTW master list)
  addon_of  family whose plugin is a master of this one (TTW add-ons to a New Vegas family)
Local ids are the ones of the combined build (races 0x800.., TTW races 0x8800.., voice records 0x4800..), so the ini
and the DLL refer to <family plugin>|<the same id>."""

FNV_MASTERS = ['FalloutNV.esm', 'DeadMoney.esm', 'HonestHearts.esm', 'LonesomeRoad.esm', 'OldWorldBlues.esm']
TTW_MASTERS = FNV_MASTERS + ['Fallout3.esm', 'Anchorage.esm', 'ThePitt.esm', 'BrokenSteel.esm', 'PointLookout.esm', 'Zeta.esm']


def F(name, races, prefixes, meshes, fx=(), ttw=False, addon_of=None, exclude=()):
    return dict(name=name, plugin=f'PlayableCreatures_{name}.esp', races=list(races), prefixes=tuple(prefixes),
                exclude=tuple(exclude), meshes=list(meshes), fx=list(fx), ttw=ttw, addon_of=addon_of)


SMDC = ('PCSuperMutantDC', 'PCSuperMutantBruteDC', 'PCSuperMutantMasterDC')
FAMILIES = [
    F('Zetan', [0x800, 0x8D7, 0x8E0, 0x8E3], ['PCZetan'], ['Zetan'], ['zetan']),
    F('GhostPeople', [0x805, 0x806, 0x8D8, 0x8D9], ['PCGhost'], ['Ghost'], ['ghost']),
    F('FeralGhouls', [0x855, 0x856, 0x8DA, 0x8DB], ['PCFeralGhoul', 'PCGlowingOne'], ['Ghoul', 'GlowingOne']),
    F('SuperMutants', [0x857, 0x858, 0x8DC, 0x8DD], ['PCSuperMutant', 'PCNightkin'], ['SuperMutant', 'Nightkin'],
      ['supermutant'], exclude=SMDC),
    F('Tunnelers', [0x8AC, 0x8CE, 0x8DE, 0x8DF], ['PCTunneler', 'PCSporeCarrier'], ['Tunneler']),
    F('Eyebot', [0x8E4, 0x8E8], ['PCEyebot'], ['Eyebot']),
    F('Securitron', [0x8ED, 0x8F1, 0x8F5, 0x8F6], ['PCSecuritron'], ['Securitron']),
    F('Protectron', [0x949, 0x94D], ['PCProtectron'], ['Protectron']),
    F('Robobrain', [0x954, 0x958], ['PCRobobrain'], ['Robobrain']),
    F('MisterHandy', [0x95E, 0x962, 0x968, 0x96C], ['PCMisterHandy', 'PCMisterGutsy'], ['MisterHandy', 'MisterGutsy']),
    F('SentryBot', [0x96F, 0x973], ['PCSentryBot'], ['SentryBot']),
    F('Deathclaw', [0x980, 0x985, 0x986, 0x98A, 0x98B, 0x98F], ['PCDeathclaw'], ['Deathclaw']),
    F('Lakelurks', [0x9F1, 0x9F6, 0x9F7, 0x9FB], ['PCLakelurk'], ['Lakelurk']),
    # Tale of Two Wastelands
    F('Swampfolk', list(range(0x8802, 0x8807)) + list(range(0x8882, 0x8887)), ['PCSwampfolk', 'PCHillfolk'],
      ['Swampfolk', 'Hillfolk'], ttw=True),
    F('Trogs', [0x8807, 0x8808, 0x8809, 0x8887, 0x8888, 0x8889], ['PCTrog'], ['Trog'], ttw=True),
    F('SuperMutantsTTW', [0x8877, 0x887A, 0x887D, 0x888A, 0x888B, 0x888C], SMDC, [], ttw=True, addon_of='SuperMutants'),
    F('Mirelurks', [0x8893, 0x8896, 0x8899, 0x889C, 0x889D, 0x889E], ['PCMirelurk'], ['Mirelurk'], ttw=True),
    F('RobobrainTTW', [], [], [], ttw=True, addon_of='Robobrain'),          # the Fallout 3 (female) robobrain voice
]
BY_NAME = {f['name']: f for f in FAMILIES}
EMPTY_OLD = 'PlayableCreatures\\Zetan\\Empty.nif'


def masters_of(fam):
    m = list(TTW_MASTERS if fam['ttw'] else FNV_MASTERS)
    if fam['addon_of']: m.append(BY_NAME[fam['addon_of']]['plugin'])
    return m


def empty_path(fam):
    """the family's own copy of the empty mesh (head parts, hands, hair); add-ons use their base family's"""
    base = BY_NAME[fam['addon_of']] if fam['addon_of'] else fam
    return f"PlayableCreatures\\{base['meshes'][0]}\\Empty.nif"


def family_of_edid(edid):
    for fam in FAMILIES:
        if any(edid.startswith(p) for p in fam['prefixes']) and not any(edid.startswith(x) for x in fam['exclude']):
            return fam['name']
    return None
