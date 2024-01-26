import re


class SIDC:
    def __init__(self):
        # SET A
        self.version = '30'
        self.identity = '01'
        self.symbolset = '00'
        self.status = '0'  # (name without hints of damaged/destroyed)
        self.hq = '0'  # we keep it as "unknown"
        self.amplifiers = '00'
        # SET B
        self.entity = '00'
        self.entity_type = '00'
        self.entity_subtype = '00'
        self.modifier1 = '00'
        self.modifier2 = '00'

    def to_string(self):
        # Set A
        # pylint: disable=line-too-long
        set_a = f'{self.version}{self.identity}{self.symbolset}{self.status}{self.hq}{self.amplifiers}'
        # xpylint: disable=line-too-long
        set_b = f'{self.entity}{self.entity_type}{self.entity_subtype}{self.modifier1}{self.modifier2}'
        return f'{set_a}{set_b}'


def check(unit_map):
    # filter ua / ru unit
    ua_units = dict(filter(lambda x: x[1]['s'] == 'ua', unit_map.items()))
    ru_units = dict(filter(lambda x: x[1]['s'] == 'ru', unit_map.items()))
    for (_, unit) in ua_units.items():
        _ = _convert(unit)
    for (_, unit) in ru_units.items():
        _ = _convert(unit)


def update(unit_map):
    for (uid, unit) in unit_map.items():
        sidc_string = _convert(unit)
        unit_map[uid]['sidc'] = sidc_string
    return unit_map


def _convert(unit):
    fullname = unit['n']  # full unit name in map
    side = unit['s']  # ua|ru
    # fix some unit names, split into child/parent ect.
    (name, parent) = _prepare_unit_name(fullname)
    # init sidc
    sidc = SIDC()
    # SET A
    sidc.identity = _get_side(side)  # set identity
    sidc.symbolset = _get_symbol_set(name)  # set symbol set
    sidc.amplifiers = _get_amplifiers(name, parent)  # set amplifier
    # SET B
    (entity, entity_type, entity_subtype, modifier1, modifier2) = _get_set_b(name, sidc.symbolset)
    sidc.entity = entity
    sidc.entity_type = entity_type
    sidc.entity_subtype = entity_subtype
    sidc.modifier1 = modifier1
    sidc.modifier2 = modifier2

    # finally return sidc string
    return sidc.to_string()


def _prepare_unit_name(name):
    # to lowercase
    name = name.lower()
    # fix some old unit names
    name_fixes = {
        'birds of magyar': '[uav] birds of magyar',
        'hornets of dovbush': '[uav] hornets of dovbush',
        'sons of thunder': '[uav] sons of thunder',
        'wasp unit': '[uav] was unit'
    }
    if name in name_fixes:
        name = name_fixes[name]

    # force standalone 'uav' into '[uav]'
    if 'uav' in name and '[uav]' not in name:
        name.replace('uav', '[uav]')
    if 'drone' in name and '[uav]' not in name:
        name.replace('drone', '[uav]')

    # remove stuff in brackets
    name = re.sub(r'\(.+?\)', '', name)

    # split name into unit name and parent name
    # if it contains the phrase " of ".
    if ' of ' in name:
        # exceptions (for better identification later on)
        exceptions = [
            '[uav] birds of magyar',
            'legion of russia battalion',
            '[uav] sons of thunder',
            '[uav] hornets of dovbush',
            'freedom of russia legion',
            'legion of russia legion'
        ]
        if name in exceptions:
            return (name, None)
        parts = name.split(' of ', 1)  # split at the first " of "
        return (parts[0], parts[1])

    # all without " of "
    return (name, None)


def _get_side(side):
    if side == 'ua':
        return '03'  # friend
    if side == 'ru':
        return '06'  # enemy
    return '00' # unknown


