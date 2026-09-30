"""Part 2: walls, doors, conduits and power wiring."""
import heapq, re, collections
from apply_build import *
from geom import rect
from render import footprint

SOLID_DEFS = {'Table2x2c', 'Bed', 'BedGuest', 'Shelf', 'FermentingBarrel', 'Battery', 'SolarGenerator', 'Grave',
              'Turret_MiniTurret', 'ElectricSmithy', 'TableMachining', 'DrugLab', 'ElectricSmelter', 'BiofuelRefinery',
              'ElectricTailoringBench', 'HandTailoringBench', 'TableSculpting', 'Brewery', 'HiTechResearchBench',
              'FueledStove', 'TableButcher', 'PokerTable', 'WindTurbine', 'HC_SlotMachineRed', 'HC_SlotMachineGreen',
              'HC_SlotMachineBlue', 'Heater', 'StandingLamp', 'SculptureLarge', 'ChessTable', 'MultiAnalyzer',
              'CommsConsole', 'LongRangeMineralScanner', 'CM_BasicManagerStation', 'FirefoamPopper', 'OrbitalTradeBeacon',
              'PodLauncher', 'TransportPod', 'FloodLight', 'HorseshoesPin'}


def rock_cells(M):
    s = M.s
    b = re.search(r'<compressedThingMapDeflate>\s*(.*?)\s*</compressedThingMapDeflate>', s, re.S)
    raw = zlib.decompress(base64.b64decode(re.sub(r'\s', '', b.group(1))), -15)
    arr = struct.unpack('<62500H', raw)
    return {(i % 250, i // 250) for i in range(62500) if arr[i]}


def build_structures(M, P, T, log=print):
    rocks = rock_cells(M)
    # ---------------------------------------------------------- walls / doors
    turret_cells = set()
    for o in P.objs:
        if o.get('replaces_wall'):
            turret_cells.add(o['pos'])
    wall_ids = {}
    for c in sorted(P.walls):
        if c in turret_cells:
            continue
        raw, nid = new_thing(M, T, 'Wall', c[0], c[1], 0, P.walls[c])
        M.new.append(raw)
    door_ids = {}
    for c in sorted(P.doors):
        raw, nid = new_thing(M, T, 'Door', c[0], c[1], 0, P.doors[c])
        M.new.append(raw)

    # ---------------------------------------------------------- power network
    cells_of = {}         # cell -> (kind, id)
    solid = set(P.walls)
    obj_cells = {}
    for o in P.objs:
        fp = set(footprint(o))
        obj_cells[id(o)] = fp
        if o['d'] in SOLID_DEFS:
            for c in fp:
                if o['d'] not in ('Battery', 'SolarGenerator', 'WindTurbine'):
                    solid.add(c) if False else None
    blocked = set()
    for o in P.objs:
        if o['d'] in SOLID_DEFS and o['d'] not in ('Battery', 'SolarGenerator', 'WindTurbine', 'Heater', 'StandingLamp',
                                                     'FirefoamPopper', 'Turret_MiniTurret'):
            blocked |= obj_cells[id(o)]
    # generators & batteries are transmitters
    TR = {}               # cell -> thing id
    for o in P.objs:
        if o['d'] in ('Battery', 'SolarGenerator', 'WindTurbine'):
            for c in obj_cells[id(o)]:
                TR[c] = o['rid']
    conduit_cells = set(P.conduits)
    # trunk along the spine
    for x in range(115, 159):
        conduit_cells.add((x, 124))
    # wind turbine lines
    for z in range(116, 133):
        conduit_cells.add((97, z))
    for x in range(97, 105):
        conduit_cells.add((x, 121))
    conduit_cells = {c for c in conduit_cells if c not in rocks}
    for c in conduit_cells:
        TR.setdefault(c, None)           # id assigned later
    consumers = [o for o in P.objs if o['d'] in POWERED]
    deleted_ids = {r.id for r in M.recs if r.deleted}
    for r in M.recs:
        if r.deleted or not r.pos or r.cls == 'Pawn':
            continue
        m = re.search(r'<parentThing>Thing_(\w+)</parentThing>', r.raw)
        if m and m.group(1) in deleted_ids:
            consumers.append({'d': r.d, 'pos': r.pos, 'rec': r, 'rot': r.rot})
            log('reconnecting kept consumer', r.d, r.pos)
    log('consumers', len(consumers))

    def passable_cost(c):
        if c in rocks: return None
        if c in blocked: return None
        if c in P.walls and c not in P.doors: return 6
        if c in P.doors: return 1.5
        return 1

    def neighbours(c):
        x, z = c
        return ((x + 1, z), (x - 1, z), (x, z + 1), (x, z - 1))

    def connected(o):
        x, z = o['pos']
        for c in [(x, z)] + list(neighbours((x, z))):
            if c in TR:
                return c
        return None

    def connect(o):
        """Dijkstra from consumer connector cells to nearest transmitter cell."""
        x, z = o['pos']
        starts = [(x, z)] + list(neighbours((x, z)))
        pq = []
        dist = {}
        prev = {}
        for s in starts:
            cost = 0.0 if s == (x, z) else 0.5
            if s in TR:
                return [s]
            heapq.heappush(pq, (cost, s)); dist[s] = cost; prev[s] = None
        while pq:
            dcur, cur = heapq.heappop(pq)
            if dcur > dist.get(cur, 1e9): continue
            if cur in TR:
                path = []
                while cur is not None:
                    path.append(cur); cur = prev[cur]
                return path
            for n in neighbours(cur):
                pc = passable_cost(n)
                if pc is None and n not in TR: continue
                nd = dcur + (pc if pc is not None else 1)
                if nd < dist.get(n, 1e9):
                    dist[n] = nd; prev[n] = cur
                    heapq.heappush(pq, (nd, n))
        return None

    added = 0
    order = sorted(consumers, key=lambda o: (o['pos'][0] - 136) ** 2 + (o['pos'][1] - 124) ** 2)
    for o in order:
        if connected(o):
            continue
        path = connect(o)
        if not path:
            log('NO POWER PATH for', o['d'], o['pos'])
            continue
        for c in path:
            if c not in TR:
                conduit_cells.add(c); TR[c] = None; added += 1
    log('conduit cells', len(conduit_cells), 'added by routing', added)

    # old drill feeder: connect network to old conduits at x>=145, z<=106
    old = [r for r in M.recs if r.d in ('HiddenConduit', 'PowerConduit') and r.pos and old_conduit_keep(r.pos) and not r.deleted]
    old_cells = {r.pos: r.id for r in old}
    if old_cells:
        # multi-source Dijkstra from network cells toward any old conduit cell
        pq = []; dist = {}; prev = {}
        for c in TR:
            dist[c] = 0; prev[c] = None; heapq.heappush(pq, (0, c))
        goal = None
        while pq:
            dcur, cur = heapq.heappop(pq)
            if dcur > dist[cur]: continue
            if cur in old_cells:
                goal = cur; break
            for n in neighbours(cur):
                pc = passable_cost(n)
                if pc is None and n not in old_cells: continue
                if pc is None: pc = 1
                nd = dcur + pc
                if nd < dist.get(n, 1e9):
                    dist[n] = nd; prev[n] = cur; heapq.heappush(pq, (nd, n))
        if goal:
            cur = goal
            n_add = 0
            while cur is not None:
                if cur not in TR and cur not in old_cells:
                    conduit_cells.add(cur); TR[cur] = None; n_add += 1
                cur = prev[cur]
            log('drill feeder cells added', n_add)
        for c, i in old_cells.items():
            TR[c] = i

    # create conduit things
    for c in sorted(conduit_cells):
        if c in old_cells:
            continue
        raw, nid = new_thing(M, T, 'PowerConduit', c[0], c[1])
        raw = set_raw_tag(raw, 'parentThing', 'null')
        M.new.append(raw)
        TR[c] = 'PowerConduit%d' % nid
    # old conduits get id map already

    # attach consumers
    missing = 0
    for o in consumers:
        c = connected(o)
        if not c:
            missing += 1
            continue
        pid = TR[c]
        ref = 'Thing_' + pid if pid else 'null'
        if o.get('rec') is not None:
            o['rec'].raw = set_raw_tag(o['rec'].raw, 'parentThing', ref)
        elif 'new_raw_idx' in o:
            M.new[o['new_raw_idx']] = set_raw_tag(M.new[o['new_raw_idx']], 'parentThing', ref)
    log('consumers without power:', missing)
    return conduit_cells, rocks


if __name__ == '__main__':
    M = SaveModel(); P = build()
    T, movable, moved, deleted = apply_build(M, P, log=lambda *a: None)
    cc, rocks = build_structures(M, P, T)
    # bounds vs rock
    bad = [c for c in list(P.walls) + [o['pos'] for o in P.objs] if c in rocks]
    print('cells on rock:', bad[:10])
    print('new things total', len(M.new))
