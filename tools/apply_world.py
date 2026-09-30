"""Part 3: grids, zones, areas, pawns, policies; writes the final save."""
import re, random, collections, sys
from apply_struct import *

OUT = '/home/user/first/mirella fans_edited.rws'

ROOF_CONSTRUCTED = h('RoofConstructed')
ROOF_ROCK = {h('RoofRockThick'), h('RoofRockThin')}


def pack_bits(cells):
    arr = bytearray(7813)
    for (x, z) in cells:
        i = z * 250 + x
        arr[i // 8] |= 1 << (i % 8)
    return bytes(arr)


def unpack_bits(b):
    return {(i % 250, i // 250) for i in range(62500) if b[i // 8] >> (i % 8) & 1}


def get_grid(s, tag, name):
    return list(struct.unpack('<62500H', dec(s, tag, name)))


def put_grid(s, tag, name, arr):
    st = s.find('<%s>' % tag)
    m = re.compile(r'(<%s>\s*)(.*?)(\s*</%s>)' % (name, name), re.S).search(s, st)
    data = enc(struct.pack('<62500H', *arr))
    return s[:m.start(2)] + data + s[m.end(2):]


def edit_world(M, P, rocks, log=print):
    s = M.s
    # ---- text assembled so far will be reassembled; we edit the *head/tail* strings separately
    return None


def build_all(log=print):
    M = SaveModel(); P = build()
    T, movable, moved, deleted = apply_build(M, P, log=log)
    conduits, rocks = build_structures(M, P, T, log=log)
    return M, P, T, rocks





# =====================================================================
WT = ['Firefighter', 'Patient', 'Doctor', 'PatientBedRest', 'BasicWorker', 'Warden', 'Handling', 'Cooking', 'Hunting',
      'Construction', 'Growing', 'Mining', 'PlantCutting', 'Smithing', 'Tailoring', 'Art', 'Crafting', 'Hauling',
      'Cleaning', 'Research', 'HaulingUrgent', 'FinishingOff', 'Managing', 'Diplomat', 'Rescuing']
# per colonist: overrides; keys prefixed with '+' are explicit enables (major passion in matching skill)
ROLES = {
    'Human417':    dict(Hunting=1, Art=2, Doctor=2, Research=4, Hauling=3, Cleaning=3),                      # Ara: shooter/artist
    'Human349926': dict(Doctor=1, Research=1, Warden=2, Handling=3, Diplomat=1, Hauling=4, Cleaning=4),     # Isla: doctor/scientist
    'Human372325': dict(Growing=1, PlantCutting=1, Crafting=3, Art=4, Tailoring=4, Firefighter=1, Patient=1, PatientBedRest=1),
    'Human323':    {'Cooking': 1, 'Growing': 2, 'PlantCutting': 2, '+Mining': 3, 'Crafting': 4, 'Cleaning': 4},  # Sawyer: cook/farmer
    'Human398':    dict(Construction=1, Growing=2, PlantCutting=2, Handling=1, Warden=3, Research=3),       # Case: builder/farmer
    'Human422742': {'Warden': 2, '+Hunting': 2, 'Mining': 3, 'Art': 4, 'Research': 4},                       # Stark: guard
    'Human448873': dict(Cooking=2, Handling=1, Tailoring=2, Crafting=2, Smithing=3, Construction=4, Hauling=2, Cleaning=2, Rescuing=1),
    'Human422624': dict(Mining=1, Research=2, Art=2, Hunting=3, Growing=4),                                   # Triss: miner/artist
    'Human212589': dict(Smithing=1, Tailoring=1, Crafting=1, Construction=2, Warden=3),                       # crafter
    'Human320312': dict(Mining=1, Research=1, Art=2, Warden=3, Smithing=4, Tailoring=4),                     # Barin: miner/scientist
}
FIGHT_SHOOT = {'Human417', 'Human422742'}
FIGHT_MELEE = {'Human349926', 'Human372325', 'Human448873', 'Human212589'}
TIMETABLE = ['Sleep'] * 6 + ['Anything'] + ['Work'] * 12 + ['Joy'] * 3 + ['Sleep'] * 2


def policy_names(head):
    def grab(tag, prefix):
        i = head.find('<%s>' % tag); j = head.find('</%s>' % tag, i)
        b = head[i:j]
        return {int(m.group(1)): '%s_%s_%s' % (prefix, m.group(2), m.group(1)) for m in re.finditer(r'<li>\s*<id>(\d+)</id>\s*<label>(.*?)</label>', b)}
    return grab('outfitDatabase', 'ApparelPolicy'), grab('foodRestrictionDatabase', 'FoodPolicy')


def pawn_kind(r):
    if r.cls != 'Pawn' or r.d != 'Human':
        return None
    if r.faction == FAC and '<hostFaction>' not in r.raw.replace('<hostFaction>null</hostFaction>', ''):
        return 'colonist'
    m = re.search(r'<hostFaction>(.*?)</hostFaction>', r.raw)
    if m and m.group(1) == FAC:
        return 'prisoner'
    if r.faction == 'Faction_0':
        return 'guest'
    return None


# =====================================================================
def zone_cells_text(cells):
    return ''.join('\n\t\t\t\t\t\t\t\t<li>(%d, 0, %d)</li>' % c for c in cells) + '\n\t\t\t\t\t\t\t'


def set_zone_cells(head, zid, cells):
    rx = re.compile(r'(<li Class="Zone_Stockpile">\s*<ID>%d</ID>.*?<cells>)(.*?)(</cells>)' % zid, re.S)
    m = rx.search(head)
    assert m, zid
    return head[:m.start(2)] + zone_cells_text(cells) + head[m.end(2):]


def area_grid_xml(cells):
    parts = []
    if cells:
        parts.append('<trueCount>%d</trueCount>' % len(cells))
    parts.append('<mapSizeX>250</mapSizeX><mapSizeZ>250</mapSizeZ>')
    parts.append('<arrDeflate>\n%s\n</arrDeflate>' % enc(pack_bits(cells)))
    return '<innerGrid>' + ''.join(parts) + '</innerGrid>'


def get_area_cells(head, aid):
    m = re.search(r'<li Class="Area_\w+">\s*<ID>%d</ID>\s*<innerGrid>(.*?)</innerGrid>' % aid, head, re.S)
    a = re.search(r'<arrDeflate>\s*(.*?)\s*</arrDeflate>', m.group(1), re.S)
    return unpack_bits(zlib.decompress(base64.b64decode(re.sub(r'\s', '', a.group(1))), -15))


def set_area_cells(head, aid, cells):
    rx = re.compile(r'(<li Class="Area_\w+">\s*<ID>%d</ID>\s*)<innerGrid>.*?</innerGrid>' % aid, re.S)
    m = rx.search(head)
    assert m, aid
    return head[:m.start()] + m.group(1) + area_grid_xml(cells) + head[m.end():]


def rects_cells(rects):
    return {(x, z) for a, b, c, d in rects for x in range(a, b + 1) for z in range(c, d + 1)}


def finalize(M, P, rocks, log=print):
    head = M.head
    # ---------------- rocks under the new base
    clear_rect = [(114, 159, 107, 156), (100, 114, 111, 136), (122, 126, 92, 107), (160, 175, 130, 136)]
    kill = {c for c in rocks if in_rects(c, clear_rect)}
    b = re.search(r'(<compressedThingMapDeflate>\s*)(.*?)(\s*</compressedThingMapDeflate>)', head, re.S)
    arr = list(struct.unpack('<62500H', zlib.decompress(base64.b64decode(re.sub(r'\s', '', b.group(2))), -15)))
    for (x, z) in kill:
        arr[z * 250 + x] = 0
    head = head[:b.start(2)] + enc(struct.pack('<62500H', *arr)) + head[b.end(2):]
    log('rock cells removed:', len(kill))

    # ---------------- terrain / roofs
    terr = get_grid(head, 'terrainGrid', 'topGridDeflate')
    hs = {n: h(n) for n in set(P.floors.values())}
    for c, f in P.floors.items():
        terr[c[1] * 250 + c[0]] = hs[f]
    under = get_grid(head, 'terrainGrid', 'underGridDeflate')
    oldfloor = {h(n) for n in ('WoodPlankFloor', 'TileSandstone', 'TileMarble', 'TileLimestone', 'TileGranite', 'TileSlate', 'Concrete', 'SterileTile')}
    nrev = 0
    for (x, z) in rects_cells(DEMO):
        i = z * 250 + x
        if (x, z) not in P.floors and terr[i] in oldfloor:
            terr[i] = under[i] if under[i] else h('Soil'); nrev += 1
    log('old floors reverted', nrev)
    head = put_grid(head, 'terrainGrid', 'topGridDeflate', terr)
    roof = get_grid(head, 'roofGrid', 'roofsDeflate')
    nroof = 0
    for (x, z) in P.roof:
        i = z * 250 + x
        if roof[i] == 0:
            roof[i] = ROOF_CONSTRUCTED; nroof += 1
    ncleared = 0
    for (x, z) in rects_cells(DEMO):
        i = z * 250 + x
        if roof[i] == ROOF_CONSTRUCTED and (x, z) not in P.roof:
            roof[i] = 0; ncleared += 1
    head = put_grid(head, 'roofGrid', 'roofsDeflate', roof)
    log('floors', len(P.floors), 'roof cells', nroof, 'old roof cleared', ncleared)

    # ---------------- stockpile zones
    fz = sorted(P.zones['freezer'], key=lambda c: (c[1], c[0]))
    wz = sorted(P.zones['store_main'] | P.zones['store_apparel'], key=lambda c: (c[0], c[1]))
    head = set_zone_cells(head, 17, fz[:120])       # Склад 4 (Important) -> freezer
    head = set_zone_cells(head, 8, fz[120:])        # Склад 6
    parts = {7: wz[:15], 5: wz[15:40], 10: wz[40:70], 11: wz[70:]}
    for zid, cells in parts.items():
        head = set_zone_cells(head, zid, cells)
    head = set_zone_cells(head, 19, sorted(P.zones['guestfood']))
    log('freezer', len(fz), 'warehouse', len(wz))
    zone_cells = {17: fz[:120], 8: fz[120:], 7: parts[7], 5: parts[5], 10: parts[10], 11: parts[11]}

    # ---------------- areas
    home = get_area_cells(head, 0)
    main_margin = rects_cells([(97, 162, 104, 160), (119, 130, 88, 108)])
    head = set_area_cells(head, 0, home | main_margin)
    broof = get_area_cells(head, 1)
    head = set_area_cells(head, 1, broof | rects_cells([(114, 159, 107, 156)]))
    head = set_area_cells(head, 6, P.areas['shop'])
    guest_label = 'Гости'
    gm = re.search(r'(<li Class="Area_Allowed">\s*<ID>6</ID>.*?</li>)', head, re.S)
    new_area = ('\n\t\t\t\t\t<li Class="Area_Allowed">\n\t\t\t\t\t\t<ID>42</ID>\n\t\t\t\t\t\t%s\n\t\t\t\t\t\t<label>%s</label>\n'
                '\t\t\t\t\t\t<color>RGBA(0.950, 0.600, 0.200, 1.000)</color>\n\t\t\t\t\t</li>') % (area_grid_xml(P.areas['guest']), guest_label)
    head = head[:gm.end()] + new_area + head[gm.end():]
    head = head.replace('<nextAreaID>42</nextAreaID>', '<nextAreaID>43</nextAreaID>', 1)
    guest_ref = 'Area_42_Named_' + guest_label
    n1 = head.count('Area_0_Home</defaultAreaRestriction>')
    head = head.replace('<defaultAreaRestriction>Area_0_Home</defaultAreaRestriction>', '<defaultAreaRestriction>%s</defaultAreaRestriction>' % guest_ref)
    head = head.replace('<guestArea>Area_0_Home</guestArea>', '<guestArea>%s</guestArea>' % guest_ref)
    log('guest area set; default restriction replaced', n1)

    # ---------------- drop crop cells under the east killbox
    def drop_growing(m):
        blk = m.group(0)
        def keep(c):
            return not (160 <= int(c.group(1)) <= 175 and 130 <= int(c.group(2)) <= 136)
        return re.sub(r'\s*<li>\((\d+), 0, (\d+)\)</li>', lambda c: c.group(0) if keep(c) else '', blk)
    head = re.sub(r'<li Class="Zone_Growing">.*?</cells>', drop_growing, head, flags=re.S)

    # ---------------- pawns
    outfits, foods = policy_names(head)
    # free cells for relocating people
    solid = set(P.walls)
    for o in P.objs:
        if o['d'] in SOLID_DEFS or o['d'] in ('Cooler', 'Vent'):
            solid |= set(footprint(o))
    spine = [(x, z) for z in (123, 125) for x in range(117, 157) if (x, z) not in solid]
    hall = [(x, z) for x in range(123, 126) for z in range(109, 117) if (x, z) not in solid]
    prison = [(x, z) for z in (141, 142) for x in range(141, 158) if (x, z) not in solid]
    used = set()
    def take(lst):
        for c in lst:
            if c not in used:
                used.add(c); return c
        raise RuntimeError('no free cell')
    region_new = [(114, 159, 107, 156), (100, 114, 111, 136), (122, 126, 92, 107), (160, 175, 130, 136)]
    moved_pawns = 0
    for r in M.recs:
        if r.cls != 'Pawn' or not r.pos:
            continue
        kind = pawn_kind(r)
        inside = in_rects(r.pos, region_new) or r.pos in solid
        if inside:
            tgt = take(hall if kind == 'guest' else prison if kind == 'prisoner' else spine)
            r.set_pos(*tgt)
            r.raw = re.sub(r'<nextCell>\([^)]*\)</nextCell>', '<nextCell>(%d, 0, %d)</nextCell>' % tgt, r.raw)
            moved_pawns += 1
        if kind == 'colonist':
            pid = r.id
            cur = [int(v) for v in re.findall(r'<li>(\d)</li>', re.search(r'<workSettings>.*?</workSettings>', r.raw, re.S).group(0))]
            new = list(cur)
            for k, v in ROLES.get(pid, {}).items():
                name = k.lstrip('+')
                i = WT.index(name)
                if cur[i] > 0 or k.startswith('+'):
                    new[i] = v
            r.raw = re.sub(r'(<workSettings>.*?<vals>)(.*?)(</vals>)', lambda m: m.group(1) + ''.join('<li>%d</li>' % v for v in new) + m.group(3), r.raw, count=1, flags=re.S)
            r.raw = re.sub(r'(<timetable>\s*<times>)(.*?)(</times>)', lambda m: m.group(1) + ''.join('<li>%s</li>' % t for t in TIMETABLE) + m.group(3), r.raw, count=1, flags=re.S)
            outfit = outfits[7] if pid in FIGHT_SHOOT else outfits[8] if pid in FIGHT_MELEE else outfits[2]
            r.raw = re.sub(r'<curOutfit>.*?</curOutfit>', '<curOutfit>%s</curOutfit>' % outfit, r.raw)
            hostility = 'Attack' if pid in FIGHT_SHOOT | FIGHT_MELEE else 'Flee'
            r.raw = re.sub(r'<hostilityResponse>\w+</hostilityResponse>', '<hostilityResponse>%s</hostilityResponse>' % hostility, r.raw, count=1)
            ROLES.setdefault('_out', {})[pid] = (new, outfit, hostility)
        elif kind == 'prisoner':
            r.raw = re.sub(r'<curRestriction>.*?</curRestriction>', '<curRestriction>%s</curRestriction>' % foods[3], r.raw)
    log('pawns relocated', moved_pawns)

    # ---------------- BetterPawnControl zone-0 links
    ds = head.find('<li Class="BetterPawnControl.DataStorage">')
    bpc = head[ds:]
    outmap = ROLES['_out']
    def patch_links(text, tag, fn):
        out = []; pos = 0
        rx = re.compile(r'<li>\s*<zone>0</zone>\s*<colonist>Thing_(\w+)</colonist>.*?</li>', re.S)
        m0 = re.search(r'<%s>' % tag, text)
        m1 = text.find('</%s>' % tag, m0.end())
        seg = text[m0.end():m1]
        def sub(m):
            pid = m.group(1)
            return fn(pid, m.group(0)) if pid in outmap else m.group(0)
        seg2 = rx.sub(sub, seg)
        return text[:m0.end()] + seg2 + text[m1:]
    def work_fn(pid, txt):
        new = outmap[pid][0]
        return re.sub(r'(<values>)(.*?)(</values>)', lambda m: m.group(1) + ''.join('<li>%d</li>' % v for v in new) + m.group(3), txt, flags=re.S)
    def sched_fn(pid, txt):
        return re.sub(r'(<schedule>)(.*?)(</schedule>)', lambda m: m.group(1) + ''.join('<li>%s</li>' % t for t in TIMETABLE) + m.group(3), txt, flags=re.S)
    def assign_fn(pid, txt):
        new, outfit, host = outmap[pid]
        txt = re.sub(r'<outfit>.*?</outfit>', '<outfit>%s</outfit>' % outfit, txt)
        txt = re.sub(r'<hostilityResponse>\w+</hostilityResponse>', '<hostilityResponse>%s</hostilityResponse>' % host, txt)
        return txt
    bpc = patch_links(bpc, 'WorkLinks', work_fn)
    bpc = patch_links(bpc, 'ScheduleLinks', sched_fn)
    bpc = patch_links(bpc, 'AssignLinks', assign_fn)
    bpc = re.sub(r'<DefaultPrisonerFoodPolicy>.*?</DefaultPrisonerFoodPolicy>', '<DefaultPrisonerFoodPolicy>%s</DefaultPrisonerFoodPolicy>' % foods[3], bpc, count=1)
    head = head[:ds] + bpc
    head = re.sub(r'(<prisonerFoodPolicy>)FoodPolicy_[^<]*(</prisonerFoodPolicy>)', r'\g<1>' + foods[3] + r'\g<2>', head)

    # ---------------- relocate loose items
    perish = {'RawPotatoes', 'RawBerries', 'RawHops', 'MealSimple', 'Kibble'}
    dump_cells = []
    zs = head[head.find('<zoneManager>'):head.find('</zoneManager>')]
    dm = re.search(r'<ID>14</ID>.*?<cells>(.*?)</cells>', zs, re.S)
    dump_cells = [(int(a), int(b)) for a, b in re.findall(r'<li>\((\d+), 0, (\d+)\)</li>', dm.group(1))]
    occupied = collections.defaultdict(int)
    for r in M.recs:
        if r.deleted or not r.pos: continue
        if r.cls in ('Pawn', 'Plant', 'DeadPlant', 'Filth'): continue
        if r.cls.startswith('Building') or r.cls == 'Building' or r.cls.endswith('GuestBed') or r.cls.endswith('ManagerStation'): continue
        occupied[r.pos] += 1
    fcells = [c for c in fz]
    wcells = [c for c in wz]
    def free_from(lst):
        for c in lst:
            if occupied[c] == 0:
                occupied[c] += 1; return c
        return None
    relocated = 0; leftovers = 0
    for r in M.recs:
        if r.deleted or not r.pos: continue
        if r.cls in ('Pawn', 'Plant', 'DeadPlant', 'Filth'): continue
        if r.cls.startswith('Building') or r.cls == 'Building' or r.cls.endswith('GuestBed') or r.cls.endswith('ManagerStation'): continue
        if not (in_rects(r.pos, DEMO) or in_rects(r.pos, CLEAR) or in_rects(r.pos, region_new)):
            continue
        if r.cls == 'Corpse':
            tgt = free_from(dump_cells)
        elif r.d in perish:
            tgt = free_from(fcells) or free_from(wcells)
        else:
            tgt = free_from(wcells) or free_from(fcells)
        if tgt is None:
            leftovers += 1; continue
        r.set_pos(*tgt); relocated += 1
    log('items relocated', relocated, 'leftover', leftovers)
    M.head = head
    return zone_cells


def clean_dangling(txt, log=print):
    ids = set(re.findall(r'<id>([A-Za-z_]+\d+)</id>', txt))
    refs = set(re.findall(r'>Thing_([A-Za-z_]+\d+)<', txt))
    bad = sorted(r for r in refs if r not in ids)
    log('dangling refs to clean:', len(bad))
    for b in bad:
        e = re.escape(b)
        txt = re.sub(r'<li>\s*<def>\w+</def>\s*<target>Thing_%s</target>\s*</li>' % e, '', txt)
        txt = re.sub(r'<li>\s*<claimant>[^<]*</claimant>\s*<job>[^<]*</job>\s*<target>Thing_%s</target>.*?</li>' % e, '', txt, flags=re.S)
        txt = re.sub(r'<li>Thing_%s</li>' % e, '', txt)
        txt = txt.replace('>Thing_%s<' % b, '>null<')
    return txt


def write_out(M):
    txt = clean_dangling(M.assemble())
    with open(OUT, 'w', encoding='utf-8-sig', newline='') as f:
        f.write(txt)
    return txt


if __name__ == '__main__':
    M, P, T, rocks = build_all()
    zc = finalize(M, P, rocks)
    txt = write_out(M)
    print('written', len(txt))