def _get_symbol_set(name):
    # relevant symbol sets are:
    # air, land unit, land installations
    # sea surface, sea subsurface
    symbolsets = {
        'unknown': '00',
        'air': '01',
        'land_unit': '10',
        'land_installation': '20',
        'sea_surface': '30',
        'sea_subsurface': '35'
    }

    # Note: default is land unit
    symbol_set = '10'  # land unit

    # to fix some potential false positives
    # we use some hard checks

    # all uav units -> land units
    checkwords = ['[uav]']
    for checkword in checkwords:
        if checkword in name:
            return symbolsets['land_unit']

    # all air bases/fields -> land installation
    checkwords = ['air base', 'airbase', 'air field', 'airfield', 'military base',
                  'command post', 'testing centre', 'aviation center', 'training center']
    for checkword in checkwords:
        if checkword in name:
            return symbolsets['land_installation']

    # all anti-aircraft units -> land installation
    checkwords = ['anti-aircraft']
    for checkword in checkwords:
        if checkword in name:
            return symbolsets['land_unit']

    # anti-submarine units -> air
    checkwords = ['anti-submarine helicopter', 'anti-submarine aviation']
    for checkword in checkwords:
        if checkword in name:
            return symbolsets['air']

    # sea subsurface
    checkwords = ['submarine']
    for checkword in checkwords:
        if checkword in name:
            return symbolsets['sea_subsurface']

    # air
    # must be chekced before sea surface units
    checkwords = ['aviation', 'helicopter', 'aircraft', 'a-50', 'su-25']
    for checkword in checkwords:
        if checkword in name:
            return symbolsets['air']

    # sea surface
    checkwords = [
        'minesweeper',
        'ship',
        'corvette',
        'tanker',
        'frigate',
        'boat',
        'cruiser',
        'flotilla',
        'oiler',
        'buyan-m'
    ]
    for checkword in checkwords:
        if checkword in name:
            return symbolsets['sea_surface']

    return symbol_set


def _get_amplifiers(name, parent):
    amplifier1 = '0'  # unknown
    amplifier2 = '0'  # unknown

    # ==================================================
    # amplifier1
    # ==================================================
    # for us only the following values are relevant:
    # 0 - Unknown
    # 1 - Echelon at brigade and below
    # 2 - Echelon at division and above
    checkwords1 = ['army group', 'army', 'corps', 'division']
    checkwords2 = ['brigade', 'regiment',
                   'battalion', 'squadron', 'company', 'detachment']
    # we test smaller unit sizes first
    for checkword in checkwords2:
        if checkword in name:
            amplifier1 = '1'
            break
    # now check all unit which are still unknown
    if amplifier1 == '0':
        for checkword in checkwords1:
            if checkword in name:
                amplifier1 = '2'
                break
    # some units or unit types are still 'unknown' at first point
    # mostly drone groups, sbu & sso groups and all the other obscure ones
    # we leave them as unknown
    # a few other groups we set manually:
    if amplifier1 == '0':
        exceptions = ['bars', '[omon]', '[pmc]', 'pmc', 'wagner group']
        for checkword in exceptions:
            if checkword in name:
                amplifier1 = '1'
                break

    # ==================================================
    # amplifier2
    # ==================================================
    # based on amplifier1 we now do the fine tuning
    dict1 = {'brigade': '8', 'regiment': '7', 'battalion': '6', 'squadron': '6',
             'company': '5', 'detachment': '4'}
    dict2 = {'army group': '4', 'army corps': '2', 'army': '3', 'corps': '2', 'division': '1'}

    if amplifier1 == '1':
        for checkword, key in dict1.items():
            if checkword in name:
                amplifier2 = key
                break

    if amplifier1 == '2':
        for checkword, key in dict2.items():
            if checkword in name:
                amplifier2 = key
                break

    # exceptions
    # bars & omon units -> battalion
    exceptions = ['bars', '[omon]', '[pmc]', 'pmc']
    for checkword in exceptions:
        if checkword in name:
            amplifier2 = dict1['battalion']
            break
    # wagner group - was a brigade
    if 'wagner group' in name:
        amplifier2 = dict1['brigade']
    # if amplifier2 is below that of the parent
    # example: 64th artillery division |of| 406th artillery brigade
    # here 'division' is actually 'divizion' aka battalion
    if parent is not None:
        if 'brigade' in parent and amplifier2 == '1':
            amplifier1 = '1'
            amplifier2 = dict1['battalion']

    # if parent is not None:
    #     print(f'{name} -> {parent} => {amplifier1} - {amplifier2}')

    return f'{amplifier1}{amplifier2}'


def _get_set_b(name, symbolset):
    # based on symbol set

    # defaults
    entity = '00'
    entity_type = '00'
    entity_subtype = '00'
    modifier1 = '00'
    modifier2 = '00'


    if symbolset == '01': # air
        (entity, entity_type, entity_subtype, modifier1, modifier2) = _get_set_b_air(name)
    elif symbolset == '10': # land unit
        (entity, entity_type, entity_subtype, modifier1, modifier2) = _get_set_b_land_unit(name)
    elif symbolset == '20': # land installations
        (entity, entity_type, entity_subtype, modifier1, modifier2) = _get_set_b_land_installation(name)
    elif symbolset == '30': # sea surface
        (entity, entity_type, entity_subtype, modifier1, modifier2) = _get_set_b_sea_surface(name)
    elif symbolset == '35': # sea subsurface
        (entity, entity_type, entity_subtype, modifier1, modifier2) = _get_set_b_sea_subsurface(name)

    # final return
    return (entity, entity_type, entity_subtype, modifier1, modifier2)

