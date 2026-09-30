"""Part 1: modify things (buildings, items) of the save according to the layout."""
import re, collections, heapq
from model import *
from layout import *
from geom import rect
from render import analyse

TICK = 16105210
FAC = 'Faction_10'

# regions -----------------------------------------------------------------
def in_rects(p, rects):
    x, z = p
    return any(a <= x <= b and c <= z <= d for a, b, c, d in rects)

DEMO = [(93, 172, 103, 147), (121, 144, 92, 106), (93, 113, 111, 136)]      # old player structures
# natural / keep-list
KEEP_DEFS = {'DeepDrill', 'SteamGeyser', 'Fence', 'FenceGate', 'PenMarker'}
CLEAR = [(114, 159, 107, 156), (100, 114, 111, 136), (122, 126, 92, 107), (92, 100, 110, 137),
         (116, 122, 156, 162), (106, 112, 138, 142), (160, 175, 130, 136)]                          # plants cleared here


def old_conduit_keep(p):
    return p[0] >= 145 and p[1] <= 106


def sort_key(r):
    return (r.pos[0], r.pos[1], r.id)


def cell_str(c):
    return '(%d, 0, %d)' % c


class _Tmpl:
    def __init__(self, r):
        self.raw = r.raw
        self.faction = r.faction
        self.cls = r.cls


def make_templates(M):
    T = {}
    for r in M.recs:
        if r.d not in T and r.pos and (r.faction in (None, FAC)):
            T[r.d] = _Tmpl(r)
    for r in M.recs:
        if r.faction == FAC and r.pos and (r.d not in T or T[r.d].faction != FAC):
            T[r.d] = _Tmpl(r)
    return T


def strip_tags(raw, tags):
    for t in tags:
        raw = re.sub(r'<%s>.*?</%s>' % (t, t), '', raw, flags=re.S)
        raw = re.sub(r'<%s\s*/>' % t, '', raw)
    return raw


def new_thing(M, T, d, x, z, rot=0, stuff=None, cls=None, extra=None):
    """Clone template for def d and return raw xml."""
    if d not in T:
        raise KeyError('no template for ' + d)
    t = T[d]
    raw = t.raw
    nid = M.nid()
    raw = re.sub(r'<id>[^<]*</id>', '<id>%s%d</id>' % (d, nid), raw, count=1)
    raw = re.sub(r'<pos>[^<]*</pos>', '<pos>%s</pos>' % cell_str((x, z)), raw, count=1)
    raw = re.sub(r'<rot>\d</rot>', '', raw)
    if rot:
        raw = raw.replace('</pos>', '</pos><rot>%d</rot>' % rot, 1)
    th = re.search(r'<health>(\d+)</health>', raw)
    hp = int(th.group(1)) if th else None
    if d == 'Wall' and stuff:
        hp = {'BlocksGranite': 510, 'BlocksSandstone': 420, 'BlocksLimestone': 420, 'Steel': 300, 'WoodLog': 195}.get(stuff, hp)
    if d == 'Door' and stuff == 'Steel':
        hp = 160
    raw = strip_tags(raw, ['health', 'tickDelta', 'lastFriendlyTouchTick', 'approachingPawn', 'lastUser',
                           'overrideGraphicIndex', 'taleRef', 'lastAttackTargetTick'])
    raw = re.sub(r'<spawnedTick>\d+</spawnedTick>', '<spawnedTick>%d</spawnedTick>' % TICK, raw)
    if stuff:
        if '<stuff>' in raw:
            raw = re.sub(r'<stuff>[^<]*</stuff>', '<stuff>%s</stuff>' % stuff, raw, count=1)
        else:
            raw = raw.replace('</pos>', '</pos><stuff>%s</stuff>' % stuff, 1) if not rot else raw.replace('</rot>', '</rot><stuff>%s</stuff>' % stuff, 1)
    if '<faction>' not in raw:
        raw = raw.replace('<questTags', '<faction>%s</faction><questTags' % FAC, 1)
    raw = re.sub(r'<parentThing>[^<]*</parentThing>', '<parentThing>null</parentThing>', raw)
    if hp:
        raw = re.sub(r'(<pos>[^<]*</pos>)', lambda m: m.group(1) + '<health>%d</health>' % hp, raw, count=1)
    return raw, nid


def set_raw_tag(raw, tag, val):
    if re.search(r'<%s>.*?</%s>' % (tag, tag), raw, re.S):
        return re.sub(r'<%s>.*?</%s>' % (tag, tag), lambda m: '<%s>%s</%s>' % (tag, val, tag), raw, count=1, flags=re.S)
    return raw.replace('</thing>', '<%s>%s</%s></thing>' % (tag, val, tag))