def _get_set_b_sea_subsurface(name):
    # defaults
    entity = '11' # we assume every unit is of military type
    entity_type = '00'
    entity_subtype = '00' # only for submarines (submerged, surfaced ect.) - we can ignore it
    modifier1 = '00'
    modifier2 = '00'
    # entity type
    if 'submarine' in name:
        entity_type = '01'
    # modifier1
    if 'kilo class' in name:
        modifier1 = '08' # attack
        modifier2 = '02' # diesel electric, general
    # return
    set_b = (entity, entity_type, entity_subtype, modifier1, modifier2)
    # print(f'{name} -> {set_b}')
    return set_b

def _get_set_b_sea_surface(name):
    # defaults
    entity = '12' # default: military combatant type
    entity_type = '00'
    entity_subtype = '00'
    modifier1 = '00'
    modifier2 = '00' # we don't need it

    # type->entity => subtype dicts
    military_combatant__surface = {
        'corvette': '05',
        'frigate': '04',
        'destroyer': '03',
        'cruiser': '02',
        'buyan-m': '05'
    }
    military_combatant__amphibious = {
        'landing ship': '07',
        'ropucha': '07'
    }
    military_combatant__mine_warefare = {
        'minesweeper': '02'
    }
    military_combatant__patrol_boat = {
        'patrol': '02'
    }
    military_non_combatant__auxiliary = {
        'oiler': '10',
        'tanker': '10',
        'intelligence': '04'
    }

    # entity type
    # military combatant -> surface
    for checkword, key in military_combatant__surface.items():
        if checkword in name:
            entity = '12'
            entity_type = '02'
            entity_subtype = key
            break
    # military combatant -> amphibious warefare
    for checkword, key in military_combatant__amphibious.items():
        if checkword in name:
            entity = '12'
            entity_type = '03'
            entity_subtype = key
            break
    # military combatant -> mine warfare
    for checkword, key in military_combatant__mine_warefare.items():
        if checkword in name:
            entity = '12'
            entity_type = '04'
            entity_subtype = key
            break
    # military combatant -> patrol boat
    for checkword, key in military_combatant__patrol_boat.items():
        if checkword in name:
            entity = '12'
            entity_type = '05'
            entity_subtype = key
            break
    # military non combatant -> auxiliary
    for checkword, key in military_non_combatant__auxiliary.items():
        if checkword in name:
            entity = '13'
            entity_type = '01'
            entity_subtype = key
            break

    # exceptions
    if 'dnieper river flotilla' in name:
        entity = '12'
        entity_type = '05' # patrol boats
        entity_subtype = '02' # general

    # modifiers
    modifiers1 = {
        'Antiair Warfare': '02',
        'Antisubmarine Warfare': '03',
        'Escort': '04',
        'Electronic Warfare': '05',
        'Intelligence, Surveillance, Reconnaissance': '06',
        'Mine Countermeasures': '07',
        'Missile Defense': '08',
        'Medical': '09',
        'Mine Warfare': '10',
        'Remote Multi-Mission Vehicle (USV only)': '11',
        'Special Operations Forces (SOF)': '12',
        'Surface Warfare': '13',
        'Ballistic Missile': '14',
        'Guided Missile': '15',
        'Other Guided Missile': '16',
        'Torpedo': '17',
        'Drone-Equipped': '18',
        'Helicopter-Equipped/VSTOL': '19',
    }

    # modifier1
    if 'guided missile' in name:
        modifier1 = modifiers1['Guided Missile']
    elif 'karakurt' in name:
        modifier1 = modifiers1['Guided Missile']
    elif 'askold' in name or 'tsiklon' in name:
        modifier1 = modifiers1['Guided Missile']
    elif 'tarantul' in name:
        modifier1 = modifiers1['Other Guided Missile']
    elif 'steregushchiy' in name:
        modifier1 = modifiers1['Guided Missile']
    elif 'orekhovo-zuyevo' in name:
        modifier1 = modifiers1['Guided Missile']
    elif 'asw' in name:
        modifier1 = modifiers1['Antisubmarine Warfare']
    elif 'minesweeper' in name:
        modifier1 = modifiers1['Mine Countermeasures']
    elif 'intelligence' in name:
        modifier1 = modifiers1['Intelligence, Surveillance, Reconnaissance']
    elif 'tanker' in name:
        modifier1 = modifiers1['Intelligence, Surveillance, Reconnaissance']

    # if modifier1 == '00' and 'landing ship' not in name and 'patrol' not in name:
    #     print(name)

    # if entity_type == '00':
    #     print(name)

    set_b = (entity, entity_type, entity_subtype, modifier1, modifier2)
    # print(f'{name} -> {set_b}')
    return set_b