def filter_xml(defs):
    return ('<filter><disallowedSpecialFilters /><allowedDefs>%s</allowedDefs><allowedHitPointsPercents>0~1</allowedHitPointsPercents>'
            '<allowedMentalBreakChance>0~1</allowedMentalBreakChance><allowedQualityLevels>Awful~Legendary</allowedQualityLevels></filter>'
            % ''.join('<li>%s</li>' % d for d in defs))


def apply_build(M, P, log=print):
    T = make_templates(M)
    # ---------------------------------------------------------------- classify
    movable = collections.defaultdict(list)
    deleted = collections.Counter()
    moved_ids = set()
    want_move_defs = {o['move'] for o in P.objs if o.get('move')}
    want_move_defs |= {'Bed', 'BedGuest', 'WindTurbine', 'SolarGenerator', 'Battery', 'FermentingBarrel', 'Grave',
                       'HorseshoesPin'}

    for r in M.recs:
        if not r.pos:
            continue
        if r.cls in ('Pawn',):
            continue
        is_bld = r.cls.startswith('Building') or r.cls in ('Building',) or r.cls.endswith('Building_GuestBed') \
            or r.cls.endswith('Building_ManagerStation')
        if r.cls in ('Plant', 'DeadPlant'):
            if in_rects(r.pos, CLEAR):
                r.deleted = True; deleted['plant'] += 1
            continue
        if not is_bld:
            continue
        if r.d in KEEP_DEFS:
            continue
        if r.d in ('PowerConduit', 'HiddenConduit'):
            if in_rects(r.pos, DEMO) and not old_conduit_keep(r.pos):
                r.deleted = True; deleted[r.d] += 1
            continue
        if not in_rects(r.pos, DEMO):
            continue
        if r.faction not in (FAC, None):
            continue
        if r.d in ('Turret_MiniTurret', 'Turret_Mortar') and r.pos[1] <= 106 and r.pos[0] >= 145:
            continue
        if r.d in ('Sarcophagus', 'AncientCryptosleepCasket', 'Column', 'ShipChunk', 'Urn', 'SteleGrand'):
            continue
        if r.d in want_move_defs or r.d in ('Bed', 'BedGuest'):
            movable[r.d].append(r)
        else:
            r.deleted = True; deleted[r.d] += 1
    for d in movable: movable[d].sort(key=sort_key)
    log('deleted:', dict(deleted))
    log('movable:', {d: len(v) for d, v in movable.items()})

    # ---------------------------------------------------------------- beds
    pawn_bed = {}
    beds = movable['Bed']
    def owners(r): return re.findall(r'<assignedPawns>(.*?)</assignedPawns>', r.raw, re.S)
    def has_owner(r):
        m = re.search(r'<assignedPawns>(.*?)</assignedPawns>', r.raw, re.S)
        return bool(m and '<li>' in m.group(1))
    prisoner_beds = [r for r in beds if 'forOwnerType>Prisoner' in r.raw]
    medical_beds = [r for r in beds if '<medical>True</medical>' in r.raw and r not in prisoner_beds]
    owned = [r for r in beds if has_owner(r) and r not in prisoner_beds and r not in medical_beds]
    spare = [r for r in beds if r not in prisoner_beds and r not in medical_beds and r not in owned]
    # owned medical beds (owner + medical)
    pools = {'colonist': owned, 'medical': medical_beds + spare, 'prisoner': prisoner_beds}
    log('beds owned/spare/medical/prisoner:', len(owned), len(spare), len(medical_beds), len(prisoner_beds))
    guest_pool = list(movable['BedGuest'])

    # ---------------------------------------------------------------- place objects
    placed = []          # (def, pos, rot, id)
    obj_ids = {}
    def register(o, raw_id):
        obj_ids[id(o)] = raw_id

    src_used = collections.defaultdict(int)
    solid_fp = {}
    for o in P.objs:
        d = o['d']; x, z = o['pos']; rot = o['rot']
        rec = None
        if d == 'Bed':
            role = o['role']
            pool = pools[role]
            if pool:
                rec = pool.pop(0)
                if role == 'medical' and '<medical>True</medical>' not in rec.raw:
                    rec.raw = rec.raw.replace('</thing>', '<medical>True</medical></thing>')
                if role == 'medical' and rec in spare:
                    pass
                if role in ('medical',) and has_owner(rec):
                    rec.raw = re.sub(r'<assignedPawns>.*?</assignedPawns>', '<assignedPawns />', rec.raw, flags=re.S)
        elif d == 'BedGuest':
            if guest_pool:
                rec = guest_pool.pop(0)
        elif o.get('move'):
            lst = movable.get(o['move'])
            if lst is None:
                lst = [r for r in M.recs if r.d == o['move'] and r.pos and not r.deleted and r.faction in (FAC, None)
                       and not any(r is q for q in sum(movable.values(), []))]
                movable[o['move']] = lst
            k = src_used[o['move']]
            if k < len(lst):
                rec = lst[k]; src_used[o['move']] += 1
        if rec is not None:
            rec.set_pos(x, z); rec.set_rot(rot)
            rec.raw = re.sub(r'<parentThing>[^<]*</parentThing>', '<parentThing>null</parentThing>', rec.raw)
            if o.get('filt') and d == 'Shelf':
                rec.raw = re.sub(r'<allowedDefs>.*?</allowedDefs>', lambda m: '<allowedDefs>%s</allowedDefs>' % ''.join('<li>%s</li>' % q for q in o['filt']), rec.raw, flags=re.S)
            o['rid'] = rec.id; o['rec'] = rec
            moved_ids.add(rec.id)
            continue
        # create new
        stuff = o.get('stuff')
        if d == 'Bed' or d == 'BedGuest':
            tmpl = 'Bed' if d == 'Bed' else 'BedGuest'
            stuff = stuff or 'WoodLog'
            raw, nid = new_thing(M, T, tmpl, x, z, rot, stuff)
            raw = re.sub(r'<assignedPawns>.*?</assignedPawns>', '<assignedPawns />', raw, flags=re.S)
            raw = re.sub(r'<forOwnerType>.*?</forOwnerType>', '', raw)
            raw = re.sub(r'<medical>.*?</medical>', '', raw)
            raw = re.sub(r'<quality>\w+</quality>', '<quality>Normal</quality>', raw)
            if d == 'Bed' and o['role'] == 'prisoner':
                raw = raw.replace('</thing>', '<forOwnerType>Prisoner</forOwnerType></thing>')
            if d == 'Bed' and o['role'] == 'medical':
                raw = raw.replace('<alreadySetDefaultMed>', '<medical>True</medical><alreadySetDefaultMed>')
            d2 = tmpl
        elif d == 'Turret_MiniTurret':
            raw, nid = new_thing(M, T, 'Turret_MiniTurret', x, z, rot, 'Steel')
            gm = re.search(r'Gun_MiniTurret(\d+)', raw)
            gid = M.nid()
            raw = raw.replace(gm.group(1), str(gid))
            raw = re.sub(r'<lastShotTick>-?\d+</lastShotTick>', '<lastShotTick>-999999</lastShotTick>', raw)
            d2 = d
        elif d == 'Shelf':
            raw, nid = new_thing(M, T, 'Shelf', x, z, rot, o.get('stuff') or 'WoodLog')
            raw = re.sub(r'<allowedDefs>.*?</allowedDefs>', lambda m: '<allowedDefs>%s</allowedDefs>' % ''.join('<li>%s</li>' % q for q in o['filt']), raw, flags=re.S)
            raw = re.sub(r'<priority>\w+</priority>', '<priority>%s</priority>' % o.get('prio', 'Normal'), raw, count=1)
            d2 = d
        elif d == 'FueledStove':
            raw, nid = new_thing(M, T, 'FueledStove', x, z, rot)
            raw = re.sub(r'<billStack>.*?</billStack>', '<billStack><bills /></billStack>', raw, flags=re.S)
            d2 = d
        elif d in ('Heater', 'Cooler'):
            raw, nid = new_thing(M, T, d, x, z, rot)
            raw = re.sub(r'<targetTemperature>[^<]*</targetTemperature>', '<targetTemperature>%d</targetTemperature>' % o.get('target', 21), raw)
            d2 = d
        elif d == 'Battery':
            raw, nid = new_thing(M, T, 'Battery', x, z, rot)
            raw = re.sub(r'<storedPower>[^<]*</storedPower>', '<storedPower>600</storedPower>', raw)
            d2 = d
        elif d in ('ChessTable', 'PartySpot'):
            raw, nid = new_thing(M, T, d, x, z, rot, stuff)
            d2 = d
        else:
            raw, nid = new_thing(M, T, d, x, z, rot, stuff)
            d2 = d
        M.new.append(raw)
        o['rid'] = '%s%d' % (d2, nid)
        o['new_raw_idx'] = len(M.new) - 1

    # leftover movable beds (unused) -> leave deleted to avoid stray things
    for d, lst in movable.items():
        for r in lst:
            if r.id not in moved_ids and d in ('Bed', 'BedGuest'):
                log('unplaced old bed', r.id, r.pos)
    return T, movable, moved_ids, deleted


if __name__ == '__main__':
    M = SaveModel()
    P = build()
    apply_build(M, P)
    print(len(M.new), 'new things')