def _get_set_b_land_installation(name):
    # defaults
    entity = '12' # default: infrastructure
    entity_type = '00'
    entity_subtype = '00'
    modifier1 = '00'
    modifier2 = '00'

    # type->entity => subtype dicts
    infrastructure__military = {
        'training center': '02',
        'military base': '02',
        'aviation center': '02',
        'testing centre': '02',
        'command post': '02'
    }
    infrastructure__transportation = {
        'airbase': '01',
        'air base': '01',
        'airfield': '01',
        'air field': '01',
    }

    # infrastructure__military
    for checkword, key in infrastructure__military.items():
        if checkword in name:
            entity = '12'
            entity_type = '08'
            entity_subtype = key
            break
    # infrastructure__transportation
    for checkword, key in infrastructure__transportation.items():
        if checkword in name:
            entity = '12'
            entity_type = '13'
            entity_subtype = key
            break

    # if entity_type == '00':
    #     print(name)

    set_b = (entity, entity_type, entity_subtype, modifier1, modifier2)
    # print(f'{name} -> {set_b}')
    return set_b

def _get_set_b_air(name):
    # defaults
    entity = '11' # default: military
    entity_type = '00'
    entity_subtype = '00'
    modifier1 = '00'
    modifier2 = '00' # we don't need it

    # type->entity => subtype dicts
    military__fixed_wing = {
        'mixed': '05',
        'bomber': '03',
        'fighter': '04',
        'tanker': '09',
        'transport': '07',
        'assault': '02',
        'reconnaissance': '11',
        'training': '12',
        'combat control': '15',
        'a-50': '16',
        'su-25': '04',
        'army aviation': '00',
        'tactical aviation': '00',
        'naval attack': '18', # we use anti-submarine here
        'early warning': '16',
        'anti-submarine': '18'
    }
    military__rotary_wing = {
        'helicopter': '00'
    }

    # military__fixed_wing
    for checkword, key in military__fixed_wing.items():
        if checkword in name:
            entity = '11'
            entity_type = '01'
            entity_subtype = key
            break
    # military__rotary_wing
    for checkword, key in military__rotary_wing.items():
        if checkword in name:
            entity = '11'
            entity_type = '02'
            entity_subtype = key
            break

    # modifier1 - we don't use them for now
    # if 'mixed' in name:
    #     modifier1 = '01'
    # elif 'bomber' in name:
    #     modifier1 = '02'
    # elif 'fighter' in name:
    #     modifier1 = '04'
    # elif 'tanker' in name:
    #     modifier1 = '06'
    # elif 'transport' in name:
    #     modifier1 = '03' # we use 'cargo' here
    # elif 'assault' in name:
    #     modifier1 = '01'
    # elif 'reconnaissance' in name:
    #     modifier1 = '18'
    # elif 'training' in name:
    #     modifier1 = '19'
    # elif 'combat control' in name:
    #     modifier1 = '11' # we use 'command post' here
    # elif 'a-50' in name:
    #     modifier1 = '12'
    # elif 'su-25' in name:
    #     modifier1 = '04' # we use 'fighter' here
    # elif 'asw' in name:
    #     modifier1 = '22'
    # elif 'submarine' in name:
    #     modifier1 = '22'
    # elif 'attack' in name:
    #     modifier1 = '01'
    # elif 'early warning' in name:
    #     modifier1 = '12'

    set_b = (entity, entity_type, entity_subtype, modifier1, modifier2)
    # print(f'{name} -> {set_b}')
    return set_b

def _get_set_b_land_unit(name):
    # defaults
    entity = '12' # default: movement & maneuver
    entity_type = '00'
    entity_subtype = '00'
    modifier1 = '00'
    modifier2 = '00'


    # basic entity and entity type
    if 'infantry' in name:
        entity = '12'
        entity_type = '11'
    elif '[uav]' in name or 'drone' in name or 'uav' in name:
        entity = '12'
        entity_type = '19'
    elif 'air assault' in name:
        entity = '12'
        entity_type = '11' # infantry
    elif 'tank' in name:
        entity = '12'
        entity_type = '05'
    elif 'air defense' in name or 'air defence' in name:
        entity = '13' # fires
        entity_type = '01'
    elif 'missile' in name or 'rocket' in name:
        entity = '13' # fires
        entity_type = '07'
    elif 'sof' in name:
        entity = '12'
        entity_type = '18'
    elif 'sbu' in name:
        entity = '12'
        entity_type = '18' #SOF
    elif 'sso' in name:
        entity = '12'
        entity_type = '18' #SOF
    elif 'mechanized' in name or 'mechanised' in name:
        entity = '12'
        entity_type = '11' # infantry
    elif 'engineering' in name or 'engineer' in name:
        entity = '14' # protection
        entity_type = '07' # engineer
    elif 'artillery' in name:
        entity = '13' # fires
        entity_type = '03'
    elif 'combined arms' in name:
        entity = '12'
        entity_type = '10'
    elif '[np]' in name:
        entity = '20' # law enforcement
        entity_type = '07'
    elif 'border guard' in name:
        entity = '20' # law enforcement
        entity_type = '02'
    elif 'rifle' in name:
        entity = '12'
        entity_type = '11'
    elif 'anti-aircraft missile' in name:
        entity = '13' # fires
        entity_type = '01'
    elif 'anti-aircraft' in name:
        entity = '13' # fires
        entity_type = '01'
    elif '[ng]' in name: # or is movement->infantry better?
        entity = '14' # protection
        entity_type = '17' # security
    elif 'omon' in name: # or is movement->infantry better?
        entity = '14' # protection
        entity_type = '17' # security
    elif 'bars' in name:
        entity = '12'
        entity_type = '11'
    elif 'territorial defense brigade' in name:
        entity = '12'
        entity_type = '11'
    elif 'tdf' in name:
        entity = '12'
        entity_type = '11'
    elif 'airborne' in name:
        entity = '12'
        entity_type = '11'
    elif 'motorized' in name:
        entity = '12'
        entity_type = '11'
    elif 'cbrn' in name:
        entity = '14' # protection
        entity_type = '01'
    elif 'nbc' in name:
        entity = '14' # protection
        entity_type = '01'
    elif '[territorial]' in name:
        entity = '12'
        entity_type = '11'
    elif '[pmc]' in name or 'pmc' in name:
        entity = '12'
        entity_type = '11'
    elif '[vol]' in name or 'volunteer' in name:
        entity = '12'
        entity_type = '11'
    elif 'signal' in name:
        entity = '11' # command & control
        entity_type = '10' # signal
    elif 'railway' in name:
        entity = '16' # sustainment
        entity_type = '36' # transportation
    elif 'logistics' in name or 'logistic' in name:
        entity = '16' # sustainment
        entity_type = '02' # all classes of supply
    elif 'reconnaissance' in name or 'reconnaisse' in name or 'recon' in name:
        entity = '12'
        entity_type = '13'
    elif 'electronic warfare' in name:
        entity = '15' # intelligence
        entity_type = '05' # electronic warfare
    elif 'communications' in name:
        entity = '11' # command & control
        entity_type = '10' # signal
    elif 'spetsnaz' in name:
        entity = '12'
        entity_type = '11'
    elif 'marine' in name:
        entity = '12'
        entity_type = '11'
    elif 'combined' in name:
        entity = '12'
        entity_type = '10'
    elif '[dpr]' in name or '[lpr]' in name:
        entity = '12'
        entity_type = '11'
    elif 'wagner group' in name:
        entity = '12'
        entity_type = '10'
    elif 'special purpose' in name: # not ideal
        entity = '12'
        entity_type = '17' # special forces
    elif 'regiment' in name: # should be last, as a catch all
        entity = '12'
        entity_type = '11'
    elif 'battalion' in name: # should be last, as a catch all
        entity = '12'
        entity_type = '11'

    # a few quick cases to set the entity_subtype
    if entity == '12' and entity_type == '11':
        if 'motorized' in name:
            entity_subtype = '04'
        elif 'mechanized' in name:
            entity_subtype = '02'

    # a few quick cases to set modifier1
    if 'marine' in name or 'naval' in name:
        modifier1 = '46' # naval

    # if entity_type == '00' and 'corps' not in name:
    #     print(name)

    set_b = (entity, entity_type, entity_subtype, modifier1, modifier2)
    # print(f'{name} -> {set_b}')
    return set_b
